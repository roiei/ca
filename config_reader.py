import collections
import json
from pprint import pprint


class Config:
    def __init__(self):
        self.cfg = collections.defaultdict(None)
        self.cfg['recursive'] = True
        self.cfg['print_opt'] = ['print_analysis_table']

    def set_recursive(self, on):
        self.cfg['recursive'] = on

    def get_recursive(self):
        return self.cfg['recursive']

    def set_recursive_depth(self, depth):
        self.cfg['recursive_depth'] = depth

    def get_recursive_depth(self):
        return self.cfg['recursive_depth']

    def set_type(self, type):
        self.cfg['type'] = type

    def get_type(self):
        return self.cfg['type']

    def set_extensions(self, extensions):
        self.cfg['extensions'] = extensions

    def get_extensions(self):
        return self.cfg['extensions']

    def set_rules(self, rules):
        self.cfg['rules'] = rules

    def get_rules(self):
        return self.cfg['rules']

    def set_suffix_filter_names(self, names):
        self.cfg['filter_suffix_name'] = names

    def get_suffix_filter_names(self):
        return self.cfg['filter_suffix_name']

    def set_filter_keyword(self, names):
        self.cfg['filter_keyword'] = names

    def get_filter_keyword(self):
        return self.cfg['filter_keyword']

    def set_print_opt(self, opt):
        self.cfg['print_opt'] = opt

    def get_print_opt(self):
        return self.cfg['print_opt']

    def isAnalysisReportOn(self):
        return 'print_analysis_table' in self.cfg['print_opt']

    def isDetailReportOn(self):
        return 'print_details' in self.cfg['print_opt']

    def set_num_of_public_func(self, num_pub_func):
        self.cfg['num_pub_func'] = num_pub_func

    def get_num_of_public_func(self):
        return self.cfg['num_pub_func']

    def set_num_of_params(self, num_params):
        self.cfg['num_params'] = num_params

    def get_num_of_params(self):
        return self.cfg['num_params']

    def set_jsonoutput_on(self, onoff):
        self.cfg['json_output'] = onoff

    def get_jsonoutput_on(self):
        return self.cfg['json_output']

    def set_duplicated_param_permitted(self, onoff):
        self.cfg['permite_duplicate_param'] = onoff
    
    def is_duplicate_param_permitted(self):
        return self.cfg['permite_duplicate_param']
    
    def set_ignore_deleted_method(self, onoff):
        self.cfg['ignore_deleted_method'] = onoff
    
    def is_deleted_method_ignorable(self):
        return self.cfg['ignore_deleted_method']
    
    def set_doxy_start_pattern(self, onoff):
        self.cfg['doxy_start_pattern'] = onoff
    
    def get_doxy_start_pattern(self):
        return self.cfg['doxy_start_pattern']
    
    def set_ignore_acc_mod(self, acc_mods):
        self.cfg['igore_comment_in_acc_mod'] = acc_mods
    
    def get_ignore_acc_mod(self):
        return self.cfg['igore_comment_in_acc_mod']
    
    def set_enum_cfg(self, enum_cfg):
        self.cfg['enum_cfg'] = enum_cfg

    def get_enum_guard_keywords(self):
        return self.cfg['enum_cfg']['guardian_keyword']
    
    def get_enum_rules(self):
        return self.cfg['enum_cfg']['rules']


class ConfigReader:
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
        cfg = Config()
        if 'recursive' in cfg_json:
            cfg.set_recursive(cfg_json["recursive"])

        if 'recursive_depth' in cfg_json:
            cfg.set_recursive_depth(cfg_json["recursive_depth"])

        if 'type' in cfg_json:
            cfg.set_type(cfg_json["type"])

        if 'extensions' in cfg_json:
            cfg.set_extensions(cfg_json["extensions"])

        if 'rules' in cfg_json:            
            cfg.set_rules(cfg_json["rules"])
        
        if 'print_opt' in cfg_json:
            cfg.set_print_opt(cfg_json["print_opt"])

        if 'filter_suffix_name' in cfg_json:
            cfg.set_suffix_filter_names(cfg_json["filter_suffix_name"])

        if 'filter_keyword' in cfg_json:
            cfg.set_filter_keyword(cfg_json["filter_keyword"])
        
        if 'enum_cfg' in cfg_json:
            cfg.set_enum_cfg(cfg_json["enum_cfg"])

        if 'modular_matrices' in cfg_json:
            cfg.set_num_of_public_func(cfg_json["modular_matrices"]["num_of_public_func"])
            cfg.set_num_of_params(cfg_json["modular_matrices"]["num_of_params"])

        if 'json_output' in cfg_json:
            cfg.set_jsonoutput_on(cfg_json["json_output"])

        if 'doxygen' in cfg_json:
            if 'permite_duplicate_param' in cfg_json['doxygen']:
                cfg.set_duplicated_param_permitted(cfg_json['doxygen']['permite_duplicate_param'])
        
        if 'doxygen' in cfg_json:
            if 'ignore_deleted_method' in cfg_json['doxygen']:
                cfg.set_ignore_deleted_method(cfg_json['doxygen']['ignore_deleted_method'])
        
        if 'doxygen' in cfg_json:
            if 'doxy_start_pattern' in cfg_json['doxygen']:
                cfg.set_doxy_start_pattern(cfg_json['doxygen']['doxy_start_pattern'])
        
        if 'doxygen' in cfg_json:
            if 'igore_comment_in_acc_mod' in cfg_json['doxygen']:
                cfg.set_ignore_acc_mod(cfg_json['doxygen']['igore_comment_in_acc_mod']) 

        return cfg
