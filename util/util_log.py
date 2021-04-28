


class Logger:
    def __init__(self, onoff):
        self.on = onoff

    def __del__(self):
        pass

    def log(self, log):
        if self.on:
            print(log)
