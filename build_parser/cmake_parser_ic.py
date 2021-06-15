import collections
from common.module_types import *
from build_parser.build_script_config import *
from util.util_file import *
import re


class CMakeBuildScriptParserIC:
    types = {
        "app": ("APP", 2),         # app module level
        "api": ("LIB", 3),         # API module level
        "service": ("SVC", 4),     # SVC module level
        "hal": ("HAL", 5) 
    }

    cfg = None
    prj = None

    @staticmethod
    def init(prj):
        CMakeBuildScriptParserIC.prj = prj
        url = os.path.dirname(os.path.realpath(__file__)) + \
            PlatformInfo.get_delimiter() + 'cfg_build_parse.json'
        CMakeBuildScriptParserIC.cfg = BuildScriptConfig(url)

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
        str_out_pat = CMakeBuildScriptParserIC.cfg.get_output_pattern(CMakeBuildScriptParserIC.prj)
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
        value = CMakeBuildScriptParserIC.types.get(type_str, ('NONE', -1))
        type, depth = value
        if type == 'NONE':
            return '', 0

        sub_type, sub_depth = \
            CMakeBuildScriptParserIC._parse_module_type(name)

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
        #print(line)

        name = line.lower()
        if name in g:
            print('name {} already exist'.format(name))
            return None, None

        words = url.split(PlatformInfo.get_delimiter())
        type = None
        depth = -1
        for word in words:
            if word in CMakeBuildScriptParserIC.types:
                type, depth = CMakeBuildScriptParserIC.types[word]

        if not type:
            #print('name {}: cannot find type {}'.format(name, type_str))
            return None, None

        name = self._replace_define_to_actual_name(name, line, content)

        g[name] = ModuleInfo()
        g[name].name = name
        g[name].type = type
        g[name].depth = depth
        g[name].url = url
        return name, line
    
    def _replace_define_to_actual_name(self, name, def_name, content):
        pattern = re.compile('set\s*\(\s*{}\s+[\w]+\s*\)'.format(def_name))
        m = pattern.finditer(content)
        target_name = ''

        for r in m:
            span = r.span()
            line = content[span[0]:span[1]]
            sx = line.find('(')
            ex = line.rfind(')')
            words = line[sx + 1:ex].split()
            target_name = words[-1]
            break

        if target_name:
            name = target_name.lower()

        return name

    @staticmethod
    def _parse_dependency(line, g, oname, ori_oname, url):
        sx = line.find('(')
        ex = line.rfind(')')
        content = line[sx + 1:ex].split()
        filtered = []

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

            if item == ori_oname:
                continue

            if item.endswith('_LIB_NAME'):
                ex = item.rfind('_LIB_NAME')
                item = item[:ex].lower()

            filtered += item,
            if 'LDFLAGS' in item:
                ex = item.rfind('_LDFLAGS')
                item = item[:ex].lower()

            if '' == item or not item:
                print('1. empty string')

            g[oname].fan_outs.add(item)

        #print(filtered)
        #print(oname, ' = ', g[oname].fan_outs)

    pattern_handlers = {
        'dependency':
            ('target_link_libraries\s*\(\n*[\w\s$\-\.#\/_s{}\n+]*\s*\n*\)',
            _parse_dependency.__func__),
        'dependency_uppercase':
            ('TARGET_LINK_LIBRARIES\s*\(\n*[\w\s$\-\.#\/_s{}\n+]*\s*\n*\)',
            _parse_dependency.__func__)
    }

    def __init__(self):
        pass

    def add_output_module(self, g, content, url):
        """
            add output module to the given graph
        """

        patts = ['project\s*\(\s*[\w]+\s*\)', 'PROJECT\s*\(\s*[\w]+\s*\)']
        res = ''
        oname = ''

        for patt in patts:
            pattern = re.compile(patt)
            m = pattern.finditer(content)
            for r in m:
                span = r.span()
                res, oname = self._parse_outputname(
                    content[span[0]:span[1]], g, url, content)

                if '' != res and None != res:
                    break
            
            if '' != res and None != res:
                break
        
        return res, oname

    def build_dep_graph(self, url):
        content = UtilFile.get_content(url)
        if not content:
            return

        g = collections.defaultdict(ModuleInfo)
        oname, ori_oname = self.add_output_module(g, content, url)

        if '' == oname:
            #print('UNDEF: url = ', url)
            return
        
        for pname, value in CMakeBuildScriptParserIC.pattern_handlers.items():
            pattern_str, _handler = value
            pattern = re.compile(pattern_str)

            m = pattern.finditer(content)
            for r in m:
                span = r.span()
                name = _handler(content[span[0]:span[1]], g, oname, ori_oname, url)

        return g
    
    def replace_macro_dep(self, g, module_infos):
        #print("+replace")
        for u, info in g.items():
            if 'CCOSAPI_LIBRARIES' in info.fan_outs:
                #print(u, end='\n')
                info.fan_outs.remove('CCOSAPI_LIBRARIES')
                for module in module_infos['LIB']:
                    info.fan_outs.add(module)


    
    


