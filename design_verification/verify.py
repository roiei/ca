from cmd_interface import *
import collections


class Report:
    def __init__(self, directory):
        self.directory = directory
        self.files = 0
        self.violate_files = 0
        self.num_classes = 0
        self.violate_classes = 0
        self.violate_cnt = 0


class FileResult:
    def __init__(self, name):
        self.name = name
        self.clzs = collections.defaultdict(list)
        self.clz_type = collections.defaultdict(str)
        self.num_missings = 0

    def __del__(self):
        pass

    def push_missing_infos(self, clz, clz_type, info):        
        self.clzs[clz] += info
        self.clz_type[clz] = clz_type
        self.num_missings += len(info)

    def get_clz_type(self, clz):
        if clz not in self.clz_type:
            return None

        return self.clz_type[clz]

    def get_missing_num(self):
        return self.num_missings

    def get_name(self):
        return self.name
