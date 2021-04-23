import matplotlib.pyplot as plt
from matplotlib.pyplot import figure, text
import np
import sys, networkx as nx, matplotlib.pyplot as plt
import collections


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
    def draw_layered_diagram(g, links):
        #nodes = ['APP1', 'APP2', 'lib1', 'lib2', 'APP3']
        #links = [('APP1', 'lib1'), ('APP1', 'lib2'), ('APP2', 'lib1'), ('APP3', 'lib1')]

        node_to_id = collections.defaultdict(str)
        id_to_node = collections.defaultdict(int)
        nodes = g.keys()

        for id, node in enumerate(nodes):
            id_to_node[id] = node
            node_to_id[node] = id

        cur_id = id + 1
        not_in_nodes = []
        for u, v in links:
            if u not in node_to_id:
                id_to_node[cur_id] = u
                node_to_id[u] = cur_id
                cur_id += 1

            if v not in node_to_id:
                id_to_node[cur_id] = v
                node_to_id[v] = cur_id
                cur_id += 1

        edges = []
        for link in links:
            u, v = link
            edges += (node_to_id[u], node_to_id[v]),

        inbound = collections.defaultdict(int)
        for u, v in edges:
            inbound[v] += 1

        node_sizes = []
        node_colors = []
        font_colors = collections.defaultdict(str)

        for n in id_to_node.keys():
            node_sizes += inbound[n]*100,
            weight = (inbound[n]*10)
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
                depth_nodes[g[node].depth] += id,

        # for depth, nodes in depth_nodes.items():
        #     print(depth)
        #     print(nodes)
        # sys.exit()

        for depth, nodes in depth_nodes.items():
            ng.add_nodes_from(nodes, layer=depth)

        ng.add_edges_from(edges)

        #pos = nx.complete_multipartite_graph(ng)
        #nx.draw(ng, pos, node_color=color, with_labels=False)

        pos = nx.multipartite_layout(ng, subset_key="layer", scale=5)
        #print(pos)

        array_op = lambda x, weight: np.array([x[0]*weight, x[1]*weight])
        pos = {id: array_op(coord, 3) for id, coord in pos.items()}

        #print(pos)
        #plt.figure(figsize=(180, 180))

        nx.draw(ng, pos, 
            node_size=node_sizes, 
            node_color=node_colors,
            edge_color='#C1F4FF',
            labels=id_to_node, 
            with_labels=False)

        degrees = dict(ng.degree)

        mnd = min(degrees.values())
        mxd = max(degrees.values())

        mx_font_size = 20
        mn_font_size = 7

        for id, (x, y) in pos.items():
            in_cnt = len(g[id_to_node[id]].fan_ins)
            out_cnt = len(g[id_to_node[id]].fan_outs)
            text(x, y, 
                id_to_node[id] + ' > in: {}, out: {}'.format(in_cnt, out_cnt), 
                fontsize=max(mn_font_size, mx_font_size*((degrees[id] + 5)/(mxd + 5))), 
                color=font_colors[id],
                ha='center', va='center')

        #nx.draw_random(ng, node_size=node_sizes, labels=id_to_node, with_labels=True)    
        plt.show()
