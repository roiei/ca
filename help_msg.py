from cmd_interface import *


class HelpHandler(Cmd):
    def __init__(self):
        pass

    def execute(self, opts, cfg):
        print('\t 1. python3.6 main.py --cmd=verify --path=directory')
        print('\t\t ex.  python3.6 main.py --cmd=verify --path=./')
        return True
