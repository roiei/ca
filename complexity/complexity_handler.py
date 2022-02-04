from cmd_interface import *
from util.util_file import *
from syntax_parser.syntax_parser_factory import *
from design_verification.verify import *
from util.util_file import *



class ComplexityAnalysisHandler(Cmd):
    def __init__(self):
        self.calc_funcs = {
            'McCabe': self.calc_cyclomatic
        }

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        depth = int(opts['depth']) if 'depth' in opts else None

        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), depth, ['cpp'])
        if not locations:
            return False, None

        parsers = SyntaxParserFactory.get_parsers(['cpp', 'hpp'])

        # for directory, files in locations.items():
        #     print('dir = ', directory)
        #     for file, file_type in files:
        #         print('file = ', file)

        # sys.exit()

        for directory, files in locations.items():
            print('dir = ', directory)
            if not files:
                continue

            for file, file_type in files:
                print('file = ', file)
                file_ext_name = UtilFile.get_extension_name(file_type)
                ext = UtilFile.get_extension(file)
                if ext not in parsers:
                    print(ext, 'not in parsers')
                    continue

                parser = parsers[ext]
                #methods_complexity = self.process_functions(file, parser, self.calc_cyclomatic)
                methods_complexity = self.process_functions_with_clang(file, parser, self.calc_cyclomatic)
                self.print_methods_complexity(methods_complexity)

                # for method in methods:
                #     for func_name, calc_func in self.calc_funcs.items():
                #         calc_func(method)
                print()

            print()

        return True, None

    def print_func_code(self, name, code):
        print('-'*20)
        print('name = ', name)
        print(code)
        print('-'*20, end='\n')

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

            #print('clz code = ', clz_codes[clz].code)

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
            # print('>'*30)
            # print('name = ', method_name)
            # print(code_blk)
            # print('>'*30)
            # print()

            res += (method_name, handler(code_blk)),

        return res

    def process_functions_with_clang(self, file, parser, handler):
        func_infos = parser.get_func_infos(file)
        if not func_infos:
            print('no func info')
            return None

        code = parser.get_code(file);
        if not code:
            print('no code in file ', file)
            return None

        res = []
        pos_line = parser.get_line_pos(code)

        for spelling, dispname, line, sline, eline in func_infos:
            spos = parser.find_pos(pos_line, sline, -1)
            epos = parser.find_pos(pos_line, eline)

            #print(sline, eline)
            #print('spos = ', spos)
            #print('pos = ', spos, epos)
            func_code = code[spos:epos + 1]
            res += (method_name, handler(code_blk)),

            self.print_func_code(spelling, func_code)

        return res

    def print_methods_complexity(self, complexity_info):
        if not complexity_info:
            return
        for i, (name, complexity) in enumerate(complexity_info):
            print('name = ', name, ', compl = ', complexity)

    def calc_cyclomatic(self, code):
        #print('+')
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
                        #print('dete = ', code[i] + code[i + 1])
                        complexity += 1
                        expr = ''
                        i += 1
                    elif i - 1 >= 0 and code[i - 1] == letter:
                        #print('dete = ', code[i - 1] + code[i])
                        complexity += 1
                        expr = ''
            elif ' ' != code[i] and not code[i].isalpha():
                if expr and expr[-1].isalpha():
                    #print('expr = ', expr)
                    if expr in branch_exprs:
                        #print('dete = ', expr)
                        complexity += 1
                    expr = ''
            elif code[i].isalpha():
                if expr and not expr[-1].isalpha():
                    #print('expr = ', expr)
                    if expr in branch_exprs:
                        #print('dete = ', expr)
                        complexity += 1
                    expr = ''
            elif code[i] == ' ':
                if code[i - 1].isalpha():
                    if expr in branch_exprs:
                        #print('dete = ', expr)
                        complexity += 1
                    expr = ''

            expr += code[i]
            i += 1

        return complexity
