import collections
from module_types import *
import re


class CMakeBuildScriptParser:
    types = {
        "APP_NAME": ("APP", 0),
        "LIB_NAME": ("LIB", 1),
        "SERVICE_NAME": ("SVC", 2)
    }

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
        output_name = ''
        if '${PROJECT_NAME}' == name:
            pattern = re.compile('project\s*\(\s*[\w]+\s*\)')
            m = pattern.search(content)
            if m:
                print(m)
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
        value = CMakeBuildScriptParser.types.get(type_str, ('NONE', 10))
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

    @staticmethod
    def _parse_outputname(line, g, param, url, content):
        #print('line = ', line)
        sx = line.find('(')
        ex = line.rfind(')')
        if sx != -1 and sx < ex:
            line = line[sx + 1: ex]
        words = line.split()
        try:
            type_str, name = words
        except ValueError:
            print(url)
            print(line)
            print(words)
            sys.exit()

        type_str = type_str.strip()
        name = name.strip()

        if name in g:
            print('name {} already exist'.format(name))
            return

        type, depth = CMakeBuildScriptParser._get_module_info(type_str, name)
        #print('type = {}, name = {}, depth = {}'.format(type, name, depth))
        if not type:
            #print('name {}: cannot find type {}'.format(name, type_str))
            return

        print('type = {}, name = {}, depth = {}'.format(type, name, depth))

        if name.startswith('$'):
            name = CMakeBuildScriptParser._find_output_name(url, name, content)

        if not name:
            print('ERROR: could not find name = {}'.format(name))
            return

        g[name] = ModuleInfo()
        g[name].name = name
        g[name].type = type
        g[name].depth = depth
        return name

    @staticmethod
    def _parse_dependency(line, g, param, url):
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

            filtered += item,
            if 'LDFLAGS' in item:
                ex = item.rfind('_LDFLAGS')
                item = item[:ex].lower()

            if '' == item or not item:
                print('1. empty string')

            g[param].fan_outs.add(item)

        #print(filtered)
        #print(param, ' = ', g[param].fan_outs)

    pattern_handlers = {
        'dependency':
            ('target_link_libraries\s*\([\w$\s{}+]*\)',
            _parse_dependency.__func__)
    }


    def __init__(self):
        pass

    def get_content(self, url):
        lines = None
        with open(url, 'r', encoding='utf8') as f:
            lines = f.readlines()

        return ''.join(lines)

    def build_dep_graph(self, url):
        content = self.get_content(url)
        if not content:
            return

        g = collections.defaultdict(ModuleInfo)
        oname = ''

        #pattern = re.compile('set\([A-Z_]+\s+[\w]+\)')
        pattern = re.compile('set\([A-Z_]+\s+[._${}\w]+\)')
        m = pattern.finditer(content)
        for r in m:
            span = r.span()
            #print(content[span[0]:span[1]])
            res = CMakeBuildScriptParser._parse_outputname(
                content[span[0]:span[1]], g, oname, url, content)

            if '' != res and None != res:
                oname = res

        if '' == oname:
            #print('UNDEF: url = ', url)
            return

        for pname, value in CMakeBuildScriptParser.pattern_handlers.items():
            pattern_str, _handler = value
            pattern = re.compile(pattern_str)

            m = pattern.finditer(content)
            for r in m:
                span = r.span()
                name = _handler(content[span[0]:span[1]], g, oname, url)
        
        return g
