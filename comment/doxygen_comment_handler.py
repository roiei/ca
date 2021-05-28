import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from cmd_interface import *
from util.util_file import *
from util.util_print import *
from syntax_parser.syntax_parser_factory import *
import matplotlib.pyplot as plt
import matplotlib
import random


class DoxygenErrorStats:
    def __init__(self):
        self.tot_method = 0
        self.err_method = 0
        self.num_items = 0
        self.num_errs = 0


class DoxygenVerificationHandler(Cmd):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), cfg.get_recursive_depth(), cfg.get_extensions())
        if not locations:
            return False, None

        parsers = collections.defaultdict(None)
        parsers[FileType.CPP_HEADER] = SyntaxParserFactory.create('hpp')
        if not parsers[FileType.CPP_HEADER]:
            print('ERROR: not supported extension')
            return False, None

        err_stats = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
        stat = DoxygenErrorStats()

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

                clz_idxs, clz_codes = parsers[file_type].get_each_class_code(whole_code)
                pos_line = parsers[file_type].get_line_pos(whole_code)

                for clz, code in clz_codes.items():
                    dir_errs[file][clz] = dir_errs[file][clz]
                    comment_codes = parsers[file_type].get_doxy_comment_method_chunks(code, clz)
                    all_methods = set(parsers[file_type].get_methods_in_class(clz, code, whole_code, pos_line))

                    commented_methods = set()
                    for line, comment_code, method_name in comment_codes:
                        commented_methods.add(parsers[file_type].remove_comment(comment_code))

                    num_no_commented = 0
                    for method, method_code, line, num_sig in all_methods:
                        stat.num_items += num_sig
                        if method_code not in commented_methods:
                            dir_errs[file][clz] += (line, 'method: {} is not documented'.format(method)),
                            num_no_commented += 1

                    stat.tot_method += len(all_methods)
                    stat.err_method += num_no_commented
                    stat.num_errs += num_no_commented
                    err_stats[directory][file][clz] += num_no_commented

                    if not comment_codes:
                        continue

                    for line, comment_code, method_name in comment_codes:
                        res, errs = parsers[file_type].verify_doxycoment_methods(\
                            comment_code, whole_code, clz, pos_line,
                            cfg.is_duplicate_param_permitted())

                        errs.sort(key=lambda p: p[0])

                        if res is not RetType.SUCCESS and res is not RetType.WARN:
                            dir_errs[file][clz] += errs

                        if errs:                            
                            err_stats[directory][file][clz] += \
                                max(len(errs) - 1, 0)
                            stat.err_method += 1
                            stat.num_errs += max(len(errs) - 1, 0)

            num_err = sum(freq for file, clzs in err_stats[directory].items() \
                for clz, freq in clzs.items())

            self.print_doxy_analysis_stats(directory, dir_errs, directory, num_err)
            if num_err:
                for file, clzs in err_stats[directory].items():
                    if not dir_errs[file]:
                        continue

                    num_err_in_file = sum([len(errs) for clz, errs in dir_errs[file].items()])
                    if not num_err_in_file:
                        continue

                    print('file: {}'.format(file))
                    for clz, errs in dir_errs[file].items():
                        if not errs:
                            continue
                        print('\tclass: ', clz)
                        for line, err in errs:
                            log_msg = err
                            if -1 != line:
                                log_msg = '\t' + '>> ' + log_msg + ' @ ' + str(line)

                            if err.startswith('method:'):
                                line += 1
                            else:
                                log_msg = '\t' + log_msg
                                
                            print('\t' + log_msg)
                    print('\n')

        self.print_doxy_analysis_dir_stats(err_stats, 'each')
        self.print_doxy_analysis_overall_stats(err_stats, stat, 'overall')
        if 'graph' in opts and opts['graph']:
            self.draw_bar_chart(err_stats, stat)
            self.draw_err_pie_charts(err_stats, stat)
        return True

    def print_doxy_analysis_overall_stats(self, err_stats, stat, title=''):
        cols = ['# tot err', '# dirs', '# class', \
            '# method', '# err method', '# err', \
            'err method %', '# items', 'err %']
        #cols = ['dir name', 'class name', '# err']
        rows = []
        col_widths = [11, 6, 9, 8, 12, 5, 12, 7, 5]

        tot_num_err = sum([freq for dir, stat in err_stats.items() for file, clzs in stat.items() for clz, freq in clzs.items()])
        tot_num_dir = len(err_stats.keys())
        num_clzs    = sum(len(clzs.keys()) for dir, stat in err_stats.items() for file, clzs in stat.items())

        row = []
        row += ('{:<9d}', tot_num_err),
        row += ('{:<6d}', tot_num_dir),
        row += ('{:<8d}', num_clzs),
        row += ('{:<8d}', stat.tot_method),
        row += ('{:<12d}', stat.err_method),
        row += ('{:<5d}', stat.num_errs),
        row += ('{:<0.2f}%', (stat.err_method/stat.tot_method)*100),
        row += ('{:<5d}', stat.num_items),
        row += ('{:<0.2f}%', (stat.num_errs/stat.num_items)*100),
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

    def print_doxy_analysis_stats(self, module_name, stat, title='', num_err=0):
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

        UtilPrint.print_lines_with_custome_lens(' * stats: {} : err={}'.format(title, num_err), 
            col_widths, cols, rows)
        print()

    def draw_bar_chart(self, err_stats, stat):
        x_labels = ['# items', '# err']
        values = [stat.num_items, stat.num_errs]
        colors = ['black','red']
         
        plt.figure(figsize=(3, 3))
        xtick_label_position = list(range(len(x_labels)))
        plt.xticks(xtick_label_position, x_labels)
         
        plt.bar(xtick_label_position, values, color=colors)
         
        plt.title('Doxygen err stat',fontsize=20)
        plt.xlabel('num items')
        plt.ylabel('item types')
        plt.show()

    def draw_err_pie_charts(self, err_stats, stat):
        font = {'family': 'serif', 'weight': 'normal', 'size': 7}
        matplotlib.rc('font', **font)

        ratios = []
        labels = []
        for dir, files in err_stats.items():
            module_name = dir.split(PlatformInfo.get_delimiter())
            module_name = '-'.join(module_name[-4:])
            num_err = sum(freq for file, clzs in files.items() for clz, freq in clzs.items())

            labels += module_name,
            ratios += (num_err/stat.num_errs)*100,

        explode = len(labels)*[0.05]

        color_tbl = ['#ff9999', '#ffc000', '#8fd9b6', \
            '#d395d0', 'blue', 'red', 'magenta', 'yellow', 'cyan', \
            'purple', 'pink', 'olive', 'green', 'blue', 'brown']
        colors = [random.choice(color_tbl) for i in range(len(labels))]
        
        plt.pie(ratios, labels=labels, autopct='%.1f%%', \
            startangle=260, counterclock=False, \
            explode=explode, shadow=True, colors=colors)
        plt.show()




