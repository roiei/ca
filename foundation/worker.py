from foundation.blocking_queue import *
from enum import Enum


class WorkerState(Enum):
    UNINITED = 1
    IDLE = 2
    RUNNING = 3
    TERMINATING = 4
    TERMINATED = 5


class WorkerCmd(Enum):
    CONTROL = 1
    SET_ARGS = 2
    DATA_DOWN = 3
    DATA_DOWN_LIST = 4
    REQUEST_RESPONSE = 5


class WorkerResult(Enum):
    DONE = 1


class Worker:
    def __init__(self, name):
       self.bq = BlockingQueue()
       self.state = WorkerState.UNINITED
       self.err_items = []
       self.ctx_handler = None
       self.name = name

    def __del__(self):
       pass

    def execute(self, cmd, args):
       self.bq.put((cmd, args))

    def start(self, args=None):
        print('+Worker::start')
        self.thread_ctx = threading.Thread(target=self.loop, args=(args,))
        self.thread_ctx.start()
        self.bq.put((WorkerCmd.CONTROL, 'start'))

    def stop(self):
        if WorkerState.RUNNING == self.state:
            self.bq.put((WorkerCmd.CONTROL, 'stop'))
            self.thread_ctx.join()

    def request_response(self, client) -> None:
        self.bq.put((WorkerCmd.REQUEST_RESPONSE, client))

    def set_handler(self, handler: 'handler') -> None:
        self.bq.put((WorkerCmd.SET_ARGS, handler))

    def loop(self, args: 'variable type') -> None:
        print('+loop:', self.name)
        handler = None
        handler_ctx = None

        self.state = WorkerState.RUNNING
        if args:
            handler = args

        while WorkerState.RUNNING == self.state:
            item = self.bq.get()
            cmd, data = item

            if WorkerCmd.CONTROL == cmd:
                if data == 'stop':
                    self.state = WorkerState.TERMINATING
            
            elif WorkerCmd.SET_ARGS == cmd:
                handler, handler_ctx = data
            elif WorkerCmd.REQUEST_RESPONSE == cmd:
                data.notify((WorkerResult.DONE, self.err_items))
                self.err_items = []
            else:
                if not handler:
                    sys.exit('Handler is not yet set!')
                handler(handler_ctx, cmd, data)

        self.state = WorkerState.TERMINATED
        print('-loop:', self.name)
