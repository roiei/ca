import getopt
import sys


def get_opts(args):
    opts = {}
    params = ' '.join(args).split(' --')
    for param in params:
        param = param.split('=')
        if not len(param) == 2:
            continue

        key, value = param
        opts[key] = value

    print(opts, end='\n\n')
    return opts
