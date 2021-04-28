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
from util.util_log import *
from cpp_parser import *


DEBUG_MSG_ON = False


class CppImplParser(SyntaxParser):
    def __init__(self, name):
        super().__init__(name)

    def __del__(self):
        super().__del__()

    def get_code_without_comment(self, url):
        return CppParser.get_code_only(url)

    def find_method_calls(self, code):
        #print(code)
        calls = collections.defaultdict(int)

        pattern = re.compile('(::|\.|->)[\w]+\s*\([\w\s]*\)\s*;')
        m = pattern.finditer(code)
        for r in m:
            span = r.span()
            sx, ex = span[0], span[1]

            while sx < ex and code[sx] in ':->.':
                sx += 1

            method = code[sx:ex + 1]
            ex = method.find('(')
            method = method[:ex]
            #print('method = ', method)
            calls[method] += 1

        return calls

            