

class ModuleInfo:
    def __init__(self):
        self.name = ''
        self.type = ''
        self.fan_outs = set()   # dependency
        self.depth = 0
        self.url = ''
        self.fan_ins = set()
        self.instability = 0
