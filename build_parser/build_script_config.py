import json


class BuildScriptConfig:
    def __init__(self, url):
        self.data = self.__read_json_cfg(url)
    
    def __del__(self):
        pass
    
    def __read_json_cfg(self, url):
        with open(url) as fp:
            return json.load(fp)
        return None
    
    def get_output_pattern(self, prj):
        if 'output_pattern' not in self.data:
            return None
        
        if None == prj or prj not in self.data['output_pattern']:
            return self.data['output_pattern']['default']
        
        return self.data['output_pattern'][prj]

