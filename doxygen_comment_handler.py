from cmd_interface import *
from util.util_file import *
from util.util_print import *
from syntax_parser_factory import *


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

            dir_errs = collections.defaultdict(list)
            for file, file_type in files:
                if file_type not in parsers:
                    continue

                whole_code = parsers[file_type].get_code(file)
                if not whole_code:
                    continue

                clz_idxs, clz_codes = parsers[file_type].get_each_class_code(whole_code)
                for clz, code in clz_codes.items():
                    comment_codes = parsers[file_type].get_doxy_comment_method_chunks(code, clz)
                    if not comment_codes:
                        continue

                    pos_line = parsers[file_type].get_line_pos(whole_code)

                    for line, comment_code in comment_codes:
                        res, errs = parsers[file_type].verify_doxycoment_methods(\
                            comment_code, whole_code, clz, pos_line,
                            cfg.is_duplicate_param_permitted())
                        if res is not RetType.SUCCESS and res is not RetType.WARN:
                            # print(' * file = {}'.format(file))
                            # for line, err in errs:
                            #     print('>>', err + ' @ ' + str(line))
                            # print('\n')
                            dir_errs[file] += errs

                        if errs:
                            err_stats[directory][file][clz] += \
                                max(len(errs) - 1, 0)

            num_err = sum(freq for file, clzs in err_stats[directory].items() \
                for clz, freq in clzs.items())
            if num_err:
                self.print_doxy_analysis_stats(directory, err_stats[directory], directory)
                for file, errs in dir_errs.items():
                    print(' * file = {}'.format(file))
                    for line, err in errs:
                        print('>>', err + ' @ ' + str(line))
                    print('\n')


        self.print_doxy_analysis_overall_stats(err_stats, 'overall')
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

    def print_doxy_analysis_stats(self, dir, stat, title=''):
        cols = ['file name', 'class name', '# err']
        rows = []
        col_widths = [35, 30, 5]

        for file, clzs in stat.items():
            pkg_name = file.split(PlatformInfo.get_delimiter())
            pkg_name = pkg_name[-1]

            for clz, err in clzs.items():
                row = []        
                row += ('{:<12s}', pkg_name),
                row += ('{:<12s}', clz),
                row += ('{:<5d}', err),
                rows += row,

        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)
        print()
