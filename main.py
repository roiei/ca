#!/usr/bin/python3.6

import os
import sys
from verify import *
from help_msg import *
from config_reader import *
#from boot_splash import *
from option import *
from util.time_tracker import *
from doxygen_comment_handler import *
from verify_handler import *
from enum_handler import *
from util.platform_info import *


def override_cfg(cfg, opts):
    if 'recursive' not in opts:
        return 
    #print(opts['recursive'])
    recur = False
    if 'True' == opts['recursive']:
        recur = True
    cfg.set_recursive(recur)


sys_ver_info = tuple(list(sys.version_info)[:3])
if sys_ver_info < (3, 5, 0):
    sys.exit('Python version {}-{}-{}, is not supported. Use more than 3.5'.
        format(*sys_ver_info))


cmd_handlers = {}
cmd_handlers['help'] = (
        HelpHandler(), 
        '--cmd=help'
    )
cmd_handlers['verify'] = (
        CPPVerificationHandler(), 
        '--cmd=verify --path=./'
    )
cmd_handlers['enum'] = (
        EnumerateCPPMethodHandler(), 
        '--cmd=enum --path=./'
    )
cmd_handlers['verify_comment'] = (
        DoxygenVerificationHandler(),
        '--cmd=verify_comment --path=./'
    )


def print_cmd_help(cmd_handlers):
    print(' <<HELP>>')
    print('-'*50)
    for cmd, desc in cmd_handlers.items():
        print('cmd = ', cmd)
        for line in desc[1:]:
            print(line)
        print()
    print('-'*50)


def execute_handler(cmd, opts, cfg):
    if cmd not in cmd_handlers or not cmd:
        print('Not supported command \'{}\''.format(cmd))
        print_cmd_help(cmd_handlers)
        return None

    time_tracker = TimeTracker()
    time_tracker.set_time(cmd, TimeElapseType.START)
    res = cmd_handlers[cmd][0].execute(opts, cfg)
    time_tracker.set_time(cmd, TimeElapseType.END)
    #print('ELAPED TIME: {:.3f} sec.'.format(time_tracker.get_total_time(opts.cmd)))
    return res


def execute(cmd, opts):
    delimeter = PlatformInfo.get_delimiter()
    cfg_reader = ConfigReader(os.path.dirname(os.path.realpath(__file__)) + \
        delimeter + '/cfg_csi.conf')
    csi_cfg_json = cfg_reader.readAsJSON()
    cfg = cfg_reader.getConfig(csi_cfg_json)
    override_cfg(cfg, opts)

    res = execute_handler(cmd, opts, cfg)
    if not res:
        print('Not supported cmd')
        return False
    return True


if __name__ == '__main__':
    opts = get_opts(sys.argv)

    if 'cover' not in opts:
        opts['cover'] = 'must'  # default: must

    try:
        cmd = opts["cmd"]
    except KeyError:
        print('ERROR: wrong parameter')
        print_help(sys.argv)
        sys.exit()
    
    ret = execute(cmd, opts)
    exit_code = 1 if not ret else 0
    sys.exit(exit_code)
