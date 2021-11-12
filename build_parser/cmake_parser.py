import collections
from common.module_types import *
from build_parser.build_script_config import *
from util.util_file import *
import re


class CMakeBuildScriptParser:
    types = {
        "APP_NAME": ("APP", 2),         # app module level
        "LIB_NAME": ("LIB", 3),         # API module level
        "SERVICE_NAME": ("SVC", 4),     # SVC module level
        "service": ("SVC", 4)
    }

    cfg = None
    prj = None

    @staticmethod
    def init(prj):
        CMakeBuildScriptParser.prj = prj
        url = os.path.dirname(os.path.realpath(__file__)) + \
            PlatformInfo.get_delimiter() + 'cfg_build_parse.json'
        CMakeBuildScriptParser.cfg = BuildScriptConfig(url)

    @staticmethod
    def _parse_module_type(name):
        module_types = {
            'hal': ('HAL', 3)
        }

        for type_name, type_info in module_types.items():
            if type_name in name:
                return type_info

        return '', 0

    @staticmethod
    def _find_output_name(url, name, content):
        str_out_pat = CMakeBuildScriptParser.cfg.get_output_pattern(CMakeBuildScriptParser.prj)
        output_name = ''
        if name.endswith('_NAME}'):
            pattern = re.compile(str_out_pat)
            m = pattern.search(content)
            if m:
                sx, ex = m.span()                
                output_name = content[sx:ex + 1]
                sx = output_name.find('(')
                ex = output_name.rfind(')')
                output_name = output_name[sx + 1:ex].strip()
                #print(output_name)

        return output_name

    @staticmethod
    def _get_module_info(type_str, name):
        #print('type = ', type_str, 'name = ', name)
        value = CMakeBuildScriptParser.types.get(type_str, ('NONE', -1))
        type, depth = value
        if type == 'NONE':
            return '', 0

        sub_type, sub_depth = \
            CMakeBuildScriptParser._parse_module_type(name)

        if sub_type:
            type += ':' + sub_type
            depth = sub_depth

        # print(type, depth)
        # print()

        return type, depth

    def _parse_outputname(self, line, g, url, content):
        #print('line = ', line)
        sx = line.find('(')
        ex = line.rfind(')')
        if sx != -1 and sx < ex:
            line = line[sx + 1: ex]
        words = line.split()
        type_str = ''
        try:
            if words and len(words) == 1:
                name = words[0]
            else:
                type_str, name = words
        except ValueError:
            print('Exit...')
            print(url)
            print(line)
            print(words)
            sys.exit()
        
        def parse_type_from_url(url):
            chunks = url.split('.')
            for chunk in chunks:
                if chunk in ['service']:
                    return chunk
            return ''
        
        type_str = type_str.strip()
        name = name.strip()

        if name in g:
            print('name {} already exist'.format(name))
            return

        type, depth = CMakeBuildScriptParser._get_module_info(type_str, name)
        
        if not type_str or not type:
            type_str = parse_type_from_url(url.split(PlatformInfo.get_delimiter())[-2])
            type, depth = CMakeBuildScriptParser._get_module_info(type_str, name)

        res_name = name
        if name.startswith('$'):
            name = res_name = CMakeBuildScriptParser._find_output_name(url, name, content)

        if not res_name:
            print('cmake:ERROR: could not find name = {}'.format(name), url)
            return

        g[name] = ModuleInfo()
        g[name].name = res_name
        g[name].type = type
        g[name].depth = depth
        g[name].url = url
        return res_name

    @staticmethod
    def _parse_dependency(line, g, param, url):
        sx = line.find('(')
        ex = line.rfind(')')
        content = line[sx + 1:ex].split()
        filtered = []


        print(content)

        for item in content:
            if item in {'${LIB_NAME}', 'PRIVATE', 
                '${APP_NAME}', '${PROJECT_NAME}', 
                '${LIBRARY_NAME}', 'SHARED', 
                '${STATICLIB_NAME}', 'STATIC',
                '${SERVICE_NAME}'}:
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

            g[param].fan_outs.add(item)

        print(filtered)
        print(param, ' = ', g[param].fan_outs)

    pattern_handlers = {
        'dependency':
            ('target_link_libraries\s*\([\w$\s{}+_]*\)',
            _parse_dependency.__func__),
        'dependency':
            ('link_directories\s*\([\w$\s{}+_]*\)',
            _parse_dependency.__func__)
    }

    def __init__(self):
        pass

    def add_output_module(self, g, content, url):
        """
            add output module to the given graph
        """
        for patt in ['project\s*\(\s*[a-zA-Z_]+\s*\)', 'set\([A-Z_]+\s+[._${}\w]+\)']:
            pattern = re.compile(patt)
            m = pattern.finditer(content)
            for r in m:
                span = r.span()
                #print(content[span[0]:span[1]])
                res = self._parse_outputname(
                    content[span[0]:span[1]], g, url, content)

                if '' != res and None != res:
                    return res
        
        return ''

    def build_dep_graph(self, url):
        content = UtilFile.get_content(url)
        if not content:
            return

        g = collections.defaultdict(ModuleInfo)
        oname = self.add_output_module(g, content, url)
        print('cmake = ', oname)
        print(url)

        if '' == oname:
            print('UNDEF: url = ', url)
            return
        
        for pname, value in CMakeBuildScriptParser.pattern_handlers.items():
            print('---')
            pattern_str, _handler = value
            pattern = re.compile(pattern_str)

            m = pattern.finditer(content)
            for r in m:
                span = r.span()
                name = _handler(content[span[0]:span[1]], g, oname, url)
        
        print('===')
        return g
    
    def replace_macro_dep(self, g, module_infos):
        for u, info in g.items():
            if 'CCOSAPI_LIBRARIES' in info.fan_outs:
                info.fan_outs.remove('CCOSAPI_LIBRARIES')
                for module in module_infos['LIB']:
                    info.fan_outs.add(module)
