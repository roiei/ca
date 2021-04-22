from cmd_interface import *
from util.util_file import *
import re
import copy
import collections
from visualization.networkx_adapter import *


class BuildScriptParser:
    def build_dep_graph(self, url):
        pass


class ProBuildScriptParser:
    def build_dep_graph(self, url):
        pass


class ModuleInfo:
    def __init__(self):
        self.name = ''
        self.type = ''
        self.dependency = set()
        self.depth = 0


class CMakeBuildScriptParser:
    types = {
        "APP_NAME": ("APP", 0),
        "LIB_NAME": ("LIB", 1),
        "SERVICE_NAME": ("SVC", 2)
    }

    @staticmethod
    def _parse_outputname(line, g, param, url):
        #print('line = ', line)
        sx = line.find('(')
        ex = line.rfind(')')
        if sx != -1 and sx < ex:
            line = line[sx + 1: ex]
        words = line.split(' ')
        type_str, name = words
        type_str = type_str.strip()
        name = name.strip()

        value = CMakeBuildScriptParser.types.get(type_str, ('NONE', 10))
        type, depth = value
        if type == 'NONE':
            return

        # print('type = ', type)
        # print('name = ', name)

        # if name == 'GIOMM_LIBRARIES':
        #     print(url)
        #     print(param)

        if name in g:
            print('name {} already exist'.format(name))
            return

        g[name] = ModuleInfo()
        g[name].name = name
        g[name].type = type
        g[name].depth = depth
        return name

    @staticmethod
    def _parse_dependency(line, g, param):
        sx = line.find('(')
        ex = line.rfind(')')
        content = line[sx + 1:ex].split()

        debug = False
        # if 'vehicleservice' == param:
        #     debug = True

        filtered = []
        for item in content:
            if item in {'${LIB_NAME}', 'PRIVATE', 
                '${APP_NAME}', '${PROJECT_NAME}', 
                '${LIBRARY_NAME}', 'SHARED', 
                '${STATICLIB_NAME}', 'STATIC'}:
                continue

            if '{' in item:
                sx = item.find('{')
                ex = item.rfind('}')
                item = item[sx + 1:ex]

            item = item.strip()
            filtered += item,
            if 'LDFLAGS' in item:
                ex = item.rfind('_LDFLAGS')
                item = item[:ex].lower()

            if '' == item or not item:
                print('1. empty string')

            g[param].dependency.add(item)
            if debug:
                print('vehicleservice ++ ', item)

        #print(filtered)
        #print(param, ' = ', g[param].dependency)

    pattern_handlers = {
        'dependency':
            ('target_link_libraries\s*\([\w$\s{}+]*\)',
            _parse_dependency.__func__)
    }


    def __init__(self):
        pass

    def get_content(self, url):
        lines = None
        with open(url, 'r', encoding='utf8') as f:
            lines = f.readlines()

        return ''.join(lines)

    def build_dep_graph(self, url):
        content = self.get_content(url)
        if not content:
            return

        g = collections.defaultdict(ModuleInfo)
        oname = ''

        pattern = re.compile('set\([A-Z_]+\s+[\w]+\)')
        m = pattern.finditer(content)
        for r in m:
            span = r.span()
            #print(content[span[0]:span[1]])
            res = CMakeBuildScriptParser._parse_outputname(
                content[span[0]:span[1]], g, oname, url)

            if '' != res and None != res:
                oname = res

        if '' == oname:
            #print('UNDEF: url = ', url)
            return

        for pname, value in CMakeBuildScriptParser.pattern_handlers.items():
            pattern_str, _handler = value
            pattern = re.compile(pattern_str)

            m = pattern.finditer(content)
            for r in m:
                span = r.span()
                name = _handler(content[span[0]:span[1]], g, oname)
        
        return g


class DependencyAnalysisHandler(Cmd):
    def __init__(self):
        self.extension_handlers = {
            'pro': ProBuildScriptParser()
        }

        self.file_handlers = {
            'CMakeLists.txt': CMakeBuildScriptParser()
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
                for u in g2[node].dependency:
                    if u not in g1[node].dependency:
                        if '' == u or not u:
                            print('2. empty string')
                        g1[node].dependency.add(u)

    def execute(self, opts, cfg):
        locations = UtilFile.get_dirs_files_with_filter(opts["path"], \
            cfg.get_recursive(), ['pro'], ['CMakeLists.txt'])
        if not locations:
            return False, None

        dep_graph = collections.defaultdict(ModuleInfo)

        for directory, files in locations.items():
            if not files:
                continue

            for file, file_type in files:
                #print(file, file_type)

                file_name = file.split('\\')[-1]
                extension = file_name.split('.')[-1]

                graph = None
                if file_name in self.file_handlers:
                    graph = \
                        self.file_handlers[file_name].build_dep_graph(file)
                # elif extension in self.extension_handlers:
                #     graph = self.extension_handlers.build_dep_graph(file_name)
                
                if graph:
                    self.merge_graph(dep_graph, graph)
                #print()

        #print('+traverse')
        #self.traverse_graph(dep_graph)
        #print()

        edges = self.get_links(dep_graph)
        NetworkX.draw_layered_diagram(dep_graph, edges)
        return True

    def traverse_graph(self, g):
        nodes = []
        for k, v in g.items():
            if v.type in {'APP', 'SVC'}:
                nodes += k,

        inbound = collections.defaultdict(int)
        for u in g:
            for v in g[u].dependency:
                inbound[v] += 1

        for app in nodes:
            print('Traverse: ')
            depth = 0
            cur_infound = copy.deepcopy(inbound)
            
            q = [(app, depth)]
            visited = set()

            while q:
                u, depth = q.pop()
                print((1 if depth else 0)*' +', depth*'--+', (1 if depth else 0)*'>', u)
                visited.add(u)
                if cur_infound[u]:
                    cur_infound[u] -= 1

                for v in g[u].dependency:
                    q += (v, depth + 1),

            print()

    def get_links(self, g):
        edges = set()
        nodes = []
        for k, v in g.items():
            if v.type in {'APP', 'LIB', 'SVC'}:
                nodes += k,

        for node in nodes:
            q = [node]

            while q:
                u = q.pop()
                for v in g[u].dependency:
                    edges.add((u, v))

        return edges
