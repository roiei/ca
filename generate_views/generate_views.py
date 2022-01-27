from cmd_interface import *
from util.util_file import *
import json


class ViewGenerationHandler(Cmd):
    def __init__(self):
        pass

    def execute(self, opts, cfg):
        if "input" not in opts:
            return False, None
        
        data = UtilFile.read_json_at_cur_dir(opts["input"])
        layer_info = self.parse_input(data)
        uml_code = self.create_view(layer_info)
        if not UtilFile.save_as_file(opts['output'], uml_code):
            print('ERROR file save')
            return False, None

        return True, None
    
    def get_valid_text_only(self, word):
        return word.replace('-', '_')
    
    def create_view(self, layer_info):
        output = '@startuml' + '\n'

        for layer, category_info in layer_info.items():
            print('layer = ', layer)
            output += 'rectangle' + ' ' + layer + ' {' + '\n'
            for category, items in category_info.items():
                print('category = ', category)
                #print('items = ', items)
                output += ' '*4 + 'rectangle' + ' ' + category + ' {' + '\n'
                for item in items[0]:
                    item = self.get_valid_text_only(item)
                    print('item = ', item)
                    output += ' '*4*2 + 'component' + ' ' + item + '\n'
                output += ' '*4 + '}' + '\n'
            output += '}' + '\n'
        
        output += '@enduml'
        return output
    
    def parse_input(self, data):
        layers = ['ccos.app']

        layer_info = collections.defaultdict(lambda: collections.defaultdict(list))

        for layer in layers:
            category_items = data['ccos.app']

            for category, items in category_items.items():
                layer_info[layer][category] += items,
        
        return layer_info
    
