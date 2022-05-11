import matplotlib
from cmd_interface import *
from util.util_file import *
import copy
import collections
from visualization.networkx_adapter import *
from util.platform_info import *
from build_parser.cmake_parser import *
from build_parser.cmake_parser_ic import *
from build_parser.pro_parser import *
from common.module_types import *
from dependency.dependency_config import *
from util.util_print import *


class BuildScriptParser:
    def build_dep_graph(self, url):
        pass


class DependencyAnalysisHandler(Cmd):
    def __init__(self):
        self.ext_handlers = {
            'pro': ProBuildScriptParser()
        }

        self.file_handlers = {
            'CMakeLists.txt': {
                "default": CMakeBuildScriptParser(),
                "ic": CMakeBuildScriptParserIC()
            }
        }

        delimiter = PlatformInfo.get_delimiter()
        cfg_reader = \
            DependencyConfigReader(os.path.dirname(os.path.realpath(__file__)) + \
            delimiter + 'cfg_dependency.conf')
        self.dep_cfg = cfg_reader.getConfig(cfg_reader.readAsJSON())

        url = os.path.dirname(os.path.realpath(__file__)) + delimiter + 'dependency_info.json'
        self.dep_infos = UtilFile.read_json(url)
        whitelist = []
        for category, items in self.dep_infos["whitelist"].items():
            whitelist += items
        self.white_list = set(whitelist)
        self.core_components = self.dep_infos["core_components"]

        self.layer_depth = {
            'HMI_APP': 0,
            'HMI_LIB': 1,
            'APP': 2,
            'LIB': 3,
            'SVC': 4,
            'LIB:HAL': 5
        }

        self.allowed_dep = {
            'HMI_APP': {'HMI_APP', 'HMI_LIB', 'APP', 'LIB', 'ETC'},
            'HMI_LIB': {'APP', 'LIB', 'ETC'},
            'APP': {'APP', 'LIB', 'ETC'},
            'LIB': {'SVC', 'ETC'},          # interface lib
            'SVC': {'SVC', 'HAL', 'ETC'},
            'LIB:HAL': {'ETC'},
            'ETC': {'ETC'}
        }

    def __del__(self):
        pass

    def merge_graph(self, g1, g2):
        """
            merge g1 and g2 in g1
        """
        for node, info in g2.items():
            if node not in g1:
                g1[node] = info
            else:
                for u in g2[node].fan_outs:
                    if u not in g1[node].fan_outs:
                        if '' == u or not u:
                            print('2. empty string')
                        g1[node].fan_outs.add(u)
    
    def init(self, prj):
        for filename, hdrs in self.file_handlers.items():
            for prj, hdr in hdrs.items():
                hdr.init(prj)
        
    def filter_files(self, loc):
        location = collections.defaultdict(list)
        types = set(['app', 'api', 'service', 'hal'])

        for directory, files in loc.items():
            paths = directory.split(PlatformInfo.get_delimiter())
            type = None
            for path in paths:
                if path in types:
                    type = path
                    break
            
            for file, file_type in files:
                file_name = file.split(PlatformInfo.get_delimiter())[-1]
                extension = file_name.split('.')[-1]

                # api gets only cmake file
                if type == 'api':
                    if file_name in self.file_handlers:
                        location[directory] += (file, file_type),
                else:
                    location[directory] += (file, file_type),
        
        return location

    def execute(self, opts, cfg) -> bool:
        locations = UtilFile.get_dirs_files_with_filter(opts["path"], \
            cfg.get_recursive(), ['pro'], ['CMakeLists.txt'])
        if not locations:
            return False
        
        locations = self.filter_files(locations)
        errs = []
        
        prj = opts['prj']
        self.init(prj)
        dep_graph = collections.defaultdict(ModuleInfo)

        for directory, files in locations.items():
            if not files:
                continue

            for file, file_type in files:
                file_name = file.split(PlatformInfo.get_delimiter())[-1]
                extension = file_name.split('.')[-1]

                graph = None
                if file_name in self.file_handlers:
                    file_prj = 'default'
                    if prj in self.file_handlers[file_name]:
                        file_prj = prj
                    graph = self.file_handlers[file_name][file_prj].build_dep_graph(file, self.white_list)
                elif extension in self.ext_handlers:
                    graph = self.ext_handlers[extension].build_dep_graph(file, self.dep_cfg, prj, self.white_list)

                if not graph:
                    errs += file,

                if graph:
                    self.merge_graph(dep_graph, graph)
                #print()

        # print('>>>>>>>>>>>>>>>')
        # for err in errs:
        #     print(err)
        # sys.exit()

        graph = self.register_fan_ins(dep_graph)
        self.add_hmilib_dep(graph, cfg)

        module_infos = {
            'LIB': self.get_api_module_names(graph)
        }

        self.file_handlers['CMakeLists.txt'][prj].replace_macro_dep(graph, module_infos)

        self.calc_stability(graph)
        
        self.traverse_graphs(graph)
        # print()
        # self.dump(graph)
        # sys.exit()

        links = self.get_links(graph)
        color_edges, node_to_id, id_to_node, violations = \
            self.create_edges(graph, links)

        self.print_dependency_violation(violations, graph, 'dependency violation')
        self.print_instability(graph, self.white_list, 'instability')
        self.print_instable_dep(graph, 'instable dependency')

        # plt.rc('font', **{'size':5})
        # plt.figure(figsize=(10, 4))
        # plt.plot([graph[k].instability for k in graph])
        # plt.xticks(range(len(graph)), [k for k in graph], rotation=90)
        # plt.show()

        if 'graph' in opts and opts['graph'] == 'True':
            if 'node' in opts and opts['node']:
                trace = NetworkX.get_trace(graph, opts['node'])
                self.traverse_graphs(graph, [opts['node']])

                for uid, vid, attr in color_edges:
                    attr['color'] = 'red' if (id_to_node[uid], id_to_node[vid]) in trace else 'white'
                
            NetworkX.draw_layered_diagram(graph, links, color_edges, node_to_id, \
                id_to_node, self.dep_cfg)

        return True
    
    def create_edges(self, graph, links):
        node_to_id = collections.defaultdict(str)
        id_to_node = collections.defaultdict(int)
        violations = []
        id = 0

        nodes = graph.keys()
        for id, node in enumerate(nodes):
            id_to_node[id] = node
            node_to_id[node] = id

        cur_id = id + 1
        not_in_nodes = []
        for u, v in links:  # {(name1, name2), ...}
            if u not in node_to_id:
                id_to_node[cur_id] = u
                node_to_id[u] = cur_id
                cur_id += 1

            if v not in node_to_id:
                id_to_node[cur_id] = v
                node_to_id[v] = cur_id
                cur_id += 1

        edges = []
        for u, v in links:
            edges += (node_to_id[u], node_to_id[v]),
        
        def_edge_color = self.dep_cfg.get_edge_color()
        color_edges = []
        cnt = 0
        tot = 0

        for uid, vid in edges:
            u = id_to_node[uid]
            v = id_to_node[vid]
            color = def_edge_color

            try:
                violation_edge = None
                if graph[v].type and graph[v].type not in self.allowed_dep[graph[u].type]:
                    violation_edge = (u, v)

                if v in self.core_components:
                    violation_edge = None

                if violation_edge:
                    violations += (u, v),
                    color = 'red'
                    cnt += 1

            except:
                print('type ERROR')
                print(f'{graph[v].type} for {v}')
                print(f'{graph[u].type} for {u}')

            color_edges += (uid, vid, {'color': color}),
            tot += 1
        
        if tot > 0:
            print(' * number of violations = {} / {} ({:.2f}%)'.format(cnt, tot, cnt/tot*100))
        return color_edges, node_to_id, id_to_node, violations
    
    def get_api_module_names(self, g):
        modules = []
        for u, info in g.items():
            if 'LIB' == info.type:
                modules += u,
        return modules
    
    def add_hmilib_dep(self, graph, cfg):
        hmi_libs = set()
        for u, info in graph.items():
            if info.type == 'HMI_LIB':
                hmi_libs.add(u)
        
        for u, info in graph.items():
            if info.type != 'HMI_APP':
                continue

            delimiter = PlatformInfo.get_delimiter()
            path = '{}'.format(delimiter).join(info.url.split(delimiter)[:-1])
            
            qml_files = UtilFile.get_dirs_files_with_filter(path, \
                cfg.get_recursive(), ['qml'], [])
            
            if not qml_files:
                print('no qml ', path)
                continue
        
            deps = []
            for directory, files in qml_files.items():
                for file, file_type in files:
                    content = UtilFile.get_content(file)
                    if not content:
                        continue

                    content = re.compile("//.*").sub("", content)
                    dep_pat = re.compile('import.*')
                    m = dep_pat.finditer(content)
                    for r in m:
                        span = r.span()
                        dep = content[span[0]:span[1]]
                        #print('dep = ', dep)
                        dep = dep.split()
                        dep.pop(0)
                        dep = [item for item in dep if not item[0].isdigit()]
                        deps += dep

            for dep in deps:
                if dep not in hmi_libs:
                    continue

                graph[u].fan_outs.add(dep)
                graph[dep].fan_ins.add(u)
    
    def dump(self, graph):
        graph = sorted(graph.items(), key=lambda p: p[0])
        for name, info in graph:
            info.fan_outs = sorted(info.fan_outs)
            info.fan_ins = sorted(info.fan_ins)
            print(name)
            print(info.name)
            print(info.type)
            print(info.depth)
            print(info.instability)
            print(info.fan_outs)
            print(info.fan_ins)

    def register_fan_ins(self, g):
        etc_depth = max([info.depth for node, info in g.items()] + [0]) + 1

        graph = copy.deepcopy(g)
        for u, info in g.items():
            for v in g[u].fan_outs:
                if v not in graph:
                    graph[v].depth = etc_depth
                    graph[v].type = 'ETC'
                graph[v].fan_ins.add(u)

        return graph

    def calc_stability(self, g):
        for u in g:
            if len(g[u].fan_ins) + len(g[u].fan_outs) == 0:
                if len(g[u].fan_outs) > 0:
                    g[u].instability = 1
                else:
                    g[u].instability = 0
            else:    
                g[u].instability = \
                    len(g[u].fan_outs)/(len(g[u].fan_ins) + len(g[u].fan_outs))

    def traverse_graphs(self, g, nodes=[]):
        if not nodes:
            for k, v in g.items():
                #if v.type in {'APP', 'SVC', 'LIB'}:
                if v.type in {'APP', 'SVC'}:
                    nodes += k,
        
        for k, v in g.items():
            print(k, " type = ", v.type)
        #sys.exit()

        inbound = collections.defaultdict(int)
        for u in g:
            for v in g[u].fan_outs:
                inbound[v] += 1

        for node in nodes:
            print('Traverse: ')
            cur_inbound = copy.deepcopy(inbound)
            self.traverse_graph(g, node, cur_inbound)
    
    def traverse_graph(self, g, node, cur_inbound):
        q = [(node, 0)]

        while q:
            u, depth = q.pop()
            if depth > 7:
                continue

            print((1 if depth else 0)*' +', \
                depth*'--+', (1 if depth else 0)*'>', u, \
                ' in ({}), out ({}), I = {:.3f}'.format(
                    len(g[u].fan_ins),
                    len(g[u].fan_outs),
                    g[u].instability))

            if 0 >= cur_inbound[u] and u != node:
                continue

            if cur_inbound[u]:
                cur_inbound[u] -= 1

            for v in g[u].fan_outs:
                q += (v, depth + 1),

        print()

    def get_links(self, g):
        edges = set()
        nodes = []
        types = set()
        for k, v in g.items():
            #if v.type in set(self.dep_cfg.get_activated_edges()):
            nodes += k,
            types.add(v.type)

        for u in nodes:
            for v in g[u].fan_outs:
                edges.add((u, v))

        return edges
    
    def print_dependency_violation(self, items, graph, title=''):
        cols = ['from name', 'from type', 'from level', 'to name', 'to type', 'to level']
        rows = []
        col_widths = [10, 9, 10, 10, 9, 8]

        for u, v in items:
            row = []
            row += ('{:<10s}', u),
            row += ('{:<9s}', graph[u].type),
            row += ('{:<10d}', graph[u].depth),
            row += ('{:<10s}', v),
            row += ('{:<9s}', graph[v].type),
            row += ('{:<8d}', graph[v].depth),
            rows += row,

        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)
    
    def print_instability(self, graph, white_list, title=''):
        cols = ['name', 'in #', 'out #', 'I']
        rows = []
        col_widths = [25, 5, 5, 5]

        for name, info in graph.items():
            if name not in white_list:
                continue

            if info.type not in self.allowed_dep:
                # print(name + 'is not allowed type')
                continue

            row = []
            row += ('{:<20s}', name),
            row += ('{:<5d}', len(graph[name].fan_ins)),
            row += ('{:<5d}', len(graph[name].fan_outs)),
            row += ('{:.3f}', graph[name].instability),
            rows += row,
        
        rows.sort(key=lambda p: p[3], reverse=True)
        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)
    
    def print_instable_dep(self, graph, title=''):
        cols = ['name', 'I', 'instable dependency (stable -> instable)']
        rows = []
        col_widths = [12, 5, 70]

        for name, info in graph.items():
            if info.instability > 0.3 or not info.fan_outs:
                continue

            instable_dep = []
            for v in info.fan_outs:
                if graph[v].instability > 0.3:
                    instable_dep += (v, graph[v].instability),
            
            if not instable_dep:
                continue
            
            row = []
            row += ('{:<12s}', name),
            row += ('{:<.3f}', info.instability),

            deps = ''
            for i, value in enumerate(instable_dep):
                name, ins_rate = value
                deps += '({}, {:.2f})'.format(name, ins_rate)
                if i < len(instable_dep) - 1:
                    deps += ', '

            row += ('{:<70s}', deps),
            rows += row,
    
        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)
            




