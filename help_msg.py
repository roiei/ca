from cmd_interface import *


class HelpHandler(Cmd):
    def __init__(self):
        pass

    def execute(self, opts, cfg):
        print('\t 1. python main.py --cmd=verify --path=directory')
        print('\t\t ex.  python3.6 main.py --cmd=verify --path=./')
        print('\t 2. python main.py --cmd=enum --path=directory')
        print('\t 3. python main.py --cmd=verify_comment --path=directory')
        return True
