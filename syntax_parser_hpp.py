import re
import os
import sys
from syntax_parser_factory import *
import collections
from search_patterns_cpp import *
from tries import *
from config_reader import *
from file_info_types import *
from foundation.types import *


DEBUG_MSG_ON = False
#DEBUG_MSG_ON = True


def logd(log):
    if not DEBUG_MSG_ON:
        return
    print(log)


class CppHeaderParser(SyntaxParser):
    def __init__(self, name):
        super().__init__(name)
        self.cfg_reader = ConfigReader(os.path.dirname(os.path.realpath(__file__)) + '/cfg_cpp.conf')
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
        }

        SearchPatternCpp.init_default_patterns()

        self.prohibited_suffixes = Trie()
        self.class_filter = Trie()
        for name in self.ignore_class_name:
            self.class_filter.insert(name[::-1])

        self.__init_modifier()
        self.filter_keywords = []

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

    def __get_each_class_code(self, code):
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
            clz = m.groups()[2]
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
            clz_idxs, nested_class_codes = self.__get_each_class_code(clz_codes[clz][:])
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
        i = 0
        n = len(expr)
        res = []

        expr = expr.split()
        if not expr:
            return []

        res += expr.pop(0),

        if clz in res[-1]:
            return []

        prefix_keywords = ['const', 'static', 'virtual']
        for kwd in prefix_keywords:
            if res[-1] == kwd and expr:
                res += expr.pop(0),

        for chunk in expr:
            if chunk and (chunk[0] != '<' or chunk[0] != '&' or chunk[0] != '*'):
                break
            res += chunk,

        res = ' '.join(res)
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

    def __get_param_block(self, text):
        n = len(text)
        i = n - 1

        while i >= 0:
            if text[i] == ')':
                break
            i -= 1

        if i < 0 or text[i] != ')':
            return False, ''

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
            return False, ''
        
        return True, text[i + 1:end + 1]

    def __get_split_lines(self, doxy_text):
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

    def __get_doxy_params(self, code, patterns):
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
            errs += 'ERROR: some param name is not designated in the code',
            return RetType.WARN, errs

        return RetType.SUCCESS, errs

    def __get_class_methods_attrs(self, clz, code):
        """
        OUT:
            {"public":[method1, method2], "protected":[method3]}
        """
        logd('+{} of {}'.format(sys._getframe().f_code.co_name, clz))
        if not code:
            return None

        access_mod = collections.defaultdict(list)
        pname, pattern = SearchPatternCpp.get_pattern_methods()
        if not pattern:
            print('ERROR: pattern for {} is not found'.format(pname))
            return

        i = 0
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
            if m:
                expr = expr[m.span()[0]:m.span()[1]].strip()
                logd('method = {}'.format(expr))
                params = self.__split_param(expr)
                ret = self.__split_return(expr, clz)
                access_mod[modifier + ' method'] += (expr, params, ret),
            elif expr and self.__is_attribute(expr):
                access_mod[modifier + ' attribute'] += (expr, None, None),
            i += 1

        #self.__print_class_methods(clz, access_mod)
        logd('-{} of {}'.format(sys._getframe().f_code.co_name, clz) + '\n'*2)
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
            for method, prams, ret in clz_methods[mod]:
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

    def set_suffix_filter(self, suffixes):
        for name in suffixes:
            self.prohibited_suffixes.insert(name[::-1])

    def set_filter_keyword(self, keywords):
        self.filter_keywords += keywords

    def get_code_without_comment(self, file):
        lines = None

        with open(file, 'r') as fp:
            lines = fp.readlines()
            lines = ''.join(lines)
            if lines:
                lines = re.compile("(?s)/\*.*?\*/").sub("", lines)
                lines = re.compile("//.*").sub("", lines)

        return lines

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
        get_each_class_code, clz_codes = self.__get_each_class_code(code)
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
        get_each_class_code, clz_codes = self.__get_each_class_code(code)
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

    def get_doxy_comment_method_chunks(self, code):
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

        patt = re.compile('@\s*param\[\s*(in|out)\s*\]')
        method_m = []

        for item in m:
            start, end = item.span()[0], item.span()[1]
            if not patt.search(code[start:end + 1]):
                continue

            method_m += item,

        pos = 0
        num_pos = len(pos_line)

        for i in range(1, len(method_m)):
            end_pos = method_m[i - 1].span()[1]
            while pos + 1 < num_pos and pos_line[pos][0] < end_pos:
                pos += 1
            res += (pos_line[pos][1], code[method_m[i - 1].span()[0]:method_m[i].span()[0] - 1]),

        if len(method_m) > 0:
            while pos + 1 < num_pos and pos_line[pos][0] < n:
                pos += 1
            res += (pos_line[pos][1], code[method_m[-1].span()[0]:]),

        return res

    def verify_doxycoment_methods(self, comment_code, is_dup_permitted=False):
        res = RetType.SUCCESS
        errs = []
        comment_pattern = re.compile('(?s)\/\*.*?\*\/')
        comment = None
        code = None
        m = comment_pattern.search(comment_code)
        if m:
            comment = comment_code[m.start():m.end()]
            code = re.compile("//.*").sub("", comment_code[m.end() + 1:])

        lines = self.__get_split_lines(comment)

        patterns = {
            'out_param': '@\s*param\s*\[\s*out\s*\]',
            'in_param': '@\s*param\s*\[\s*in\s*\]',
        }

        doxy_params = self.__get_doxy_params(lines, patterns)

        func_code = self.__get_func_code(code)
        if not func_code:
            errs += 'ERROR: no code but comment',
            return RetType.WARN, errs

        code_params = []
        ret, err = self.__get_code_params(func_code, code_params)
        errs += err
        if RetType.ERROR == ret:
            return ret, errs

        for code_param in code_params:
            if code_param not in doxy_params:
                errs += 'ERROR: \'' + code_param + '\' is not documented',
                res = RetType.ERROR

        for doxy_param_name in doxy_params:
            if doxy_param_name not in code_params:
                errs += 'ERROR: \'' + doxy_param_name + \
                    '\' does not exist in the code',
                res = RetType.ERROR
            elif not is_dup_permitted:
                code_params.pop(code_params.index(doxy_param_name))

        if errs:
            errs.insert(0, ' @ {}'.format(func_code))

        return res, errs

    def get_code(self, file):
        lines = None

        with open(file, 'r') as fp:
            lines = fp.readlines()
            lines = ''.join(lines)

        return lines
