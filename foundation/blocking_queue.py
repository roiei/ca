
import threading


class BlockingQueue:
    def __init__(self):
        self.data = []
        self.n = 0
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)

    def __del__(self):
        pass

    def put(self, data):
        with self.cv:
            self.data += data,
            self.n += 1
            self.cv.notifyAll()

    def get(self):
        ret = None
        with self.cv:
            if self.n == 0:
                self.cv.wait()
            if self.n > 0:
                ret = self.data.pop(0)
                self.n -= 1
        return ret

