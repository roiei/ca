import collections
import json
from pprint import pprint


class DependencyConfig:
    def __init__(self):
        self.cfg = collections.defaultdict(None)

    def __del__(self):
        pass

    def set_edge_color(self, value):
        self.cfg['edge_color'] = value

    def get_edge_color(self):
        return self.cfg['edge_color']

    def set_max_font_size(self, value):
        self.cfg['max_font_size'] = value

    def get_max_font_size(self):
        return self.cfg['max_font_size']

    def set_min_font_size(self, value):
        self.cfg['min_font_size'] = value

    def get_min_font_size(self):
        return self.cfg['min_font_size']

    def set_fan_in_weight(self, value):
        self.cfg['fan_in_weight'] = value

    def get_fan_in_weight(self):
        return self.cfg['fan_in_weight']

    def set_node_size_weight(self, value):
        self.cfg['node_size_weight'] = value

    def get_node_size_weight(self):
        return self.cfg['node_size_weight']

    def set_activated_edges(self, value):
        self.cfg['activated_edges'] = value

    def get_activated_edges(self):
        return self.cfg['activated_edges']


class DependencyConfigReader:
    def __init__(self, cfg_url):
        self.cfg_url = cfg_url

    def __del__(self):
        pass

    def readAsText(self):
        lines = None
        with open(self.cfg_url, 'r') as fin:
            lines = fin.readlines()
        return lines

    def readAsJSON(self):
        with open(self.cfg_url) as fp:
            return json.load(fp)
        return None

    def getConfig(self, cfg_json):
        cfg = DependencyConfig()
        if 'edge_color' in cfg_json:
            cfg.set_edge_color(cfg_json["edge_color"])

        if 'max_font_size' in cfg_json:
            cfg.set_max_font_size(cfg_json["max_font_size"])

        if 'min_font_size' in cfg_json:
            cfg.set_min_font_size(cfg_json["min_font_size"])

        if 'fan_in_weight' in cfg_json:
            cfg.set_fan_in_weight(cfg_json["fan_in_weight"])

        if 'node_size_weight' in cfg_json:
            cfg.set_node_size_weight(cfg_json["node_size_weight"])

        if 'activated_edges' in cfg_json:
            cfg.set_activated_edges(cfg_json["activated_edges"])

        return cfg
