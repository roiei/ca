import os
import collections
import typing
from cmd_interface import Cmd
from syntax_parser import SyntaxParserFactory
from config_reader import ConfigReader
from util import UtilFile
from util import PlatformInfo
from util import UtilPrint


class ComplexityInfo:
    def __init__(self, name, cplx, level):
        self.name = name
        self.cplx = cplx
        self.level = level


class ComplexityAnalysisHandler(Cmd):
    def __init__(self):
        self.calc_funcs = {
            'McCabe': self.calc_cyclomatic
        }

        deli = PlatformInfo.get_delimiter()
        self.cfg_reader = ConfigReader(
            os.path.dirname(os.path.realpath(__file__)) + 
            deli + '..' + deli  + 'config' + deli  + 'cfg_complexity.conf')
        self.cfg = self.cfg_reader.readAsJSON()

    def __del__(self):
        pass

    def execute(self, opts: typing.Dict, cfg) -> bool:
        depth = int(opts['depth']) if 'depth' in opts else None

        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), depth, ['cpp'])
        if not locations:
            return False, None

        parsers = SyntaxParserFactory.get_parsers(['cpp', 'hpp'], self.cfg["clang_lib_location"])
        levels = self.cfg['complexity_level']

        cplx_info = collections.defaultdict(lambda: collections.defaultdict(list))
        inc_paths = UtilFile.find_filtered_subdirs(opts["path"], None, ['hpp', 'h'])

        for directory, files in locations.items():
            if not files:
                continue

            for file, file_type in files:
                file_ext_name = UtilFile.get_extension_name(file_type)
                ext = UtilFile.get_extension(file)
                if ext not in parsers:
                    print(ext, 'not in parsers')
                    continue

                parser = parsers[ext]
                #methods_complexity = self.process_functions(file, parser, self.calc_cyclomatic)
                methods_complexity = \
                    self.process_functions_with_clang(
                        file, 
                        parser, 
                        self.calc_cyclomatic,
                        inc_paths)
                
                if not methods_complexity:
                    continue

                for i, (name, complexity) in enumerate(methods_complexity):
                    level = self.find_complexity_level(levels, complexity)
                    cplx_info[directory][file] += ComplexityInfo(name, complexity, level),

        self.print_complexity(cplx_info)
        return True

    def print_complexity(self, cplx_info):
        cols = ['func/method name', 'McCabe complexity', 'complexity level']
        col_widths = [30, 20, 20]

        for directory, files in cplx_info.items():
            print('directory = ', directory)

            for file, infos in files.items():
                rows = []
                for info in infos:
                    row = []
                    row += ('{:<12s}', info.name),
                    row += ('{:<12d}', info.cplx),
                    row += ('{:<5s}',  info.level),
                    rows += row,

                UtilPrint.print_lines_with_custome_lens(\
                    ' * complexity of file = {}'.format(file), 
                    col_widths, cols, rows)
                print()

    def find_complexity_level(self, levels, complexity):
        l = 0
        r = len(levels) - 1
        while l <= r:
            m = (l + r)//2
            if levels[m][1] == complexity:
                return levels[m]
            if levels[m][1] < complexity:
                l = m + 1
            else:
                r = m - 1

        return levels[l - 1][0]

    def print_func_code(self, name, code, code_type):
        print('func code', '-'*20)
        print('code_type = ', code_type)
        print('name = ', name)
        print('code = ')
        print(code)
        print('-'*30, end='\n')

    def process_functions(self, file, parser, handler):
        res = []
        code = parser.get_code(file);
        if not code:
            print('no code in file ', file)
            return None

        pos_line = parser.get_line_pos(code)
        found, clz_codes = parser.get_each_class_code(code, pos_line)

        clz_pos = []
        for clz in clz_codes:
            if not clz_codes[clz].code:
                continue

            clz_pos += (clz_codes[clz].start_pos, clz_codes[clz].end_pos),

        clz_pos.sort(key=lambda p: p[1], reverse=True)
        wo_clz_code = code
        
        print('clz_pos = ', clz_pos)

        for start, end in clz_pos:
            print('start line = ', start)
            print('end line   = ', end)
            wo_clz_code = wo_clz_code[:start] + wo_clz_code[end + 1:]

        method_codes = []
        for clz in clz_codes:
            if not clz_codes[clz].code:
                continue

            clz_code = parser.remove_access_modifier(clz_codes[clz].code)
            methods = parser.get_method_code_blocks(clz_code)

            for method_name, code_blk, code_start, code_end in methods:
                method_codes += (clz + '::' + method_name, code_blk),

        methods = parser.get_method_code_blocks(wo_clz_code)
        for method_name, code_blk, code_start, code_end in methods:
            method_codes += (method_name, code_blk),

        for method_name, code_blk in method_codes:
            res += (method_name, handler(code_blk)),

        return res

    def process_functions_with_clang(self, file, parser, handler, inc_paths):
        func_infos = parser.get_func_infos(file, inc_paths)
        if not func_infos:
            print('no func info')
            return None

        code = parser.get_code_lines(file)
        if not code:
            print('no code in file ', file)
            return None
        
        func_pos = self.filter_no_code_items(code, parser, func_infos)

        res = []
        del_len = 50
        func_pos.sort(key=lambda p: p[2])

        for spelling, dispname, line, spos, epos, code_type in func_pos:
            func_code = code[spos:epos + 1]
            res += (spelling, handler(func_code)),

        return res

    def filter_no_code_items(self, code, parser, func_infos):
        pos_line = parser.get_line_pos(code)
        func_pos = []

        for spelling, dispname, line, sline, eline, code_type in func_infos:
            spos = parser.find_pos(pos_line, sline, -1)
            epos = parser.find_pos(pos_line, eline)

            if spelling not in code:
                continue

            if sline < eline and spos < epos:
                func_pos += (spelling, dispname, line, spos, epos, code_type),

        return func_pos

    def process_functions_with_raw(self, file, parser, handler):
        code = parser.get_code(file);
        if not code:
            print('no code in file ', file)
            return None

        pos_line = parser.get_line_pos(code)

        func_infos = parser.get_func_infos_by_brace(code, pos_line)
        if not func_infos:
            print('no func info')
            return None

        res = []
        for method_name, start_line, func_code in func_infos:
            res += (method_name, handler(func_code)),

        return res

    def print_methods_complexity(self, complexity_info):
        if not complexity_info:
            return
        for i, (name, complexity) in enumerate(complexity_info):
            print('name = ', name, ', compl = ', complexity)

    def calc_cyclomatic(self, code):
        i = 0
        n = len(code)
        expr = ''
        branch_exprs = {'?', '||', 'catch', 'if', 'case', 'for', '&&', 'while'}
        complexity = 1

        while i < n:
            if code[i] == '?':
                complexity += 1
            elif code[i] == '|' or code[i] == '&':
                for letter in ['|', '&']:
                    if i + 1 < n and code[i + 1] == letter:
                        complexity += 1
                        expr = ''
                        i += 1
                    elif i - 1 >= 0 and code[i - 1] == letter:
                        complexity += 1
                        expr = ''
            elif ' ' != code[i] and not code[i].isalpha():
                if expr and expr[-1].isalpha():
                    if expr in branch_exprs:
                        complexity += 1
                    expr = ''
            elif code[i].isalpha():
                if expr and not expr[-1].isalpha():
                    if expr in branch_exprs:
                        complexity += 1
                    expr = ''
            elif code[i] == ' ':
                if code[i - 1].isalpha():
                    if expr in branch_exprs:
                        complexity += 1
                    expr = ''

            expr += code[i]
            i += 1

        return complexity
