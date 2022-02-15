import re
from syntax_parser.search_patterns_cpp import *


class ClassCodeInfo:
    def __init__(self):
        self.code = ''
        self.start_line = 0
        self.start_offset = 0
        self.nested = False


class CommonCppParser:
    def __init__(self):
        SearchPatternCpp.init_default_patterns()

    def find_line(self, pos_line, pos):
        l = 0
        end = r = len(pos_line)

        while l <= r:
            m = (l + r)//2
            if pos_line[max(0, m - 1)][0] <= pos <= pos_line[min(end, m)][0]:
                return pos_line[m][1]

            if pos_line[m][0] < pos:
                l = m + 1
            else:
                r = m - 1

        return -1

    def find_pos(self, pos_line, line, offset=0) -> int:
        l = 0
        end = r = len(pos_line) - 1

        while l <= r:
            m = (l + r)//2

            if pos_line[m][1] == line:
                return pos_line[max(m + offset, 0)][0]

            if pos_line[m][1] < line:
                l = m + 1
            else:
                r = m - 1

        return pos_line[min(l, end)][0]

    def get_line_pos(self, code):
        n = len(code)
        i = 0
        line = 1
        pos_line = [(0, 0)]

        while i < n:
            if code[i] == '\n':
                pos_line += (i, line),
                line += 1
            i += 1

        pos_line += (i, line),
        return pos_line

    def get_loc(self, code):
        if not code:
            return 0

        i = 0
        n = len(code)
        cnt = 0

        if n > 0:
            cnt += 1

        while i < n:
            if code[i] == '\n':
                cnt += 1
            i += 1

        return cnt

    def remove_comment(self, code):
        code = str(code)
        code = re.compile("(?s)/\*.*?\*/").sub("", code)
        code = re.compile("//.*").sub("", code)
        code.strip()
        return code

    def get_method_end_pos(self, code):
        i = 0
        n = len(code)

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

        return i

    def remove_curly_brace(self, code, depth=1):
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

    def remove_code_in_header(self, clz, clz_code):
        if not clz_code:
            return None

        # RegEx is not possible for nested curly brace cases
        # pname, pattern = SearchPatternCpp.get_pattern_curly_brace()
        # if not pattern:
        #     return print('ERROR: pattern for {} is not found'.format(pname))
        # code = pattern.sub(";", clz_code)

        i = 0
        n = len(clz_code)
        brace_cnt = 0
        curlybrace_cnt = 0
        code = ''

        while i < n:
            if brace_cnt == 0 and clz_code[i] == '{':
                curlybrace_cnt += 1
            elif brace_cnt == 0 and clz_code[i] == '}':
                if curlybrace_cnt and brace_cnt == 0:
                    code += ';'
                curlybrace_cnt -= 1
            elif clz_code[i] == '(':
                brace_cnt += 1
            elif clz_code[i] == ')':
                brace_cnt -= 1

            if curlybrace_cnt == 0 and clz_code[i] != '}':
                code += clz_code[i]
            
            i += 1

        return code

    def find_class_end_with_code(self, code, start_idx):
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

    def get_each_class_code(self, code, code_remove=False, pos_line=None):
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

            length = self.find_class_end_with_code(code, idx)
            if -1 == length:
                break

            if 'enum' in found:
                code = code[idx + length:]
                pos += idx + length
                continue

            res_found_clz += found,
            code_info = ClassCodeInfo()
            clz_codes[clz] = code_info

            if pos_line:
                line = self.find_line(pos_line, pos + idx)
                code_info.start_line = line
                code_info.start_pos = pos + idx
                code_info.start_offset = pos + idx
                code_info.end_line = self.find_line(pos_line, pos + idx + length)
                code_info.end_pos = pos + idx + length

            code_info.code = self.remove_curly_brace(code[idx:idx + length])

            # call itself recrusively for nested class
            clz_idxs, nested_class_codes = self.get_each_class_code(code_info.code[:])
            for nclz, nclz_code in nested_class_codes.items():
                clz_codes["nested::" + nclz] = nclz_code

            if code_remove:
                code_info.code = self.remove_code_in_header(clz, code_info.code)

            for nclz_found in clz_idxs:
                idx = nclz_found.find('{')
                if idx == -1:
                    continue
                nclz_found = nclz_found[:idx]
                code_info.code = re.compile(nclz_found).sub("", code_info.code)

            code = code[idx + length:]
            pos += idx + length

        return res_found_clz, clz_codes

    def shrink_code_section(self, positions, code):
        positions.sort(key=lambda p: p[1], reverse=True)
        trimed_code = ''
        for start, end in positions:
            trimed_code = code[start: end + 1] + trimed_code

        return trimed_code

    def remove_access_modifier(self, code):
        """
            remove access modifier from code such as
                public:, private:, protected:
        """
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

            while cur >= 0 and code[cur].isalpha() or code[cur] == ' ':
                word += code[cur]
                cur -= 1

            if cur < i - 1:
                remove_pos += (cur + 1, i),

        for start, end in remove_pos[::-1]:
            code = code[:start] + code[end + 1:]

        return code
