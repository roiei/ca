from multiprocessing import Process, Queue
import collections
from worker_process import *


#process.daemon = True  # terminate all the child processes when the parent dies


class CustomeWorkerCmd(Enum):
    TEST1 = 1
    TEST2 = 2


def handler1(name, cmd, data):
    print('+handler1')
    if CustomeWorkerCmd.TEST1 == cmd:
        print(name, ' test ', data)
    else:
        print('error: UNDEF. cmd = ', cmd)


def handler2(name, cmd, data):
    print('+handler2')
    if CustomeWorkerCmd.TEST2 == cmd:
        print(name, ' test ', data)
    else:
        print('error: UNDEF. cmd = ', cmd)


if __name__ == '__main__':
    n = 5
    procs = collections.defaultdict(lambda proc, connector: ProcessContext(proc, connector))
    ctx = [0]

    for i in range(n):
        name = str(i)
        connector = Connector()

        p = Process(target=WorkerProc.start_work, args=(handler1, connector, str(i), ctx))
        p.start()

        procs[name] = ProcessContext(p, connector)

    print('sending \'test\' cmd')
    for i in range(n):
        procs[str(i)].connector.in_queue.put((CustomeWorkerCmd.TEST1, str(i)))

    for i in range(n):
        procs[str(i)].connector.in_queue.put((WorkerCmd.REQUEST_RESPONSE, None))

    for i in range(n):
        procs[str(i)].connector.in_queue.put((WorkerCmd.SET_HANDLER, handler2))

    for i in range(n):
        procs[str(i)].connector.in_queue.put((CustomeWorkerCmd.TEST2, str(i)))

    for i in range(n):
        procs[str(i)].connector.in_queue.put((WorkerCmd.CONTROL, 'stop'))

    for i in range(n):
        procs[str(i)].proc.join()

    print('print res')

    for i in range(n):
        while not procs[str(i)].connector.out_queue.empty():
            print('{:<3d}: res = {}'.format(i, procs[str(i)].connector.out_queue.get()))
