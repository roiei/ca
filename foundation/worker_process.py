from enum import Enum
from multiprocessing import Queue, Value
import sys
import os
from console_progressbar import ProgressBar
from util.time_tracker import *


class WorkerState(Enum):
    UNINITED = 1
    IDLE = 2
    RUNNING = 3
    TERMINATING = 4
    TERMINATED = 5


class WorkerCmd(Enum):
    CONTROL = 1
    SET_HANDLER = 2
    DATA_DOWN = 3
    DATA_DOWN_LIST = 4
    REQUEST_RESPONSE = 5
    SET_SHARED_CTX = 6
    PRINT_PROGRESS = 7
    RESET_REQUEST_STATUS = 8
    SET_CUSTOM_CTX = 9
    SET_ELAPSE_START_TIME = 10
    GET_ELAPSE_TIME = 11
    EXPECT_ELAPSE_TIME = 12


class WorkerResult(Enum):
    DONE = 1
    ERROR = 2
    ELAPSE_TIME = 3


class Connector:
    def __init__(self):
        self.in_queue = Queue()
        self.out_queue = Queue()


class ProcessContext:
    def __init__(self, proc, connector):
        self.proc = proc
        self.connector = connector


class RequestStatus:
    def __init__(self):
        self.unit_cnt = 0
        self.req_cnt = 0
        self.req_err_cnt = 0
        self.err_reqs = []

    def reset(self):
        self.unit_cnt = 0
        self.req_cnt = 0
        self.req_err_cnt = 0
        self.err_reqs = []


class HandlerCtx:
    def __init__(self):
        self.is_inited = False
        self.custom_ctx = None
        self.handler_ctx = None


class WorkerProc:
    def __init__(self, handler, connector, name, ctx):
        self.handler = handler
        self.handler_ctx = None
        self.in_queue = connector.in_queue
        self.out_queue = connector.out_queue
        self.name = name
        self.ctx = ctx
        self.prog_bar = ProgressBar(total=100, 
                prefix='', suffix='', decimals=3, 
                length=30, fill='|', zfill='-')

        # elapse time
        self.report_et = False
        self.track_cnt = 0
        self.elapse_wnd_size = 20
        self.elapse_times = []
        self.elapse_time = -1
        self.avg_et = -1
        self.time_tracker = TimeTracker()

    def loop(self) -> None:
        print('+loop:', self.name)
        self.state = WorkerState.RUNNING
        request_status = RequestStatus()
        handler_ctx = HandlerCtx()

        while WorkerState.RUNNING == self.state:
            item = self.in_queue.get()
            cmd, data = item

            if WorkerCmd.CONTROL == cmd:
                if data == 'stop':
                    self.state = WorkerState.TERMINATING
            elif WorkerCmd.SET_HANDLER == cmd:
                self.handler, self.handler_ctx = data
            elif WorkerCmd.SET_SHARED_CTX == cmd:
                self.ctx = data
            elif WorkerCmd.PRINT_PROGRESS == cmd:
                if not self.ctx:
                    sys.exit('ERROR: shared CTX is not set')
                self.print_progress(self.ctx, request_status, data)
            elif WorkerCmd.REQUEST_RESPONSE == cmd:
                res = WorkerResult.DONE if 0 == request_status.req_err_cnt else WorkerResult.ERROR
                self.out_queue.put((res, (self.name, request_status)))
            elif WorkerCmd.RESET_REQUEST_STATUS == cmd:
                request_status.reset()
            elif WorkerCmd.SET_CUSTOM_CTX == cmd:
                handler_ctx.custom_ctx = data
            elif WorkerCmd.SET_ELAPSE_START_TIME == cmd:
                time_tracker.set_time(data, TimeElapseType.START)
            elif WorkerCmd.GET_ELAPSE_TIME == cmd:
                time_tracker.set_time(data, TimeElapseType.END)
                self.out_queue.put((WorkerResult.ELAPSE_TIME, time_tracker.get_total_time(data)))
            elif WorkerCmd.EXPECT_ELAPSE_TIME == cmd:
                self.report_et = data
                self.track_cnt = 0
                self.elapse_time = 0
                self.elapse_times = []
            else:
                if not self.handler:
                    sys.exit('Handler is not yet set!')

                self.set_start_time()
                request_status.unit_cnt = len(data) if type(data) is list else 1
                request_status.req_cnt += request_status.unit_cnt
                errs = self.handler(self.name, cmd, data, handler_ctx)
                if errs:
                    request_status.err_reqs += errs
                    request_status.req_err_cnt += len(errs)
                self.update_elapse_time()

        self.state = WorkerState.TERMINATED
        print('-loop:', self.name)

    def set_start_time(self):
        if self.report_et:
            self.time_tracker.set_time('handler', TimeElapseType.START)

    def update_elapse_time(self):
        if self.report_et:
            self.time_tracker.set_time('handler', TimeElapseType.END)
            et = self.time_tracker.get_total_time('handler')

            self.elapse_times += et,
            self.elapse_time += et
            if len(self.elapse_times) >= self.elapse_wnd_size:
                self.elapse_time -= self.elapse_times.pop(0)

            self.avg_et = self.elapse_time/len(self.elapse_times)

    def print_progress(self, ctx, request_status, overall_prog):
        prog_cnt, prog_num = ctx
        prog_cnt.value += request_status.unit_cnt   # need to protect it by mutex ?

        self.prog_bar.print_progress_bar(prog_cnt.value/prog_num.value*100)

        if not request_status.req_cnt:
            return

        overall_prog, unit_percent = overall_prog
        tot_prog = overall_prog + prog_cnt.value*(unit_percent/prog_num.value)

        pnt_arg = '[proc={:3}, pid={:7}] prog:{:.2f}%, overall:{:.2f}%, err:{:.2f}%'.format(
            self.name,
            os.getpid(),
            prog_cnt.value/prog_num.value*100,
            tot_prog,
            request_status.req_err_cnt/request_status.req_cnt*100
            )

        if self.report_et and -1 != self.avg_et:
            left_time = self.avg_et*((100 - tot_prog)/(unit_percent/prog_num.value))
            pnt_arg += ', lt:{:.2f} s, {:.2f} m, avget:{:.2f}'.format(left_time, left_time/60, self.avg_et)

        print(pnt_arg)

    @staticmethod
    def start_work(handler, connector, name, ctx):
        worker_process = WorkerProc(handler, connector, name, ctx)
        worker_process.loop()