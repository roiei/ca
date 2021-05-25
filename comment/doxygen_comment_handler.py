import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from cmd_interface import *
from util.util_file import *
from util.util_print import *
from syntax_parser.syntax_parser_factory import *


class DoxygenErrorStats:
    def __init__(self):
        self.num_err = 0
        self.clz_num_err = collections.defaultdict(int)


class DoxygenVerificationHandler(Cmd):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), cfg.get_extensions())
        if not locations:
            return False, None

        parsers = collections.defaultdict(None)
        parsers[FileType.CPP_HEADER] = SyntaxParserFactory.create('hpp')
        if not parsers[FileType.CPP_HEADER]:
            print('ERROR: not supported extension')
            return False, None

        err_stats = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))

        for directory, files in locations.items():
            if not files:
                continue

            dir_errs = collections.defaultdict(lambda: collections.defaultdict(list))
            for file, file_type in files:
                if file_type not in parsers:
                    continue

                whole_code = parsers[file_type].get_code(file)
                if not whole_code:
                    continue

                clz_methods = parsers[file_type].get_methods(whole_code)
                clz_idxs, clz_codes = parsers[file_type].get_each_class_code(whole_code)

                for clz, code in clz_codes.items():
                    comment_codes = parsers[file_type].get_doxy_comment_method_chunks(code, clz)
                    #comment_codes = parsers[file_type].get_doxy_comment_method_chunks_2(code, clz, clz_methods)
                    #print('comment_codes = ', comment_codes)
                    #sys.exit()

                    # for clz_name, method_info in clz_methods.items():
                    #     for attr, methods in method_info.items():
                    #         for method in methods:
                    #             print(method) # (method, param, ret)

                    if not comment_codes:
                        continue

                    pos_line = parsers[file_type].get_line_pos(whole_code)

                    for line, comment_code in comment_codes:
                        res, errs = parsers[file_type].verify_doxycoment_methods(\
                            comment_code, whole_code, clz, pos_line,
                            cfg.is_duplicate_param_permitted())
                        if res is not RetType.SUCCESS and res is not RetType.WARN:
                            dir_errs[file][clz] += errs

                        if errs:
                            err_stats[directory][file][clz] += \
                                max(len(errs) - 1, 0)

            num_err = sum(freq for file, clzs in err_stats[directory].items() \
                for clz, freq in clzs.items())
            if num_err:
                self.print_doxy_analysis_stats(directory, dir_errs, directory)

                for file, clzs in err_stats[directory].items():
                    if not dir_errs[file]:
                        continue

                    print('file: {}'.format(file))
                    for clz, errs in dir_errs[file].items():
                        for line, err in errs:
                            log_msg = err
                            if -1 != line:
                                log_msg = '\t' + '>> ' + log_msg + ' @ ' + str(line)
                            print('\t' + log_msg)
                    print('\n')

        self.print_doxy_analysis_overall_stats(err_stats, 'overall')
        self.print_doxy_analysis_dir_stats(err_stats, 'each')
        return True

    def print_doxy_analysis_overall_stats(self, err_stats, title=''):
        cols = ['# total err', '# dirs', '# classes']
        #cols = ['dir name', 'class name', '# err']
        rows = []
        col_widths = [12, 12, 12]

        tot_num_err = sum([freq for dir, stat in err_stats.items() for file, clzs in stat.items() for clz, freq in clzs.items()])
        tot_num_dir = len(err_stats.keys())
        num_clzs    = sum(len(clzs.keys()) for dir, stat in err_stats.items() for file, clzs in stat.items())

        row = []
        row += ('{:<12d}', tot_num_err),
        row += ('{:<12d}', tot_num_dir),
        row += ('{:<12d}', num_clzs),
        rows += row,

        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)

    def print_doxy_analysis_dir_stats(self, err_stats, title=''):
        cols = ['pkg', '# err classes', '# errs']
        #cols = ['dir name', 'class name', '# err']
        rows = []
        col_widths = [35, 14, 12]

        for dir, files in err_stats.items():
            module_name = dir.split(PlatformInfo.get_delimiter())
            module_name = '-'.join(module_name[-4:])

            num_err = sum(freq for file, clzs in files.items() for clz, freq in clzs.items())
            if not num_err:
                continue

            num_clzs = sum(len(clzs.keys()) for file, clzs in files.items())

            row = []
            row += ('{:<12s}', module_name),
            row += ('{:<12d}', num_clzs),
            row += ('{:<12d}', num_err),
            rows += row,

        rows.sort(key=lambda p: p[2], reverse=True)

        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)

    def print_doxy_analysis_stats(self, module_name, stat, title=''):
        cols = ['file name', 'class name', '# err']
        rows = []
        col_widths = [35, 30, 5]

        for file, clzs in stat.items():
            module_name = file.split(PlatformInfo.get_delimiter())
            module_name = module_name[-1]

            for clz, errs in clzs.items():
                row = []        
                row += ('{:<12s}', module_name),
                row += ('{:<12s}', clz),
                row += ('{:<5d}',  len(errs)),
                rows += row,

        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)
        print()
