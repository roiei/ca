
from foundation.worker import *
import sys


class WorkerManager:
    def __init__(self, num_threads):
        self.workers = []
        self.num_threads = num_threads
        self.bq = BlockingQueue()

        for i in range(num_threads):
            self.workers += Worker(str(i)),

    def __del__(self):
        len(self.workers)
        for i in range(self.num_threads):
            self.workers[i].stop()

    def get_jobs(self):
        return self.num_threads

    def start(self):
        for i in range(self.num_threads):
            self.workers[i].start()

    def stop(self):
        for i in range(self.num_threads):
            self.workers[i].stop()

    def do_requests(self, cmd, requests_arg: 'a list of requests') -> ['errors']:
        n = len(requests_arg)
        num_thr = self.num_threads

        if n >= num_thr:
            num_chunk = n//num_thr
        else:
            num_chunk = n
            num_thr = n

        jobs = []
        errs = []

        print('thr = ', num_thr)
        print('n = {}, num_chunk = {}, left = {}'.format(n, num_chunk, n%num_thr))

        sizes = [num_chunk]*num_thr
        if n%num_thr:
            sizes[-1] += n%num_thr

        offset = 0
        for i in range(len(sizes)):
            jobs += requests_arg[offset:offset + sizes[i]],
            offset += sizes[i]

        for i in range(num_thr):
            for job in jobs[i]:
                self.workers[i].execute(cmd, job)
            self.workers[i].request_response(self)

        cnt = 0
        for i in range(num_thr):
            resp, err_items = self.bq.get()
            if WorkerResult.DONE == resp and not err_items:
                #print('got done resp.')
                cnt += 1
            else:
                print('ERROR: download error for the following items')
                for err_item in err_items:
                    print(err_items)
                errs += err_items

        print('-do_requests')

        if cnt < num_thr:
            print('error: there is threads haven\'t notified yet')

        return errs

    def notify(self, result):
        #print('notified', result)
        if WorkerResult.DONE == result[0]:
            self.bq.put(result)

    def set_handler(self, args):
        for i in range(self.num_threads):
            self.workers[i].set_handler(args)

    def set_handler_context(self, ctx_handler, ctx):
        for i in range(self.num_threads):
            self.workers[i].set_handler_context(ctx_handler, ctx)
