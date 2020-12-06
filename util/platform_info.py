import platform


class PlatformInfo:
    def __init__(self):
        pass

    @staticmethod
    def is_Linux():
        return 'Linux' in platform.system()

    @staticmethod
    def get_delimiter():
        if PlatformInfo.is_Linux():
            return '/'
        else:
            return '\\'
