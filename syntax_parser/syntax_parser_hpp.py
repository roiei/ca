import re

from syntax_parser.syntax_parser_factory import *
import collections
from syntax_parser.search_patterns_cpp import *
from common.tries import *
from config_reader import *
from file_info_types import *
from foundation.types import *
from util.util_log import *
from syntax_parser.cpp_parser import *


logger = Logger(False)


class CppHeaderParser(SyntaxParser):
    def __init__(self, name):
        super().__init__(name)
        deli = PlatformInfo.get_delimiter()
        self.cfg_reader = ConfigReader(
            os.path.dirname(os.path.realpath(__file__)) + 
            deli + '..' + deli  + 'config' + deli  + 'cfg_cpp.conf')
        self.cfg_json = self.cfg_reader.readAsJSON()
        if None == self.cfg_json:
            sys.exit('wrong configuration file!')
        self.ignore_class_name = self.cfg_json['ignore_class_name']
        self.rule_funcs = {
            "rof": self.__check_rof,
            "prohibit_protected": self.__check_protected,
            "singleton_getinstance_return": self.__check_getinstance_return,
            "class_type": self.__check_class_type,
            "prohibit_keyword": self.__check_prohibit_keyword,
            "name_suffix": self.__check_suffix,
            "prohibit_friend": self.__check_friend,
            "prohibit_nested_class": self.__check_nested_class,
            "modularity_num_funcs": self.__check_cohesion_num_public_methods,
            "modularity_num_params": self.__check_cohesion_num_params,
            "prohibit_raw_pointer": self.__check_raw_pointer,
        }

        SearchPatternCpp.init_default_patterns()

        self.prohibited_suffixes = Trie()
        self.class_filter = Trie()
        for name in self.ignore_class_name:
            self.class_filter.insert(name[::-1])

        self.__init_modifier()
        self.filter_keywords = []

        self.ret_map = {
            'TRUE': 'HBool',
            'FALSE': 'HBool',
            'HResult': 'HResult',
        }

    def __del__(self):
        super().__del__()

    def __get_class_name_from_file(self, file):
        #pname, pattern = SearchPatternCpp.get_pattern_class_def()
        pattern = re.compile('(class[\s]+)([\w]+)(\s)*(:)*(\s)*(public|protected|private)*(\s)*[\w]*(\s)*([\s\n]*{)')
        class_name = []

        with open(file, "r") as fp:
            while True:
                line = fp.readline()
                if not line:
                    break

                m = pattern.match(line)
                if not m:
                    continue

                class_name += m.groups()[1],

        #print('name = ', class_name)
        return class_name

    def get_non_class_code(self, code):
        pattern = re.compile('(enum\s*)*(class[\s]+)([\w]+)(\s)*(:)*(\s)*(public|protected|private)*(\s)*[\w]*(\s)*([\s\n]*{)')
        sections = []
        non_clz_code = code
        skipped_offset = 0

        while True:
            m = pattern.search(code)
            if not m:
                break

            found = m.group()
            clz = m.groups()[2].strip()
            idx = m.start()
            eidx = self.__find_class_end_with_code(code, idx)
            if -1 == eidx:
                break

            if 'enum' in found:
                code = code[idx + eidx:]
                skipped_offset += idx + eidx
                continue

            if -1 == idx:
                break

            scode = skipped_offset + m.span()[0]
            ecode = skipped_offset + eidx + 3

            sections.insert(0, (scode, ecode))
            code = code[idx + eidx:]
            skipped_offset += idx + eidx

        for s, e in sections:
            non_clz_code = non_clz_code[:s] + non_clz_code[e:]

        #print('---'*10 + '\n' + non_clz_code + '\n' + '---'*10)
        return non_clz_code


    def get_each_class_code(self, code):
        """
        OUT:
            {"class1":"code1", "class2":"code2"}
        """
        pattern = re.compile('(enum\s*)*(class[\s]+)([\w]+)(\s)*(:)*(\s)*(public|protected|private)*(\s)*[\w]*(\s)*([\s\n]*{)')
        clz_codes = collections.defaultdict(str)
        res_found_clz = []

        while True:
            m = pattern.search(code)
            if not m:
                break

            found = m.group()
            clz = m.groups()[2].strip()
            idx = m.start()
            if -1 == idx:
                break

            eidx = self.__find_class_end_with_code(code, idx)
            if -1 == eidx:
                break

            if 'enum' in found:
                code = code[idx + eidx:]
                continue

            res_found_clz += found,
            clz_codes[clz] = self.__remove_curly_brace(code[idx:idx + eidx])

            # if there is class code in the class 
            clz_idxs, nested_class_codes = self.get_each_class_code(clz_codes[clz][:])
            for nclz, nclz_code in nested_class_codes.items():
                clz_codes["nested::" + nclz] = nclz_code

            clz_codes[clz] = self.__remove_code_in_header(clz, clz_codes[clz])

            for nclz_found in clz_idxs:
                idx = nclz_found.find('{')
                if idx == -1:
                    continue
                nclz_found = nclz_found[:idx]
                clz_codes[clz] = re.compile(nclz_found).sub("", clz_codes[clz])

            code = code[idx + eidx:]

        return res_found_clz, clz_codes

    def get_enum_codes(self, code, whole_code, pos_line):
        """
        OUT:
            {"class1":"code1", "class2":"code2"}
        """
        pattern = re.compile('enum\s+(class\s+)*[\w_]+\s*\:*\s*[\w]*\s*{\s*[\/*<\d\s,\w=|+();:!@#$%^&()-_=+\"\',~`]*}\s*;')
        clz_codes = collections.defaultdict(str)
        res_found_clz = []

        enum_codes = []
        m = re.finditer(pattern, code)
        m = list(m)
        for item in m:
            start, end = item.span()[0], item.span()[1]
            expr = code[start:end + 1]
            pos = whole_code.find(expr)

            line = self.find_line(pos_line, pos)
            name = self.get_enum_name(expr)
            enum_codes += (name, expr, line),
            #print('enum code = ', expr)

        return enum_codes

    def __find_class_end_with_regex(self, code, start_idx):
        """
            start_idx is 'class A {' <- { position
        """
        clz_code = code[start_idx:]
        pattern_end = re.compile('}\s*;')
        m = pattern_end.search(clz_code)
        if m:
            return m.end()
        return -1

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

    def __remove_code_in_header(self, clz, clz_code):
        if not clz_code:
            return None

        # RegEx is not possible for nested curly brace cases
        # pname, pattern = SearchPatternCpp.get_pattern_curly_brace()
        # if not pattern:
        #     return print('ERROR: pattern for {} is not found'.format(pname))
        # code = pattern.sub(";", clz_code)

        i = 0
        n = len(clz_code)
        open_cnt = 0
        code = ''

        while i < n:
            if clz_code[i] == '{':
                open_cnt += 1
            elif clz_code[i] == '}':
                if open_cnt:
                    code += ';'
                open_cnt -= 1

            if open_cnt == 0 and clz_code[i] != '}':
                code += clz_code[i]
            
            i += 1

        return code

    # deprecated method: hard to get method with RegEx
    def __get_class_methods_regex(self, clz, code):
        pname, pattern = SearchPatternCpp.get_pattern_methods()
        if not pattern:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        m = pattern.finditer(code)
        for r in m:
            expr = r[0]
            expr = expr.strip()

    def __init_modifier(self):
        self.mod_trie = Trie()
        for mod in ['public', 'protected', 'private']:
            self.mod_trie.insert(mod[::-1])

    def __print_class_methods(self, clz, access_mod):
        print('class = ', clz)
        for mod in access_mod:
            if not access_mod[mod]:
                continue

            print('modifier = ', mod, ', num = ', len(access_mod[mod]))
            for method in access_mod[mod]:
                print('\tmethod = ', method)
            print()

    def __remove_whitespace_between_delimeter(self, expr, opn, close):
        n = len(expr)
        opn_cnt = 0
        i = 0
        res = ''

        while i < n:
            if expr[i] == opn:
                opn_cnt += 1
            elif expr[i] == close:
                opn_cnt -= 1

            if opn_cnt == 0:
                res += expr[i]
            elif opn_cnt > 0:
                if expr[i] != ' ':
                    res += expr[i]
            i += 1
        return res

    def __remove_whitespace_between_brace(self, expr):
        brace_type = [('<', '>'), ('(', ')')]
        for opn, close in brace_type:
            expr = self.__remove_whitespace_between_delimeter(expr, opn, close)

        return expr

    def __split_return(self, func_expr, clz):
        expr = self.__remove_whitespace_between_brace(func_expr)
        #print('expr = ', expr)
        i = 0
        n = len(expr)
        res = []

        expr = expr.split()
        if not expr:
            return None

        res += expr.pop(0),

        if clz in res[-1]:
            return None

        if not expr:
            return None

        prefix_keywords = ['const', 'static', 'virtual']
        for kwd in prefix_keywords:
            if res[-1] == kwd and expr:
                res += expr.pop(0),

        for chunk in expr:
            if chunk and (chunk[0] != '<' or chunk[0] != '&' or chunk[0] != '*'):
                break
            res += chunk,

        res = ' '.join(res)

        sb = res.find('(')
        eb = res.find(')')
        if sb != -1 and eb != -1:
            res = res[:sb]

        #print(': ', res, clz, res.find(clz))
        if -1 != res.find(clz):
            return None

        return res

    def __is_attribute(self, expr):
        res = True
        chunks = expr.split()
        if chunks and (len(chunks) == 2 and 
            (chunks[0] in ['class', 'struct'])):
            res = False
        return res

    # deprecated
    def __get_param_block_pre(self, func_expr):
        sidx = func_expr.rfind('(')
        eidx = func_expr.rfind(')')
        if sidx > eidx:
            return False, ''

        return True, func_expr[sidx + 1:eidx]

    def __get_param_pos(self, text):
        n = len(text)
        i = n - 1

        while i >= 0:
            if text[i] == ')':
                break
            i -= 1

        if i < 0 or text[i] != ')':
            return -1, ''

        i -= 1
        end = i
        close = 1

        while i >= 0:
            if text[i] == ')':
                close += 1
            elif text[i] == '(':
                close -= 1

            if close == 0:
                break
            i -= 1

        if i < 0:
            return -1, ''

        return i, end

    def __get_param_block(self, text):
        sx, ex = self.__get_param_pos(text)
        if -1 == sx:
            return False, ''
        
        return True, text[sx + 1:ex + 1]

    def __get_split_lines(self, doxy_text):
        if not doxy_text:
            return

        lines = []
        i = 0
        line = ''
        while i < len(doxy_text):
            if doxy_text[i] == '@':
                if line and line[0] == '@':
                    lines += line,
                line = '@'
            else:
                line += doxy_text[i]
            i += 1

        lines += line,
        return lines

    def __split_param(self, func_expr):
        """
        TODO:
            function pointer
        """
        params = []
        res, param = self.__get_param_block(func_expr)
        if not res:
            return None

        l = r = 0
        n = len(param)
        arrow_brace = 0

        while r < n:
            if param[r] == '<':
                arrow_brace += 1
            elif param[r] == '>':
                arrow_brace -= 1

            if arrow_brace == 0 and param[r] == ',':
                params += param[l:r].strip(),
                l = r + 1

            r += 1

        if r > l:
            params += param[l:r].strip(),

        return params

    def __get_variable_name(self, params):
        """
            get variable name from each parameter
        """
        vars = []
        res = True

        for param in params:
            param = param.split('=')[0].split()[-1]
            pos = 0
            for i in range(len(param) - 1, -1, -1):
                if not (param[i].isalpha() or param[i].isdigit() or param[i] == '_'):
                    pos = i + 1
                    break

            var = param[pos:] if pos else param
            if '' == var:
                res = False
                continue

            vars += var,

        return res, vars

    def __get_doxy_patterns(self, code, patterns):
        doxy_params = []
        for line in code:
            for param_type, param_pattern in patterns.items():
                m = re.search(param_pattern, line)
                if m:
                    line = line[m.end():].replace(':', ' ')    
                    idx = line.find('\n')
                    line = line[:idx]
                    param = line.split()[0].replace(',', '')
                    param = param.strip()
                    doxy_params += param,

        return doxy_params

    def __get_func_code(self, code):
        errs = []
        pname, pattern = SearchPatternCpp.get_pattern_methods()
        if not pattern:
            return None

        m = pattern.search(code)
        if not m:
            return None

        func_code = code[m.span()[0]:m.span()[1]].strip()
        if func_code.startswith('define'):
            return None

        return func_code

    def __get_code_params(self, func_code, code_params):
        errs = []
        params = self.__split_param(func_code)
        ret = self.__split_return(func_code, 'None')
        # print('params = ', params, 'ret = ', ret)

        ret_var, code_param = self.__get_variable_name(params)
        code_params += code_param
        if not ret_var:
            errs += 'ERROR: variable is not defined in the param code',
            return RetType.WARN, errs

        return RetType.SUCCESS, errs

    def __get_class_methods_attrs(self, clz, code, whole_code=None, pos_line=None):
        """
        OUT:
            {"public":[method1, method2], "protected":[method3]}
        """
        logger.log('+{} of {}'.format(sys._getframe().f_code.co_name, clz))
        if not code:
            return None

        access_mod = collections.defaultdict(list)
        pname, pattern = SearchPatternCpp.get_pattern_methods()
        if not pattern:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        i = 0
        line = -1
        n = len(code)
        modifier = 'private'

        while i < n:
            expr = ''
            is_modifier = False

            while i < n and (code[i] != '{' and code[i] != ';' and code[i] != '}'):
                if code[i] == ':':
                    if self.mod_trie.search(expr[-1::-1].strip()):
                        modifier = expr.strip()
                        is_modifier = True
                        break

                expr += code[i]
                i += 1

            if is_modifier:
                i += 1
                continue

            expr = expr.strip()
            m = pattern.search(expr)
            #print(expr)
            if m:
                sx = m.span()[0]
                ex = m.span()[1]
                expr = expr[sx:ex].strip()

                if pos_line:
                    pos = whole_code.find(expr)
                    line = self.find_line(pos_line, pos)

                #print(expr, pos_line, pos)
                #sys.exit()
                #print(expr)
                logger.log('method = {}'.format(expr))
                params = self.__split_param(expr)
                ret = self.__split_return(expr, clz)
                access_mod[modifier + ' method'] += (expr, params, ret, line),
            elif expr and self.__is_attribute(expr):
                access_mod[modifier + ' attribute'] += (expr, None, None, -1),
            i += 1

        #self.__print_class_methods(clz, access_mod)
        logger.log('-{} of {}'.format(sys._getframe().f_code.co_name, clz) + '\n'*2)
        return access_mod

    def __check_keyword(self, namespace, kwd, clz_methods):
        """
        DESC:
            check class type is defined one or not
        OUT:
            [pattern_name1:True,    <-- pair is not used
             pattern_name2:False]   <-- pair is used
        """
        if not clz_methods:
            return {kwd: True}

        for mod in clz_methods:
            for method, prams, ret, line in clz_methods[mod]:
                idx = method.find(kwd)
                if -1 == idx:
                    continue

                i = idx + len(kwd)
                while i < len(method):
                    if method[i] != ' ':
                        break
                    i += 1

                if namespace == "std":
                    if i < len(method) and method[i] == '<':
                        return {kwd: False}
                else:
                    return {kwd: False}

        return {kwd: True}

    # default: common code
    def __get_clz_type(self, clz, clz_code):
        """
        IN:
            clz: class name
            clz_code: code of the class
        OUT:
            class type: REGULAR, INTERFACE, ABSTRACT, STATIC
        """
        if not clz_code:
            return ClassType.UNDEFINED

        clz_type = ClassType.REGULAR
        pname, pattern = SearchPatternCpp.get_pattern_pure_virtualfunc()
        if not pattern:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        has_interface_name = clz.startswith('I')

        m = pattern.search(clz_code)
        if m and has_interface_name:
            clz_type = ClassType.INTERFACE
        elif not m and has_interface_name:
            clz_type = ClassType.UNDEFINED
        elif m and not has_interface_name:
            clz_type = ClassType.ABSTRACT

        pname, pattern = SearchPatternCpp.get_pattern_singleton()
        if not pattern:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        m = pattern.search(clz_code)
        if m:
            clz_type = ClassType.SINGLETON

        return clz_type

    # rule code
    def __check_rof(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        OUT
            {"pattern1":False, "pattern2":True, ...}
        """
        if clz_type not in [ClassType.REGULAR, ClassType.ABSTRACT, ClassType.SINGLETON]:
            return None

        done = collections.defaultdict(bool)

        for pname, pattern in SearchPatternCpp.get_pattern_rof():
            if done[pname]:     # set False here
                continue

            res = pattern.search(clz_codes[clz])
            if res:
                done[pname] = True

        return done

    # rule code
    def __check_friend(self, clz, clz_type, clz_codes, clz_methods, cfg):
        done = collections.defaultdict(bool)

        if not clz_codes[clz]:
            return done

        for pname, pattern in SearchPatternCpp.get_pattern_friend():
            if done[pname]:     # set False here
                continue

            res = pattern.search(clz_codes[clz])
            if not res:
                done[pname] = True

        return done

    # rule code
    def __check_protected(self, clz, clz_type, clz_codes, clz_methods, cfg):
        done = collections.defaultdict(bool)

        if not clz_codes[clz]:
            return done

        for pname, pattern in SearchPatternCpp.get_pattern_protected():
            if done[pname]:     # set False here
                continue

            res = pattern.search(clz_codes[clz])
            if not res:
                done[pname] = True

        return done

    # rule code
    def __check_getinstance_return(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        DESC:
            this function checks whether getInstance returns raw pointer or similar to that.
            if a function returns raw pointer, then it return [pattern_name:False]
        OUT:
            [pattern_name1:True,    <-- no raw pointer found
             pattern_name2:False]   <-- raw pointer found
        """
        if ClassType.SINGLETON != clz_type:
            return None

        done = collections.defaultdict(bool)

        for pname, pattern in SearchPatternCpp.get_pattern_singleton_ptr():
            if done[pname]:     # set False here
                continue

            res = pattern.search(clz_codes[clz])
            if not res:
                #print(clz_codes[clz][res.span()[0] - 100 : res.span()[1]])
                done[pname] = True

        return done

    # rule code
    def __check_class_type(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        DESC:
            check class type is defined one or not
        OUT:
            [pattern_name1:True,    <-- defined class
             pattern_name2:False]   <-- not defined class
        """
        if ClassType.UNDEFINED == clz_type:
            return {'UNDEFINED class type' : False}
        return {'UNDEFINED class type' : True}

    # rule code
    def __check_prohibit_keyword(self, clz, clz_type, clz_codes, clz_methods, cfg):
        res = {}
        for keyword in self.filter_keywords:
            namespace, keyword = keyword.split('::')
            ret = self.__check_keyword(namespace, keyword, clz_methods)
            for kwd, result in ret.items():
                res['prohibit_keyword:' + kwd] = result

        return res

    # rule code
    def __check_suffix(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        DESC:
            check class type is defined one or not
        OUT:
            [pattern_name1:True,    <-- pair is not used
             pattern_name2:False]   <-- pair is used
        """
        ret, suff = self.prohibited_suffixes.is_registered_suffix_exist(clz.lower()[::-1])
        if ret:
            return {"wrong_suffix -> " + suff[::-1]: False}
                
        return {"wrong_suffix": True}

    # rule code
    def __check_nested_class(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        """
        if clz.startswith('nested::'):
            return {"nested class -> {}".format(clz): False}

        return {"nested class": True}

    # rule code
    def __check_cohesion_num_public_methods(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        """
        res = {}
        num_limit = cfg.get_num_of_public_func()

        num_func = len(clz_methods['public method'])
        if num_func >= num_limit:
            return {"violate_modularity" + f" -> num public methods {num_func}": False}

        return {"violate_modularity": True}

    # rule code
    def __check_cohesion_num_params(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        """
        res = {}
        num_limit = cfg.get_num_of_params()

        for acc in clz_methods:
            for expr, params, ret in clz_methods[acc]:
                if params and len(params) >= num_limit:
                    expr = expr.strip()[:50] + '...'
                    res["violate_modularity" + " -> num params of {}".format(expr)] = False

        return res if res else {"violate_modularity": True}

    # rule code
    def __check_raw_pointer(self, clz, clz_type, clz_codes, clz_methods, cfg):
        """
        """
        res = {}

        for acc in clz_methods:
            for expr, params, ret in clz_methods[acc]:
                if params:
                    for param in params:
                        if '*' in param:
                            res["violate_raw_ptr" + " -> {}".format(expr)] = False

                if ret and '*' in ret:
                    res["violate_raw_ptr" + " -> {}".format(expr)] = False

        return res if res else {"violate_modularity": True}

    def get_method_calls(self, code):
        print(code)
        sys.exit()
        pass

    def get_method_name(self, method):
        sx, ex = self.__get_param_pos(method)
        if -1 == sx:
            return ''

        method_name = method[:sx]
        if not method_name:
            return ''

        method_chunks = method_name.split()

        try:
            if len(method_chunks) > 1 and method_chunks[-1] in {'==', '=', '+', '-'} and 'operator' in method_chunks[-2]:
                method_name = method_chunks[-2] + method_chunks[-1]
            else:
                method_name = method_chunks[-1] 
        except IndexError:
            print('index err @ method: ', method_name)
            print(method, sx, ex)
            print('app is terminated...')
            sys.exit()

        return method_name

    def get_enum_name(self, chunk):
        pattern = re.compile('enum\s+(class\s+)*[\w_]+\s*\:*\s*[\w]*')
        m = pattern.search(chunk)
        enum_name = ''
        if m:
            sx = m.span()[0]
            ex = m.span()[1]
            enum_name = chunk[sx:ex]
            enum_name = enum_name.split()
            while enum_name and enum_name[0] in {'enum', 'class'}:
                enum_name.pop(0)

            enum_name = ''.join(enum_name)

        return enum_name

    def set_suffix_filter(self, suffixes):
        for name in suffixes:
            self.prohibited_suffixes.insert(name[::-1])

    def set_filter_keyword(self, keywords):
        self.filter_keywords += keywords

    def get_code_without_comment(self, url):
        return CppParser.get_code_only(url)

    def remove_comment(self, code):
        code = re.compile("(?s)/\*.*?\*/").sub("", code)
        code = re.compile("//.*").sub("", code)
        code.strip()

        pname, pattern = SearchPatternCpp.get_pattern_methods()
        if not pattern:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        m = pattern.search(code)
        if m:
            sx = m.span()[0]
            ex = m.span()[1]
            code = code[sx:ex].strip()

        return code

    def check_rules(self, code, report, cfg, rule_coverage="all"):
        """
        IN:
            class names and code including the class names
            rules
                ["rof"]
        OUT:
            missing rules : {(cls, cls_type) : [missing_pattern_name1, missing_pattern_name2}
        """
        rules = cfg.get_rules()
        get_each_class_code, clz_codes = self.get_each_class_code(code)
        if not clz_codes:
            return None

        report.num_classes = len(clz_codes)
        result = collections.defaultdict(list)

        for clz in clz_codes:
            if self.class_filter.is_registered_suffix_exist(clz[::-1])[0]:
                continue

            clz_type = self.__get_clz_type(clz, clz_codes[clz])
            SearchPatternCpp.reset_patterns(clz)
            clz_methods = self.__get_class_methods_attrs(clz, clz_codes[clz])

            for rule in rules:
                acc, rule = rule.split('::')
                if acc != 'must' and rule_coverage != 'all':
                    continue

                if rule not in self.rule_funcs:
                    print('Not supported rule.')
                    continue

                done = self.rule_funcs[rule](clz, clz_type, clz_codes, clz_methods, cfg)
                if not done:
                    continue

                for pname, success in done.items():
                    if not success:
                        result[(clz, clz_type)] += pname,

        return result    # missing_rules

    def get_methods(self, code):
        """
        IN:
            file code w/o comment
        OUT:
            {"class1" : {"public":[method1, method2], "protected":[method3]}, 
             "class2" : {"public":[method4, method5]}}
        """
        get_each_class_code, clz_codes = self.get_each_class_code(code)
        if not clz_codes:
            return None

        clz_methods = collections.defaultdict(None)

        for clz in clz_codes:
            if self.class_filter.is_registered_suffix_exist(clz[::-1])[0]:
                continue

            if not clz_codes[clz]:
                continue

            clz_type = self.__get_clz_type(clz, clz_codes[clz])
            SearchPatternCpp.reset_patterns(clz)

            methods = self.__get_class_methods_attrs(clz, clz_codes[clz])
            clz_methods[clz] = methods

        return clz_methods    # missing_rules

    def get_methods_in_class(self, clz_name, clz_code, whole_code, pos_line):
        if not clz_code:
            return None

        clz_code = re.compile("(?s)/\*.*?\*/").sub("", clz_code)
        clz_code = re.compile("//.*").sub("", clz_code)

        method_infos = self.__get_class_methods_attrs(clz_name, clz_code, whole_code, pos_line)
        method_names = []

        for acc, methods in method_infos.items():
            for method_code, params, ret, line in methods:
                method_name = self.get_method_name(method_code)
                if '' != method_name:
                    num_signatures = len(params) + 1 if params else 0
                    method_names += (method_name, method_code, line, num_signatures),

        return method_names

    def get_doxy_comment_chunks(self, code, clz, get_name=None):
        """
            find doxygen comment block
            regarding doxy comment
                /** ~~ */
        """
        comment_pattern = re.compile('(?s)\/\*.*?\*\/')
        res = []
        n = len(code)

        i = 0
        line = 1
        pos_line = []

        while i < n:
            if code[i] == '\n':
                pos_line += (i, line),
                line += 1
            i += 1

        pos_line += (i, line),

        m = re.finditer(comment_pattern, code)
        m = list(m)

        doxy_cmt_pattern = '@\s*brief'
        patt = re.compile(doxy_cmt_pattern)
        method_m = []

        for item in m:
            start, end = item.span()[0], item.span()[1]
            comment_code = code[start:end + 1]
            if not patt.search(comment_code):
                continue

            method_m += item,

        pos = 0
        num_pos = len(pos_line)

        for i in range(len(method_m)):
            end_pos = method_m[i].span()[1]
            while pos + 1 < num_pos and pos_line[pos][0] < end_pos:
                pos += 1

            comment_start = method_m[i].span()[0]
            comment_end = method_m[i].span()[1]

            end = code[comment_end:].find(';')
            chunk_code = code[comment_start:end + comment_end + 1]

            # print('chunk_code = ', chunk_code)
            # print('-----')

            if get_name:
                method_name = get_name(chunk_code)
                if '' != method_name:
                    res += (pos_line[pos][1], chunk_code, method_name),

        return res

    def get_doxy_comment_method_chunks(self, code, clz):
        return self.get_doxy_comment_chunks(code, clz, self.get_method_name);

    def get_doxy_comment_enum_chunks(self, code):
        return self.get_doxy_comment_chunks(code, None, self.get_enum_name);

    def get_doxy_comment_method_chunks_2(self, code, clz, clz_methods):
        """
            under development
        """
        for attr, methods in clz_methods[clz].items():
            for method in methods:
                scode = code.find(method[0])

                sdoxy = code[:scode].rfind('/\*\*')

                print(code[sdoxy:scode])
                sys.exit()


        doxy_cmt_pattern = '/\*\*[].\w*@\s[]*\*/'
        comment_pattern = re.compile(doxy_cmt_pattern)

        m = re.finditer(comment_pattern, code)
        m = list(m)

        for item in m:
            start, end = item.span()[0], item.span()[1]

    def verify_doxycoment_methods(self, comment_code, whole_code, clz, pos_line, is_dup_permitted=False):
        # print('--------------->>')
        # print('comment_code = ', comment_code)
        # print('---------------<<')
        res = RetType.SUCCESS
        errs = []
        comment_pattern = re.compile('(?s)\/\*.*?\*\/')
        comment = None
        code = None
        m = comment_pattern.search(comment_code)
        if m:
            comment = comment_code[m.start():m.end()]
            code = re.compile("//.*").sub("", comment_code[m.end() + 1:])

        commnet_lines = self.__get_split_lines(comment)

        patterns = {
            'out_param': '@\s*param\s*\[\s*out\s*\]',
            'in_param': '@\s*param\s*\[\s*in\s*\]',
        }

        doxy_params = self.__get_doxy_patterns(commnet_lines, patterns)
        doxy_returns = self.__get_doxy_patterns(commnet_lines, {'return': '@\s*(retval|return)\s*'})

        func_code = self.__get_func_code(code)

        #print(func_code)
        if not func_code:
            errs += (-1, 'ERROR: no code but comment'),
            return RetType.WARN, errs

        func_idx = whole_code.find(func_code)
        err_line = self.find_line(pos_line, func_idx)

        code_params = []
        ret, err = self.__get_code_params(func_code, code_params)
        errs += [(-1, e) for e in err]
        if RetType.ERROR == ret:
            return ret, errs

        return_code = self.__split_return(func_code, clz)
        #print('return = ', return_code, 'for func = ', func_code)
        if return_code in {'explicit', 'virtual'}:
            return_code = None

        if return_code and (-1 != return_code.find(clz) or (-1 != clz.find(return_code))):
            # if return_code != clz:
            #     errs += (err_line, 'did you try to declare constructor?'),
            #     res = RetType.ERROR
            return_code = None

        for code_param in code_params:
            if code_param not in doxy_params:
                errs += (err_line, '\'' + code_param + '\' is not documented'),
                res = RetType.ERROR

        for doxy_param_name in doxy_params:
            if doxy_param_name not in code_params:
                errs += (err_line, '\'' + doxy_param_name + \
                    '\' does not exist in the code'),
                res = RetType.ERROR
            elif not is_dup_permitted:
                code_params.pop(code_params.index(doxy_param_name))

        #print(return_code)

        if (return_code and 'void' not in return_code) and not doxy_returns:
            errs += (err_line, 'return \"{}\" is not documented'.format(return_code)),
            res = RetType.ERROR

        if (return_code and 'void' not in return_code) and not doxy_returns:
            errs += (err_line, 'return \"{}\" does not exist in the code'.\
                format(return_code)),
            res = RetType.ERROR

        if errs:
            mn = min([line for line, msg in errs])
            errs.insert(0, (mn - 1, 'method: {}'.format(func_code)))

        return res, errs

    def verify_doxycomment_enum(self, enum_code, enum_line, whole_code, pos_line):
        res = RetType.SUCCESS
        errs = []

        sx = enum_code.find('{')
        ex = enum_code.rfind('}')
        offset_lines = enum_code[:sx].count('\n')
        enum_code = enum_code[sx + 1:ex]

        # TODO
        # 아래 코드는 \n을 기준으로 split 그런데 one line에 모든 코드가 존재하는 경우가 있음
        #  -> 물론 이런 경우도 에러 처리 필요
        #
        # split은 주석을 제외한 코드를 가지고 ,로 해야함 (주석 내 , 가 있을 수 있음)
        # A, B, C...로 나오면, A시작, B 시작 - 1을 A 구간으로 결정 (주석 포함) 하여 한개 item으로 결정
        # line은 코드 blk에서 offset을 찾아 offset의 line을 구해야함

        lines = enum_code.split('\n')
        lines = [line.strip() for line in lines if line and line != '\n']

        patterns = [re.compile("\/\*\*<[\w\s[=\]-_:;()'\"\/!@#$%,^~&*`+?]*\*\/"),
            re.compile('\/\/\/<[\w\s[=\]-_:;()\'\"\/,!@#$%^~&*`+?]*')]

        for i, line in enumerate(lines):
            #print('line = ', line)
            comment = None

            for pattern in patterns:
                m = pattern.search(line)
                if not m:
                    continue

                sx = m.span()[0]
                ex = m.span()[1]
                comment = line[sx:ex + 1]
                sx, ex = 0, 0
                if comment.startswith('/**<'):
                    sx = comment.find('/**<') + 4
                    ex = comment.rfind('*/') - 1
                else:
                    sx = comment.find('///<') + 4
                    ex = len(comment)

                comment = comment[sx:ex + 1].strip()
                #print('comment = ', comment)

            if not comment:
                errs += (offset_lines + enum_line + 1 + i, '\'' + line + '\'' + 'is not documented'),

            # todo:
            # 1. find  /**< 16 bits signed little endian */
            # ///< BOOK_MARK 
            # \/\*\*<[\w\s[=\]-_:;()'"\/!@#$%^~&*`+?]*\*\/

        return res, errs


    def get_code(self, file):
        lines = []

        res = UtilFile.get_lines(file, lines)
        if ReturnType.SUCCESS != res:
            return None

        return ''.join(lines)

    def get_line_pos(self, code):
        n = len(code)
        i = 0
        line = 1
        pos_line = []

        while i < n:
            if code[i] == '\n':
                pos_line += (i, line),
                line += 1
            i += 1

        pos_line += (i, line),
        return pos_line

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

