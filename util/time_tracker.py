import time
import datetime
import collections
from enum import Enum


class TimeElapseType(Enum):
    START = 1
    MID = 2
    END = 3


class TimeTracker:
    def __init__(self):
        pass

    def __del__(self):
        pass

    times = collections.defaultdict(dict)

    @classmethod
    def set_time(cls, marker: 'key', elapse_type: TimeElapseType):
        cls.times[marker][elapse_type] = time.time()

    @classmethod
    def get_time(cls, marker: 'key', elapse_type: TimeElapseType):
        return cls.times[marker][elapse_type]

    @classmethod
    def get_total_time(cls, marker: 'key') -> 'time in second':
        if not cls.times[marker][TimeElapseType.START] or not cls.times[marker][TimeElapseType.END]:
            return -1

        return cls.times[marker][TimeElapseType.END] - cls.times[marker][TimeElapseType.START]

    @classmethod
    def get_markers(cls):
        return cls.times.keys()

    @staticmethod
    def get_time():
        return str(datetime.datetime.today().strftime("%Y%m%d_%H%M%S"))
