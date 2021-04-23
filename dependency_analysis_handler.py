from cmd_interface import *
from util.util_file import *
import copy
import collections
from visualization.networkx_adapter import *
from util.platform_info import *
from cmake_parser import *
from module_types import *


class BuildScriptParser:
    def build_dep_graph(self, url):
        pass


class ProBuildScriptParser:
    def build_dep_graph(self, url):
        pass


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
                for u in g2[node].fan_outs:
                    if u not in g1[node].fan_outs:
                        if '' == u or not u:
                            print('2. empty string')
                        g1[node].fan_outs.add(u)

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
                file_name = file.split(PlatformInfo.get_delimiter())[-1]
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

        graph = self.register_fan_ins(dep_graph)
        self.calc_stability(graph)

        print('+traverse')
        self.traverse_graph(graph)
        print()

        edges = self.get_links(graph)
        NetworkX.draw_layered_diagram(graph, edges)
        return True

    def register_fan_ins(self, g):
        etc_depth = max([info.depth for node, info in g.items()]) + 1

        graph = copy.deepcopy(g)
        for u, info in g.items():
            for v in g[u].fan_outs:
                if v not in graph:
                    graph[v].depth = etc_depth
                graph[v].fan_ins.add(u)

        return graph

    def calc_stability(self, g):
        for u in g:
            if len(g[u].fan_ins) + len(g[u].fan_outs) == 0:
                g[u].instability = 1
            else:    
                g[u].instability = \
                    len(g[u].fan_outs)/(len(g[u].fan_ins) + len(g[u].fan_outs))

    def traverse_graph(self, g):
        nodes = []
        for k, v in g.items():
            #if v.type in {'APP', 'SVC', 'LIB'}:
            if v.type in {'APP', 'SVC'}:
                nodes += k,

        inbound = collections.defaultdict(int)
        for u in g:
            for v in g[u].fan_outs:
                inbound[v] += 1

        for node in nodes:
            print('Traverse: ')
            depth = 0
            cur_inbound = copy.deepcopy(inbound)
            
            q = [(node, depth)]
            visited = set()

            while q:
                u, depth = q.pop()
                print((1 if depth else 0)*' +', \
                    depth*'--+', (1 if depth else 0)*'>', u, \
                    ' in ({}), out ({}), I = {:.3f}'.format(
                        len(g[u].fan_ins),
                        len(g[u].fan_outs),
                        g[u].instability))

                visited.add(u)
                if cur_inbound[u]:
                    cur_inbound[u] -= 1

                for v in g[u].fan_outs:
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
                for v in g[u].fan_outs:
                    edges.add((u, v))

        return edges
