from enum import Enum
from foundation.worker_process import *
from multiprocessing import Queue, Process, Value
import collections


def print_progress(ctx):
    prog_cnt, prog_num = ctx
    prog_cnt.value += 1
    print('progress: {:2.f}%'.format(prog_cnt.value/prog_num.value*100))


class WorkerController:
    def __init__(self, num_worker):
        self.num_worker = num_worker
        self.procs = collections.defaultdict(lambda proc, connector: ProcessContext(proc, connector))
        self.prog_cnt = Value('d', 0.0)
        self.prog_num = Value('d', 0.0)

        for i in range(num_worker):
            name = str(i)
            connector = Connector()
            p = Process(target=WorkerProc.start_work, args=(None, connector, str(i), (self.prog_cnt, self.prog_num)))
            p.start()
            self.procs[name] = ProcessContext(p, connector)

    def __del__(self):
        self.stop_procs()
        self.join()

    def distribute_job(self, items, cmd, overall_prog, handler, handler_ctx=None):
        n = len(items)

        self.prog_cnt.value = 0     # <- shared ctx, Value (used by each process)
        self.prog_num.value = n     # <- shared ctx, Value (used by each process)

        #print('+dist job: ', self.prog_cnt.value, self.prog_num.value)

        # 1: 0 ~ 1.9(1)
        # 2: 1.9 (1) ~ 3.6(3)
        # 3: 3.6(3) ~ 5.7(5)
        # ...
        # 10: 17.1(17) ~ 19

        chunk = n/self.num_worker

        for i in range(self.num_worker):
            self.procs[str(i)].connector.in_queue.put((WorkerCmd.SET_HANDLER, (handler, handler_ctx)))

        i = 0
        while i < self.num_worker:
            start = int(i*chunk)
            end = n if i == self.num_worker - 1 else int(i*chunk + chunk)
            thr = str(i)

            for job_idx in range(start, end):
                try:
                    self.procs[thr].connector.in_queue.put((cmd, items[job_idx]))
                except IndexError as e:
                    print('job_idx = ', job_idx, n)

                self.procs[thr].connector.in_queue.put((WorkerCmd.PRINT_PROGRESS, 
                        overall_prog))

            i += 1

    def distribute_batch_job(self, items, cmd, overall_prog, handler, handler_ctx=None):
        n = len(items)

        self.prog_cnt.value = 0     # <- shared ctx, Value (used by each process)
        self.prog_num.value = n     # <- shared ctx, Value (used by each process)

        chunk = n/self.num_worker

        for i in range(self.num_worker):
            self.procs[str(i)].connector.in_queue.put((WorkerCmd.SET_HANDLER, (handler, handler_ctx)))

        i = 0
        while i < self.num_worker:
            start = int(i*chunk)
            end = n if i == self.num_worker - 1 else int(i*chunk + chunk)

            self.procs[str(i)].connector.in_queue.put((cmd, items[start:end]))
            self.procs[str(i)].connector.in_queue.put((WorkerCmd.PRINT_PROGRESS, overall_prog))
            i += 1

    def get_resp(self):
        resps = None
        for i in range(self.num_worker):
            self.procs[str(i)].connector.in_queue.put((WorkerCmd.REQUEST_RESPONSE, None)),

        for i in range(self.num_worker):
            res, data = self.procs[str(i)].connector.out_queue.get()
            name, request_status = data

            if WorkerResult.DONE != res:
                print('ERROR: failure of request in process \'{}\''.format(name))
                for err_item in request_status.err_reqs:
                    print('\t error item = ', err_item)
                print()
                resps = request_status.err_reqs

        return resps

    def stop_procs(self):
        for i in range(self.num_worker):
            self.procs[str(i)].connector.in_queue.put((WorkerCmd.CONTROL, 'stop'))

    def reset_request_status(self):
        resps = []
        for i in range(self.num_worker):
            resps += self.procs[str(i)].connector.in_queue.put((WorkerCmd.RESET_REQUEST_STATUS, None)),
        return resps

    def join(self):
        for i in range(self.num_worker):
            self.procs[str(i)].proc.join()

    def do_job(self, items, do_cmd, overall_prog, handler, handler_ctx=None):
        self.reset_request_status()
        self.distribute_job(items, do_cmd, overall_prog, handler, handler_ctx)
        return self.get_resp()

    def do_batch_job(self, items, do_cmd, overall_prog, handler, handler_ctx=None):
        self.reset_request_status()
        self.distribute_batch_job(items, do_cmd, overall_prog, handler, handler_ctx)
        return self.get_resp()

    def set_custom_ctx(self, ctx):
        for i in range(self.num_worker):
            self.procs[str(i)].connector.in_queue.put((WorkerCmd.SET_CUSTOM_CTX, ctx))
