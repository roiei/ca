import matplotlib.pyplot as plt
from matplotlib.pyplot import figure, text
import np
import sys, networkx as nx, matplotlib.pyplot as plt
import collections
from common.module_types import *
import pprint


class NetworkX:
    def __init__(self):
        pass

    def __del__(self):
        pass

    @staticmethod
    def get_rgb_color(val):
        rgb = \
            ((int('0xFF',16) & val)<<16) | \
            ((int('0xFF',16) & val)<<8) | \
            ((int('0xFF',16) & val))

        return rgb

    @staticmethod
    def draw_layered_diagram(g, links, edges, node_to_id, id_to_node, dep_cfg):
        filtered_g = collections.defaultdict(ModuleInfo)
        for k, v in g.items():
            if not ' ' in k and '\\' not in k and '/' not in k:
                filtered_g[k] = v

        g = filtered_g
        
        inbound = collections.defaultdict(int)
        for u, v, attr in edges:
            inbound[v] += 1

        node_sizes = []
        node_colors = []
        font_colors = collections.defaultdict(str)

        fan_in_weight = dep_cfg.get_fan_in_weight()
        node_size_weight = dep_cfg.get_node_size_weight()

        for n in id_to_node.keys():
            node_sizes += inbound[n]*node_size_weight,
            weight = (inbound[n]*fan_in_weight)
            node_color = NetworkX.get_rgb_color(weight)
            font_color = NetworkX.get_rgb_color(max(0, 50 - weight))
            node_colors += node_color,
            font_color = str(hex(font_color))
            font_color = '#' + '{:0>6}'.format(font_color[2:])
            font_colors[n] = font_color

        ng = nx.DiGraph()
        depth_nodes = collections.defaultdict(list)
        for id, node in id_to_node.items():
            if node in g:
                #print('name = ', node, 'depth = ', g[node].depth)
                depth_nodes[g[node].depth] += id,

        for depth, nodes in depth_nodes.items():
            ng.add_nodes_from(nodes, layer=depth)

        pos = nx.multipartite_layout(ng, subset_key="layer", scale=5)

        array_op = lambda x, weight: np.array([x[0]*weight, x[1]*weight])
        pos = {id: array_op(coord, 3) for id, coord in pos.items()}

        #print(pos)
        #plt.figure(figsize=(180, 180))

        ng.add_edges_from(edges)  # color is not set here but at draw

        edge_colors = [attr['color'] for uid, vid, attr in ng.edges(data=True)]

        nx.draw(ng, pos, 
            node_size=node_sizes, 
            node_color=node_colors,
            edge_color=edge_colors,
            labels=id_to_node, 
            with_labels=False)
        
        degrees = dict(ng.degree)
        mxd = max(degrees.values())

        mx_font_size = dep_cfg.get_max_font_size()
        mn_font_size = dep_cfg.get_min_font_size()

        for id, (x, y) in pos.items():
            in_cnt = len(g[id_to_node[id]].fan_ins)
            out_cnt = len(g[id_to_node[id]].fan_outs)
            try:
                title = id_to_node[id] + ' > in: {}, out: {}'.format(in_cnt, out_cnt)
                title += ', IS: {:.2f}'.format(g[id_to_node[id]].instability)

                text(x, y, 
                    title, 
                    fontsize=max(mn_font_size, mx_font_size*((degrees[id] + 5)/(mxd + 5))), 
                    color=font_colors[id],
                    ha='center', va='center')
            except TypeError:
                print('EXCEPTION: TypeError')
                print(id)
                print(id_to_node[id])
                print(id_to_node)
                sys.exit()

        #nx.draw_random(ng, node_size=node_sizes, labels=id_to_node, with_labels=True)    
        plt.show()

    @staticmethod
    def get_trace(graph, node: "start node"):
        """
        @param[in] graph {"node_name": ModuleInfo, ...}
        @retval {(u1, v1), (u2, v2), ...}
        """
        trace = set()
        q = [node]
        visited = set(node)

        while q:
            u = q.pop(0)

            for v in graph[u].fan_outs:
                trace.add((u, v))

            for v in graph[u].fan_outs:
                if v in visited:
                    continue

                visited.add(v)
                q += v,
            
        return trace
    
    @staticmethod
    def print_trace(graph, node: "start node"):
        """
        @param[in] graph {"node_name": ModuleInfo, ...}
        """
        q = [(node, 0)]
        visited = set(node)

        while q:
            u, depth = q.pop(0)
            print('--'*depth + '> ' + u)
            
            for v in graph[u].fan_outs:
                print('--'*(depth + 1) + '> ' + v)    

            for v in graph[u].fan_outs:
                if v in visited:
                    continue

                visited.add(v)
                q += (v, depth + 1),
        print()


