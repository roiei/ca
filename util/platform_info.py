import platform


class PlatformInfo:
    def __init__(self):
        pass

    @staticmethod
    def is_Linux():
        plt = platform.system()
        return 'Linux' in plt

    @staticmethod
    def get_delimiter():
        if PlatformInfo.is_Linux():
            return '/'
        else:
            return '\\'
