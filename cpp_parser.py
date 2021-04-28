import re


class CppParser:
    def __init__(self):
        pass

    def __del__(self):
        pass

    @staticmethod
    def get_code_only(url):
        lines = None

        try:
            fp = open(url, 'r')
        except FileNotFoundError as e:
            print(e, 'for ', url)
            return None
        except IsADirectoryError as e:
            print(e, 'for ', url)
            return None

        try:
            lines = fp.readlines()
        except UnicodeDecodeError as e:
            print(e, 'for ', url)
            return None

        try:
            lines = ''.join(lines)
        except TypeError as e:
            print(e, 'for ', url)

        if lines:
            lines = re.compile("(?s)/\*.*?\*/").sub("", lines)
            lines = re.compile("//.*").sub("", lines)

        fp.close()
        return lines