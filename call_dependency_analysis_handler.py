from cmd_interface import *
from util.util_file import *
from util.util_print import *
import copy
import collections
from visualization.networkx_adapter import *
from util.platform_info import *
from cmake_parser import *
from pro_parser import *
from module_types import *
from dependency_config import *
from syntax_parser_factory import *
import matplotlib.pyplot as plt
import matplotlib.table as tbl
import numpy as np  


class BuildScriptParser:
    def build_dep_graph(self, url):
        pass


class CallStats:
    def __init__(self):
        self.non_called_method_num = 0
        self.called_method_num = 0
        self.num_methods = 0


class MethodCallInfo:
    def __init__(self):
        self.dir_info = collections.defaultdict(
            lambda: collections.defaultdict(
                lambda: collections.defaultdict(int)))
        self.method_freqs = collections.defaultdict(list)
        self.method_clzs  = collections.defaultdict(set)


class CallDependencyAnalysisHandler(Cmd):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        self.get_methods(opts, cfg)

    def _write_method_info(self, callinfo, url):
        print('save')
        for k, v in callinfo.method_clzs.items():
            callinfo.method_clzs[k] = list(v)

        dir_info = {}
        for dir_name, clz_info in callinfo.dir_info.items():
            if dir_name not in dir_info:
                dir_info[dir_name] = {}

            for clz_name, method_info in callinfo.dir_info[dir_name].items():
                if clz_name not in dir_info[dir_name]:
                    dir_info[dir_name] [clz_name] = {}

                for method_name, freq in callinfo.dir_info[dir_name][clz_name].items():
                    if method_name not in dir_info[dir_name] [clz_name]:
                        dir_info[dir_name] [clz_name][method_name] = 0

        adict = {
            'method_freq': callinfo.method_freqs,
            'method_clzs': callinfo.method_clzs,
            'dir_info': dir_info
        }

        with open(url, "w", encoding='utf-8') as fp:
            json.dump(adict, fp)
        return True

    def _read_method_info(self, callinfo, url):
        with open(url, "r", encoding='utf-8') as fp:
            adict = json.load(fp)

        for name, freq in adict['method_freq'].items():
            callinfo.method_freqs[name] = freq

        for name, clz_list in adict['method_clzs'].items():
            callinfo.method_clzs[name] = set(clz_list)

        dir_info = adict['dir_info']
        for dir_name, clz_info in dir_info.items():
            for clz_name, method_info in dir_info[dir_name].items():
                for method_name, freq in dir_info[dir_name][clz_name].items():
                    callinfo.dir_info[dir_name][clz_name][method_name] = \
                        dir_info[dir_name][clz_name][method_name]

    def get_methods(self, opts, cfg):
        callinfo = MethodCallInfo()

        if 'loadfile' in opts:
            self._read_method_info(callinfo, opts['loadfile'])
        else:
            callinfo = self.get_method_names(opts, cfg)
            if not callinfo:
                return False, None

        if 'savefile' in opts:
            self._write_method_info(callinfo, opts['savefile'])
            return

        locations = UtilFile.get_dirs_files(opts["upath"], \
            cfg.get_recursive(), ['cpp'])
        if not locations:
            return None

        syntax_parsers = collections.defaultdict(None)
        syntax_parsers[FileType.CPP_IMPL] = SyntaxParserFactory.create('cpp')
        if not syntax_parsers[FileType.CPP_IMPL]:
            print('ERROR: not supported extension', FileType.CPP_IMPL)
            return None

        for directory, files in locations.items():
            if not files:
                continue

            for file, file_type in files:
                if file_type not in syntax_parsers:
                    continue

                # todo: + finding class 

                parser = syntax_parsers[file_type]
                code = parser.get_code_without_comment(file)
                if not code:
                    continue

                #print(file)
                calls = parser.find_method_calls(code)

                self.update_freq(calls, callinfo)

        self.update_dir_info(callinfo)
        dir_stats = self.calc_dir_stats(callinfo)

        for dname, dstat in dir_stats.items():
            if not dname.startswith('ccos.'):
                continue

            self.print_call_stats(dstat, dname)
            print()
            # for cname, method_info in callinfo.dir_info[dname].items():
            #     print(cname)
            #     for mname, freq in method_info.items():
            #         print('\t', mname, freq)

        self.print_result(callinfo)
        #self.print_targetfreq_methods(callinfo, 0)
        #self.print_above_targetfreq_methods(callinfo, 0)

        #self.draw_result_tbl(callinfo) # possible but data is too big to use it

    def update_freq(self, calls, callinfo):
        for method, freq in calls.items():
            if method in callinfo.method_freqs:
                callinfo.method_freqs[method] += 1

            sidx = method.find('::')
            caller, method = method[:sidx], method[sidx + 2:]
            #print(caller, method)

            if method in callinfo.method_freqs:
                callinfo.method_freqs[method] += 1

    def update_dir_info(self, callinfo):
        for dname, clz_info in callinfo.dir_info.items():
            for cname, method_info in clz_info.items():
                for mname, freq in method_info.items():
                    if mname in callinfo.method_freqs:
                        callinfo.dir_info[dname][cname][mname] = \
                            callinfo.method_freqs[mname]

    def calc_dir_stats(self, callinfo):
        dir_stats = collections.defaultdict(CallStats)

        for dname, clz_info in callinfo.dir_info.items():
            tot_call_num = 0
            called_call_num = 0

            for cname, method_info in clz_info.items():
                tot_call_num += len(method_info.keys())

                for mname, freq in method_info.items():
                    if freq > 0:
                        called_call_num += 1

            dir_stats[dname].num_methods = tot_call_num
            dir_stats[dname].called_method_num = called_call_num
            dir_stats[dname].non_called_method_num = tot_call_num - called_call_num

        return dir_stats

    def print_call_stats(self, stats, title=''):
        cols = ['# methods', '# called', '# called %', '# not called', '# not called %']
        rows = []
        col_widths = [12, 12, 12, 12, 14]

        row = []
        row += ('{:<12d}', stats.num_methods),
        row += ('{:<12d}', stats.called_method_num),
        row += ('{:<.3f} %', (stats.called_method_num/stats.num_methods)*100),
        row += ('{:<12d}', stats.non_called_method_num),
        row += ('{:<.3f} %', (stats.non_called_method_num/stats.num_methods)*100),
        rows += row,

        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)

    def print_result(self, callinfo):
        cols = ['method', 'freq', 'candidates']
        col_widths = [30, 5, 80]
        rows = []
        stats = CallStats()

        call_freqs = sorted(callinfo.method_freqs.items(), reverse=True, key=lambda p: p[1])
        methods = []
        freqs = []
        for k, v in call_freqs:
            methods += k,
            freqs += v,
            if v:
                stats.called_method_num += 1
            stats.num_methods += 1

        stats.non_called_method_num = stats.num_methods - stats.called_method_num

        self.print_call_stats(stats)

        candidates = []
        for method in methods:
            candidates += callinfo.method_clzs[method],

        for i in range(len(methods)):
            row = []
            row += ('{:<12s}', methods[i]),
            row += ('{:<12d}', freqs[i]),
            row += ('{:<12s}', ', '.join(candidates[i])),
            rows += row,

        UtilPrint.print_lines_with_custome_lens(' * call freq.', 
            col_widths, cols, rows)

    def print_above_targetfreq_methods(self, callinfo, target_freq):
        print('+print_above_targetfreq_methods')
        for method, freq in callinfo.method_freqs.items():
            if '::' in method:
                continue
            if freq > target_freq:
                print('method = {}, freq = {}, suspicious = {}'.format(
                    method, freq, callinfo.method_clzs[method]))

    def print_targetfreq_methods(self, callinfo, target_freq):
        print('+print_no_ref_methods')
        for method, freq in callinfo.method_freqs.items():
            if '::' in method:
                continue
            if freq == target_freq:
                print('method = {}, freq = {}, suspicious = {}'.format(
                    method, freq, callinfo.method_clzs[method]))

    def draw_result_tbl(self, callinfo):
        print('+')
          
        colLabels  = ['method', 'freq', 'candidate']
        methods    = list(callinfo.method_freqs.keys())
        freqs      = list(callinfo.method_freqs.values())
        candidates = []

        for method in methods:
            candidates += callinfo.method_clzs[method],

        cell_vals = []
        for i in range(len(methods)):
            #cell_vals += [methods[i], freqs[i], candidates[i]],
            cell_vals += [methods[i], freqs[i], ""],

        val1 = ["{:X}".format(i) for i in range(10)]
        val2 = ["{:02X}".format(10 * i) for i in range(10)]
        val3 = [["" for c in range(10)] for r in range(10)]

        fig, ax = plt.subplots()
        ax.set_axis_off()
        table = tbl.table(
            ax,
            cellText = cell_vals[:10],
            #rowLabels = val2,
            colLabels = colLabels,
            #rowColours = ["palegreen"] * 10,
            colColours =["palegreen"] * 3,
            cellLoc ='center', 
            loc ='upper left')
          
        ax.add_table(table)
        ax.set_title('result', fontweight ="bold")
        plt.show()

    def get_method_names(self, opts, cfg):
        locations = UtilFile.get_dirs_files(opts["ppath"], \
            cfg.get_recursive(), cfg.get_extensions())
        if not locations:
            return None

        syntax_parsers = collections.defaultdict(None)
        syntax_parsers[FileType.CPP_HEADER] = SyntaxParserFactory.create('hpp')
        if not syntax_parsers[FileType.CPP_HEADER]:
            print('ERROR: not supported extension', FileType.CPP_HEADER)
            return None

        file_clz_methods = collections.defaultdict(None)
        callinfo = MethodCallInfo()

        for directory, files in locations.items():
            if not files:
                continue

            for file, file_type in files:
                if file_type not in syntax_parsers:
                    continue

                parser = syntax_parsers[file_type]

                whole_code = parser.get_code_without_comment(file)
                if not whole_code:
                    continue

                clz_methods = parser.get_methods(whole_code)
                if not clz_methods:
                    continue

                for clz, method_info in clz_methods.items():
                    if not (clz.startswith('H') or clz.startswith('IH')):
                        continue

                    self.find_methods(parser, callinfo, directory, clz, method_info)

                file_clz_methods[file] = clz_methods

        return callinfo

    def find_methods(self, parser, callinfo, directory, clz, method_info):
        for scope, methods in method_info.items():            
            if 'public' not in scope:
                continue

            for method in methods:
                method_name = parser.get_method_name(method[0])

                if method_name == clz or \
                    method_name[1:] == clz or \
                    'operator' in method_name:
                    continue

                # if method_name == '=':
                #     print(method)

                clz_method = clz + '::' + method_name

                callinfo.method_clzs[method_name].add(clz)

                if method_name not in callinfo.method_freqs:
                    callinfo.method_freqs[method_name] = 0

                if clz_method not in callinfo.method_freqs:
                    callinfo.method_freqs[clz_method] = 0

                dir_chunks = directory.split(PlatformInfo.get_delimiter())
                start = 0
                if len(dir_chunks) >= 2:
                    start = -2
                directory = '-'.join(dir_chunks[start:])

                if method_name not in callinfo.dir_info[directory][clz]:
                    callinfo.dir_info[directory][clz][method_name] = 0

                if clz_method not in callinfo.dir_info[directory][clz]:
                    callinfo.dir_info[directory][clz][method_name] = 0