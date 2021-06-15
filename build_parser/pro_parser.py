import collections
from common.module_types import *
from util.util_file import *
import re


class ProBuildScriptParser:
    def __init__(self):
        pass

    @staticmethod
    def _add_dependency_libs(line, g, param, url):
        line = line.strip()
        if line.startswith('#'):
            return

        line = line.split('+=')[-1].strip()
        items = line.split(' -')

        nitems = []
        for item in items:
            if item.startswith('-L'):
                continue

            item = item.strip()
            i = 0
            while i < len(item):
                if not item[i].isalpha():
                    break
                i += 1
            nitems += item[1:i],

        items = nitems

        # print('line = ', line)
        # print('items =', items)
        # sys.exit()
        for item in items:
            g[param].fan_outs.add(item)
    
    @staticmethod
    def _add_dependency_pkgs(line, g, param, url):
        line = line.strip()
        line = line.split('+=')[-1].strip()
        items = [item.strip() for item in line.split()]

        nitems = []
        for item in items:
            if item.startswith('-L'):
                continue

            i = 0
            while i < len(item):
                if not item[i].isalpha():
                    break
                i += 1
            nitems += item[:i],

        items = nitems

        for item in items:
            g[param].fan_outs.add(item)

    pattern_handlers = {
        'dependency':
            ('LIBS\s*\+=[][$/}{\w\s-]*\n',
            _add_dependency_libs.__func__),
        'pkg_dependency': 
            ('PKGCONFIG\s*\+=[][$/}{\w\s-]*\n', 
            _add_dependency_pkgs.__func__)
    }

    def remove_comment(self, content):
        content = re.compile("#.*").sub("", content)
        return content

    def build_dep_graph(self, url, dep_cfg, prj):
        prefix = dep_cfg.get_prefix()['app'][prj]
        if prefix not in url:
            return None

        content = UtilFile.get_content(url)
        if not content:
            return
        
        content = self.remove_comment(content)
        g = collections.defaultdict(ModuleInfo)

        oname = self.add_output_module(g, content, url)

        #print('url = ', url, 'oname = ', oname)

        if '' == oname:
            #print('UNDEF: url = ', url)
            return
        
        #print('pro = ', oname)

        for pname, value in ProBuildScriptParser.pattern_handlers.items():
            pattern_str, _handler = value
            pattern = re.compile(pattern_str)

            m = pattern.finditer(content)
            for r in m:
                span = r.span()
                name = _handler(content[span[0]:span[1]], g, oname, url)

        return g

    def add_output_module(self, g, content, url):
        """
            add output module to the given graph
        """
        type_str = self.find_module_type(content)
        if not type_str:
            print('Pro: No type', url)
            return ''

        name = self.find_module_name(content, g, url)
        if name in g:
            print('name {} already exist'.format(name), url)
            return ''

        type, depth = self.get_module_info(type_str, name, url)
        if not type:
            #print('name {}: cannot find type {}'.format(name, type_str))
            return ''

        if not name:
            print('Pro:ERROR: could not find name = {}'.format(name), url)
            return ''

        #print('type = {}, name = {}, depth = {}'.format(type, name, depth))
        
        g[name] = ModuleInfo()
        g[name].name = name
        g[name].type = type
        g[name].depth = depth
        g[name].url = url

        #print('type = {}, name = {}'.format(type, name))
        return name

    def find_module_type(self, content):
        pattern = re.compile('TEMPLATE\s*=\s*[\w]+')
        m = pattern.search(content)
        if not m:
            return None

        type = ''
        words = m.group().split('=')
        words = [word.strip() for word in words]
        #print(words)
        if words[0] == 'TEMPLATE':
            type = words[1]

        return type

    def find_module_name(self, content, g, url):
        pattern = re.compile('TARGET\s*=\s*[\w]+')
        m = pattern.finditer(content)
        for r in m:
            span = r.span()
            sx, ex = span[0], span[1]
            res = self._parse_outputname(
                content[sx:ex], g, url, content)

            if '' != res and None != res:
                return res

        return ''

    types = {
        "app": ("HMI_APP", 0),      # HMI app component level
        "lib": ("HMI_LIB", 1)       # UI library module level
    }

    def get_module_info(self, type_str, name, url):
        #print('type = ', type_str)
        #print('name = ', name)
        #print('url = ', url)

        type, depth = ProBuildScriptParser.types.get(type_str, ('NONE', -1))
        if type == 'NONE':
            return '', 0

        return type, depth

    def _parse_outputname(self, line, g, url, content):
        #TARGET = ccshmi
        words = line.split('=')
        words = [word.strip() for word in words]
        #print('words = ', words)

        #if 'hcloud' == words[-1]:
            #print(url)
            #sys.exit()

        try:
            _, name = words
        except ValueError:
            print('ValueError: exception')
            print('\t', url)
            print('\t', line)
            print('\t', words)
            sys.exit()

        return name
