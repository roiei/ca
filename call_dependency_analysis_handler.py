from cmd_interface import *
from util.util_file import *
import copy
import collections
from visualization.networkx_adapter import *
from util.platform_info import *
from cmake_parser import *
from pro_parser import *
from module_types import *
from dependency_config import *
from syntax_parser_factory import *


class BuildScriptParser:
    def build_dep_graph(self, url):
        pass


class CallDependencyAnalysisHandler(Cmd):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        self.get_methods(opts, cfg)

    def _write_method_info(self, method_freqs, url):
        with open(url, "w", encoding='utf-8') as fp:
            for k, v in method_freqs.items():
                fp.write(k + ', ' + v[0] + ', ' + str(v[1]) + '\n')
        return True

    def _read_method_info(self, method_freqs, url):
        with open(url, "r", encoding='utf-8') as fp:
            while True:
                line = fp.readline()
                if not line:
                    break

                method, clz, freq = line.split(',')
                method = method.strip()
                freq = int(freq)
                method_freqs[method] = [clz, freq]

    def get_methods(self, opts, cfg):
        method_freqs = collections.defaultdict(list)

        if 'loadfile' in opts:
            self._read_method_info(method_freqs, opts['loadfile'])
        else:
            method_freqs = self.get_method_names(opts, cfg)
            if not method_freqs:
                return False, None

        if 'savefile' in opts:
            self._write_method_info(method_freqs, opts['savefile'])
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

                parser = syntax_parsers[file_type]

                code = parser.get_code_without_comment(file)
                if not code:
                    continue

                #print(file)
                calls = parser.find_method_calls(code)

                for method, freq in calls.items():
                    if method in method_freqs:
                        method_freqs[method][1] += 1

        print('>>>>>>>>')
        #print(method_freqs)
        for k, v in method_freqs.items():
            if v[1] == 0:
                print(k, v)
        for k, v in method_freqs.items():
            if v[1] != 0:
                print(k, v)
        print('<<<<<<<<')

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
        method_freqs = collections.defaultdict(list)

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

                    self.find_methods(parser, method_freqs, clz, method_info)

                file_clz_methods[file] = clz_methods

        return method_freqs

    def find_methods(self, parser, method_freqs, clz, method_info):
        for scope, methods in method_info.items():
            if 'public' not in scope:
                continue

            for method in methods:
                #print('methods = ', method[0])
                method_name = parser.get_method_name(method[0])
                if method_name not in method_freqs and method_name != clz \
                    and method_name[1:] != clz:
                    method_freqs[method_name] = [clz, 0]