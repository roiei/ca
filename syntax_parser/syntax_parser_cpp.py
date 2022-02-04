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
    def __init__(self, name):
        super().__init__(name)
        self.comm_cpp_parser = CommonCppParser()
        if not PlatformInfo.is_Linux():
            clang.cindex.Config.set_library_file('C:/Program Files/LLVM/bin/libclang.dll')
        self.target_cursors = {CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR, CursorKind.CXX_METHOD, CursorKind.FUNCTION_DECL}

    def __del__(self):
        super().__del__()

    def get_code_without_comment(self, url):
        return CppParser.get_code_only(url)

    def find_method_calls(self, code):
        #print(code)
        calls = collections.defaultdict(int)

        #pattern = re.compile('(::|\.|->)[\w]+\s*\([\w\s,\"~]*\)\s*;')
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
            
            #print('caller = ', caller, ', method = ', method)
            calls[caller + '::' + method] += 1

        # [(clz1, call1), (clz2, call2), ...]
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

    def __find_class_end_with_code(self, code, start_idx):
        clz_code = code[start_idx:]
        if not clz_code or '{' == clz_code[0]:
            return -1

        n = len(clz_code)
        i = 0
        while i < n and clz_code[i] != '{':
            i += 1

        if i == n:
            return -1

        op_cnt = 1
        i += 1

        while op_cnt and i < n:
            if '{' == clz_code[i]:
                op_cnt += 1
            elif '}' == clz_code[i]:
                op_cnt -= 1
            i += 1

        if op_cnt > 0:
            return -1

        return i

    def __remove_curly_brace(self, code, depth=1):
        i = 0
        n = len(code)

        # remove the first '{'' and the last '}'
        while i < n and code[i] != '{':
            i += 1

        if i < n and code[i] == '{':
            i += 1  # skip '{'

        tail = n - 1
        while tail >= 0 and code[tail] != '}':
            tail -= 1

        if tail >= 0 and code[tail] == '}':
            tail -= 1 # skip '}'

        return code[i:tail + 1]

    def get_each_class_code(self, code, pos_line=None):
        pattern_name, pattern = SearchPatternCpp.get_pattern_find_class_start()
        clz_codes = collections.defaultdict(ClassCodeInfo)
        res_found_clz = []
        pos = 0

        while True:
            m = pattern.search(code)
            if not m:
                break

            found = m.group()
            clz = m.groups()[2].strip()
            idx = m.start()
            if -1 == idx:
                break

            length = self.__find_class_end_with_code(code, idx)
            if -1 == length:
                break

            if 'enum' in found:
                code = code[idx + length:]
                continue

            res_found_clz += found,
            code_info = ClassCodeInfo()
            clz_codes[clz] = code_info

            if pos_line:
                line = self.comm_cpp_parser.find_line(pos_line, pos + idx)
                code_info.start_line = line
                code_info.start_pos = pos + idx
                code_info.start_offset = pos + idx
                code_info.end_line = self.comm_cpp_parser.find_line(pos_line, pos + idx + length)
                code_info.end_pos = pos + idx + length

            code_info.code = self.__remove_curly_brace(code[idx:idx + length])

            # print('>>>>>>>>>>>>>>>>>>>>>')
            # print('code_info.code = ', code_info.code)
            # print('<<<<<<<<<<<<<<<<<<<<<')

            # call itself recrusively for nested class
            clz_idxs, nested_class_codes = self.get_each_class_code(code_info.code[:])
            for nclz, nclz_code in nested_class_codes.items():
                clz_codes["nested::" + nclz] = nclz_code

            for nclz_found in clz_idxs:
                idx = nclz_found.find('{')
                if idx == -1:
                    continue
                nclz_found = nclz_found[:idx]
                code_info.code = re.compile(nclz_found).sub("", code_info.code)

            code = code[idx + length:]
            pos += idx + length

        return res_found_clz, clz_codes

    def remove_comments(self, code):
        code = re.compile("(?s)/\*.*?\*/").sub("", code)
        code = re.compile("//.*").sub("", code)
        return code

    def get_code(self, url):
        lines = self.get_code_lines(url)
        code = self.remove_comments(lines)
        return code

    def get_methods_in_file(self, url):
        print('get methods: url = ', url)

    def find_pos(self, pos_line, line, offset=0):
        return self.comm_cpp_parser.find_pos(pos_line, line, offset)

    def get_line_pos(self, code):
        return self.comm_cpp_parser.get_line_pos(code)

    def get_method_end_pos(self, code):
        i = 0
        n = len(code)

        #print('method input code = ', code)

        while i < n:
            if code[i] == '(':
                break
            i += 1

        if i == n:
            return None

        opn_cnt = 1
        i += 1

        while i < n and opn_cnt:
            if code[i] == '(':
                opn_cnt += 1
            elif code[i] == ')':
                opn_cnt -= 1
            i += 1

        #print('method name only = ', code[:i])
        return i

    def get_method_code_blocks(self, code):
        #print('+get_method_code_blocks')
        pname, pattern_method = SearchPatternCpp.get_pattern_methods()
        if not pattern_method:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        hpp_parser = CppHeaderParser('?')
        # print('\n'*3)
        # print('-'*30)
        # print('code = ', code)
        # print('-'*30)
        # print('\n'*3)        

        code_start_pos = []
        m = pattern_method.finditer(code)
        for item in m:
            start = item.span()[0]
            end = item.span()[1]

            method_end_pos = self.get_method_end_pos(code[start:end])
            #print('method = ', code[start:end])
            
            method_name = hpp_parser.get_method_name(code[start:start + method_end_pos])

            if not method_name:
                #print('method was not found ({})'.format(method_name))
                continue

            #print('method_name = ', method_name)
            #print()

            code_start_pos += (method_name, start + method_end_pos),

        n = len(code)
        res = []

        for method_name, code_start in code_start_pos:
            #print('>>', code[code_start - 10: code_start + 10])

            if res and res[-1][-1] >= code_start:
                #print('false detection!: ', method_name, code_start_pos[-1][1], start)
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

            # print('***')
            # print(method_name + ' = ', code[code_start:i])
            # print()

        # for method_name, method_code in res:
        #     print('***')
        #     print(method_name + ' = ', method_code)
        #     print()

        return res

    def remove_access_modifier(self, code):
        i = 0
        n = len(code)
        pos = []

        while i < n:
            if i == n - 1 and code[i] == ':' and i - 1 >= 0 and code[i - 1] != ':':
                pos += i,

            if i < n - 1 and code[i] == ':' and i - 1 >= 0 and code[i - 1] != ':' \
                    and i + 1 < n and code[i + 1] != ':':
                pos += i,

            i += 1

        remove_pos = []

        for i in pos:
            word = ''
            cur = i - 1

            while code[cur].isalpha() or code[cur] == ' ':
                word += code[cur]
                cur -= 1

            if cur < i - 1:
                remove_pos += (cur + 1, i),

            #print('word = ', word[::-1])

        #print('remove_pos = ', remove_pos)

        for start, end in remove_pos[::-1]:
            code = code[:start] + code[end + 1:]

        return code

    def get_function_names(self, code):
        index = clang.cindex.Index.create()

    def get_func_infos(self, file):
        index = clang.cindex.Index.create()
        tu = index.parse(file, args='-xc++ --std=c++14'.split())

        func_infos = []
        q = [(tu.cursor, 0)]
        while q:
            cursor, level = q.pop()

            if cursor.kind in self.target_cursors:
                func_infos += (cursor.spelling, cursor.displayname, 
                    cursor.location.line, 
                    cursor.extent.start.line,
                    cursor.extent.end.line),

            #show(cursor.kind, 'spel = ', cursor.spelling, 'disp = ', 
            #    cursor.displayname, cursor.location, level=level)
            
            for c in cursor.get_children():
                q += (c, level + 1),

        return func_infos
