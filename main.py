#!/usr/bin/python

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from help_msg import HelpHandler
from config_reader import ConfigReader, Config
from option import get_opts
from comment import DoxygenVerificationHandler
from design_verification import CPPVerificationHandler
from enu import EnumerateCPPMethodHandler, LoCHandler
from dependency import DependencyAnalysisHandler, CallDependencyAnalysisHandler
from generate_views import ViewGenerationHandler
from complexity import ComplexityAnalysisHandler
from util import PlatformInfo
from util import TimeTracker, TimeElapseType
from typing import Dict


def override_cfg(cfg, opts):
    if 'recursive' in opts:
        cfg.set_recursive(opts['recursive'])

    if 'recursive_depth' in opts:
        cfg.set_recursive(True)
        cfg.set_recursive_depth(int(opts['recursive_depth']))


sys_ver_info = tuple(list(sys.version_info)[:3])
if sys_ver_info < (3, 5, 0):
    sys.exit('Python version {}-{}-{}, is not supported. Use more than 3.5'.
        format(*sys_ver_info))


cmd_handlers = {
    'help': (
        HelpHandler(), 
        '--cmd=help'
    ),
    'verify': (
        CPPVerificationHandler(), 
        '--cmd=verify --path=./'
    ),
    'enum': (
        EnumerateCPPMethodHandler(), 
        '--cmd=enum --path=./'
    ),
    'verify_comment': (
        DoxygenVerificationHandler(),
        '--cmd=verify_comment --path=./ [--recursive_depth=2]'
    ),
    'dependency': (
        DependencyAnalysisHandler(),
        '--cmd=dependency --path=./ --prj=prj  [--graph=True] [--node=node_name_to_highlight]'
    ),
    'call_dependency': (
        CallDependencyAnalysisHandler(),
        '--cmd=call_dependency --ppath=./ --upath=./  [--savefile=name] \
        [--loadfile=name]'
    ),
    'generate_view': (
        ViewGenerationHandler(),
        '--cmd=generate_view --input=input_data_file --output=output_data_file'
    ),
    'complexity': (
        ComplexityAnalysisHandler(),
        '--cmd=complexity --path=path [--recursive_depth=2]'
    ),
    'loc': (
        LoCHandler(),
        '--cmd=loc --path=path'
    )
}


def print_cmd_help(cmd_handlers):
    print(' <<HELP>>')
    print('-'*50)
    for cmd, desc in cmd_handlers.items():
        print('cmd = ', cmd)
        for line in desc[1:]:
            print(line)
        print()
    print('-'*50)


def execute_handler(cmd: str, opts: Dict, cfg: Config) -> bool:
    if cmd not in cmd_handlers or not cmd:
        print('Not supported command \'{}\''.format(cmd))
        print_cmd_help(cmd_handlers)
        return False

    time_tracker = TimeTracker()
    time_tracker.set_time(cmd, TimeElapseType.START)
    res = cmd_handlers[cmd][0].execute(opts, cfg)
    time_tracker.set_time(cmd, TimeElapseType.END)
    #print('ELAPED TIME: {:.3f} sec.'.format(time_tracker.get_total_time(opts.cmd)))
    return res


def execute(cmd: str, opts: Dict) -> bool:
    delimeter = PlatformInfo.get_delimiter()
    cfg_reader = ConfigReader(os.path.dirname(os.path.realpath(__file__)) + \
        delimeter + 'config' + delimeter + 'cfg_csi.conf')
    cfg = cfg_reader.getConfig(cfg_reader.readAsJSON())
    override_cfg(cfg, opts)

    res = execute_handler(cmd, opts, cfg)
    if not res:
        print('executor returns error')
        return False
    return True


if __name__ == '__main__':
    opts = get_opts(sys.argv)

    if 'cover' not in opts:
        opts['cover'] = 'must'  # default: must
    
    if 'prj' not in opts:
        opts['prj'] = 'default'

    try:
        cmd = opts["cmd"]
    except KeyError:
        print('ERROR: wrong parameter')
        print_cmd_help(cmd_handlers)
        sys.exit()
    
    ret = execute(cmd, opts)
    exit_code = 1 if not ret else 0
    sys.exit(exit_code)
