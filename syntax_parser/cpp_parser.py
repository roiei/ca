import re
from enum import Enum
from util.util_file import *


class CppParser:
    def __init__(self):
        pass

    def __del__(self):
        pass

    @staticmethod
    def get_code_only(url):
        lines = []
        res = UtilFile.get_lines(url, lines, 'utf-8')
        if res == ReturnType.UNICODE_ERR:
            res = UtilFile.get_lines(url, lines, 'euc-kr')
        elif res != ReturnType.SUCCESS:
            return None

        if not lines:
            print('Err: not possible to read: ', url)
            return None

        try:
            lines = ''.join(lines)
        except TypeError as e:
            print(e, 'for ', url)

        #print(lines)

        if lines:
            lines = re.compile("(?s)/\*.*?\*/").sub("", lines)
            lines = re.compile("//.*").sub("", lines)

        return lines