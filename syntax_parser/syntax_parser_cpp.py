import re
from syntax_parser.syntax_parser_factory import *
import collections
from syntax_parser.search_patterns_cpp import *
from config_reader import *
from file_info_types import *
from foundation.types import *
from util.util_log import *
from syntax_parser.cpp_parser import *
from syntax_parser.syntax_parser_cpp_com import *
from common.parsing_info_types import *
import clang.cindex
from clang.cindex import CursorKind


DEBUG_MSG_ON = False


class ClassCodeInfo:
    def __init__(self):
        self.code = ''
        self.start_line = 0
        self.start_pos = 0
        self.start_offset = 0
        self.end_line = 0
        self.end_pos = 0
        self.nested = False


class CppImplParser(SyntaxParser):
    def __init__(self, name, ctx=None):
        super().__init__(name)
        self.comm_cpp_parser = CommonCppParser()
        if not PlatformInfo.is_Linux() and ctx:
            clang.cindex.Config.set_library_file(ctx)
        self.target_cursors = {CursorKind.CONSTRUCTOR, 
            CursorKind.DESTRUCTOR, CursorKind.CXX_METHOD, CursorKind.FUNCTION_DECL}
        self.cursor_tbl = {
            CursorKind.DESTRUCTOR: CODE_TYPE.DESTRUCTOR,
            CursorKind.CONSTRUCTOR: CODE_TYPE.CONSTRUCTOR,
            CursorKind.CXX_METHOD: CODE_TYPE.METHOD,
            CursorKind.FUNCTION_DECL: CODE_TYPE.FUNC_DECL
        }

    def __del__(self):
        super().__del__()

    def get_code_without_comment(self, url):
        return CppParser.get_code_only(url)

    def get_loc(self, code):
        return self.comm_cpp_parser.get_loc(code)

    def find_method_calls(self, code):
        """
            return
                [(clz1, call1), (clz2, call2), ...]
        """
        calls = collections.defaultdict(int)
        pattern = re.compile('[\w]+(::|\.|->)[\w]+\s*\([\w\s,\"~]*\)\s*;')
        m = pattern.finditer(code)

        for r in m:
            span = r.span()
            sx, ex = span[0], span[1]
            part = code[sx:ex + 1]

            midx = part.find('::')
            if -1 == midx:
                midx = part.find('.')

            if -1 == midx:
                midx = part.find('->')

            caller = part[:midx]
            sx = midx

            while sx < ex and part[sx] in ':->.':
                sx += 1

            method = part[sx:ex + 1]
            ex = method.find('(')
            method = method[:ex]
            
            calls[caller + '::' + method] += 1
        
        return calls

    def get_code_lines(self, url):
        lines = []
        res = UtilFile.get_lines(url, lines, 'utf-8')

        if res == ReturnType.UNICODE_ERR:
            res = UtilFile.get_lines(url, lines, 'euc-kr')
        elif res != ReturnType.SUCCESS:
            return None

        if not lines:
            print('Err: not possible to read: ', url)
            return None

        return ''.join(lines)

    def remove_comment(self, code):
        return self.comm_cpp_parser.remove_comment(code)

    def get_code(self, url):
        lines = self.get_code_lines(url)
        code = self.remove_comment(lines)
        return code

    def find_pos(self, pos_line, line, offset=0):
        return self.comm_cpp_parser.find_pos(pos_line, line, offset)

    def get_line_pos(self, code):
        return self.comm_cpp_parser.get_line_pos(code)

    def get_method_end_pos(self, code):
        return self.comm_cpp_parser.get_method_end_pos(code)

    def get_method_code_blocks(self, code):
        pname, pattern_method = SearchPatternCpp.get_pattern_methods()
        if not pattern_method:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        hpp_parser = CppHeaderParser('?')

        code_start_pos = []
        m = pattern_method.finditer(code)
        for item in m:
            start = item.span()[0]
            end = item.span()[1]

            method_end_pos = self.get_method_end_pos(code[start:end])
            method_name = hpp_parser.get_method_name(code[start:start + method_end_pos])

            if not method_name:
                #print('method was not found ({})'.format(method_name))
                continue

            code_start_pos += (method_name, start + method_end_pos),

        n = len(code)
        res = []

        for method_name, code_start in code_start_pos:
            if res and res[-1][-1] >= code_start:
                # print('false detection!: ', method_name, code_start_pos[-1][1], start)
                # wrong detection of method
                # to prevent it, it needs to fix regex expression ...
                continue

            i = code_start

            while i < n:
                if code[i] == '{':
                    break
                i += 1

            if i == n or code[i] != '{':
                continue

            func_code = ''
            opn_cnt = 1

            i += 1

            while i < n and opn_cnt:
                if code[i] == '{':
                    opn_cnt += 1
                elif code[i] == '}':
                    opn_cnt -= 1

                assert(opn_cnt >= 0)
                i += 1

            res += (method_name, code[code_start:i], code_start, i),

        return res

    def remove_access_modifier(self, code):
        return self.comm_cpp_parser.remove_access_modifier(code)

    def get_function_names(self, code):
        index = clang.cindex.Index.create()

    def get_func_infos(self, file, inc_paths):
        index = clang.cindex.Index.create()
        args = '-xc++ --std=c++14'
        for i, path in enumerate(inc_paths):
            args += ' -I' + path

        tu = index.parse(file, args=args.split())

        func_infos = []
        q = [(tu.cursor, 0)]

        # for d in tu.diagnostics:
        #     if d.severity >= 3:
        #         print('Error:', d.spelling, d.location)

        while q:
            cursor, level = q.pop()
            #print(level, cursor.kind, cursor.spelling, cursor.kind in self.target_cursors, cursor_file)
            cursor_file = cursor.location.file

            if cursor.kind in self.target_cursors:
                if cursor_file.name == file:
                    func_infos += (cursor.spelling, 
                        cursor.displayname, 
                        cursor.location.line, 
                        cursor.extent.start.line,
                        cursor.extent.end.line,
                        self.cursor_tbl[cursor.kind]),

            if cursor_file and cursor_file.name != file:
                continue
            
            for c in cursor.get_children():
                q += (c, level + 1),

        return func_infos

    def get_func_infos_by_brace(self, code, pos_line):
        """
        return
            [(func_name, start line, func code), ...]
        """
        res = []
        found, clz_codes = self.comm_cpp_parser.get_each_class_code(code, False, pos_line)
        clz_pos = []
        for clz in clz_codes:
            if not clz_codes[clz].code:
                continue

            clz_pos += (clz_codes[clz].start_pos, clz_codes[clz].end_pos),
            res += self.get_code_in_brace(clz_codes[clz].code, pos_line)

        clz_pos.sort(key=lambda p: p[1], reverse=True)
        wo_clz_code = code

        for start_pos, end_pos in clz_pos:
            wo_clz_code = wo_clz_code[:start_pos] + wo_clz_code[end_pos + 1:]

        wo_clz_code = self.filter_func_code_only(wo_clz_code)
        res += self.get_code_in_brace(wo_clz_code, pos_line)

        return res

    def filter_func_code_only(self, code):
        func_pos = []
        n = len(code)
        i = 0

        while i < n:
            if code[i] == '{':
                break
            i += 1

        if i == n or code[i] != '{':
            # no function here
            return

        opn = 1
        start_pos = i
        i += 1

        while i < n:
            if code[i] == '{':                
                opn += 1
                if opn == 1:
                    start_pos = i
            elif code[i] == '}':
                opn -= 1
                if opn == 0:
                    func_pos += (start_pos, i),

            i += 1

        for idx, (start, end) in enumerate(func_pos):
            i = start - 1
            while i >= 0:
                if code[i] == ';' or code[i] == '}':
                    break
                i -= 1

            if code[i] == ';' or code[i] == '}':
                i += 1
            func_pos[idx] = (i, end)

        trimed_code = self.comm_cpp_parser.shrink_code_section(func_pos, code)
        return trimed_code

    def print_funcs(self, funcs, num_delimeter=30):
        print('-'*num_delimeter)
        for name, line, func_code in funcs:
            print('name = ', name)
            print('line = ', line)
            print(func_code)
            print('-'*num_delimeter, end='\n\n')
        print('-'*num_delimeter)

    def get_code_in_brace(self, code, pos_line):
        if not code:
            return []

        n = len(code)
        i = 0
        opn = 0
        func = ''
        start_line = 0
        start_pos = 0
        pre_end_pos = 0
        funcs = []

        while i < n:
            if code[i] == '{':
                opn += 1
                if 1 == opn:
                    start_pos = i
                    start_line = self.comm_cpp_parser.find_line(pos_line, i)
                else:
                    func += code[i]
                i += 1
                continue

            if code[i] == '}':
                opn -= 1
                if 0 == opn:
                    func_name = self.find_func_name(code, start_pos, pre_end_pos)
                    if func_name:
                        funcs += (func_name, start_line, func),
                    func = ''
                    pre_end_pos = i
                else:
                    func += code[i]

                i += 1
                continue

            if opn:
                func += code[i]

            i += 1

        return funcs

    def find_func_name(self, code, pos, pre_end_pos):
        pname, pattern_method = SearchPatternCpp.get_pattern_methods()
        if not pattern_method:
            print('ERROR: pattern for {} is not found'.format(pname))
            return ''

        hpp_parser = CppHeaderParser('?')

        n = len(code)
        i = pos - 1
        opn = 0

        while i > pre_end_pos and code[i] != ')':
            i -= 1

        if code[i] != ')':
            return ''

        opn = 1
        i -= 1

        while i > pre_end_pos and opn > 0:
            if code[i] == '(':
                opn -= 1

            if code[i] == ')':
                opn += 1

            i -= 1

        while i > pre_end_pos and (code[i] != '}' and code[i] != ';'):
            i -= 1

        if i < 0:
            i = 0

        if code[i] == '}':
            i += 1

        filtered_code = code[i:pos - 1]

        code_start_pos = []
        m = pattern_method.finditer(filtered_code)
        for item in m:
            start = item.span()[0]
            end = item.span()[1]

            method_end_pos = self.get_method_end_pos(filtered_code[start:end])
            method_name = hpp_parser.get_method_name(filtered_code[start:start + method_end_pos])
            if not method_name:
                continue

            code_start_pos += (method_name, start + method_end_pos),

        if not code_start_pos:
            print('ERROR: No name is found!')
            return ''

        if code_start_pos and len(code_start_pos) > 1:
            print('WRONG: multiple name is detected!')
            print(code_start_pos)

        # print('found name = ', code_start_pos[0][0])
        # print('-'*20, '>>', end='\n\n')
        return code_start_pos[0][0]

    def get_each_class_code(self, code, code_remove=False, pos_line=None):
        return self.comm_cpp_parser.get_each_class_code(code, False, pos_line)
