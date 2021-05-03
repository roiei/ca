import re
from enum import Enum


class ReturnType(Enum):
    SUCCESS = 0
    FILE_OPEN_ERR = 1
    UNICODE_ERR = 2


class CppParser:
    def __init__(self):
        pass

    def __del__(self):
        pass

    @staticmethod
    def open_file(url, encoding='UTF8'):
        try:
            fp = open(url, 'r', encoding=encoding)
        except FileNotFoundError as e:
            print(e, 'for ', url)
            return None
        except IsADirectoryError as e:
            print(e, 'for ', url)
            return None
        except PermissionError as e:
            print(e, 'for ', url)
            return None

        return fp

    @staticmethod
    def get_lines(url, lines, encoding='utf-8'):
        fp = CppParser.open_file(url, encoding)
        if not fp:
            return ReturnType.FILE_OPEN_ERR

        try:
            lines += fp.readlines()
        except UnicodeDecodeError as e:
            #print('UnicodeDecodeError:', e, 'for ', url)
            fp.close()
            return ReturnType.UNICODE_ERR

        fp.close()
        return ReturnType.SUCCESS

    @staticmethod
    def get_code_only(url):
        lines = []
        res = CppParser.get_lines(url, lines, 'utf-8')
        if res == ReturnType.UNICODE_ERR:
            res = CppParser.get_lines(url, lines, 'euc-kr')
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