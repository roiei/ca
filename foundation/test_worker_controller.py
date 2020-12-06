from worker_controller import *


class CustomeWorkerCmd(Enum):
    TEST1 = 1
    TEST2 = 2


def handler(name, cmd, data):
    print('+handler')
    if CustomeWorkerCmd.TEST1 == cmd:
        print(name, ': got TEST1 cmd, data to process = ', data)
        return True

    print('error: UNDEF. cmd = ', cmd)
    return False


if __name__ == '__main__':
    worker_ctrlr = WorkerController(2)
    worker_ctrlr.do_job(list(range(10)), CustomeWorkerCmd.TEST1, handler)
    worker_ctrlr = None
