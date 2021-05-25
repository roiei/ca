from cmd_interface import *
from util.util_file import *
from syntax_parser.syntax_parser_factory import *
from design_verification.verify import *


def print_func_info(func_info, depth_column):
    for func, params, ret in func_info:
        res = 'void' if not ret else ret
        print(depth_column*2 + ' +- ', func)
        if ret:
            print(depth_column*2 + ' |     -> ' + res)

        if not params:
            continue

        print(depth_column*3 + ' +-  params : ', ":", "// {}".format(len(params)))
        for param in params:
            print(depth_column*4 + '  +- ', param)


def print_enum_result(file_clz_methods):
    depth_column = ' |    '

    for file, clzs in file_clz_methods.items():
        print(file)
        for clz, acc_mods in clzs.items():
            print(' +- ', clz)
            for acc_mod, methods in acc_mods.items():
                print(depth_column*1 + ' +- {:<10}'.format(acc_mod), ":", "// {}".format(len(methods)))
                print_func_info(methods, depth_column)


class EnumerateCPPMethodHandler(Cmd):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), cfg.get_extensions())
        if not locations:
            return False, None

        syntax_parsers = collections.defaultdict(None)
        syntax_parsers[FileType.CPP_HEADER] = SyntaxParserFactory.create('hpp')
        if not syntax_parsers[FileType.CPP_HEADER]:
            print('ERROR: not supported extension')
            return False, None
        
        file_clz_methods = collections.defaultdict(None)

        for directory, files in locations.items():
            if not files:
                continue

            for file, file_type in files:
                if file_type not in syntax_parsers:
                    continue

                whole_code = syntax_parsers[file_type].get_code_without_comment(file)
                if not whole_code:
                    continue

                clz_methods = syntax_parsers[file_type].get_methods(whole_code)
                if not clz_methods:
                    continue

                file_clz_methods[file] = clz_methods

        print_enum_result(file_clz_methods)
        return True, None
