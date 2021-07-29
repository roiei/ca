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
import pandas as pd
import seaborn as sbn


class DoxygenErrorStats:
    def __init__(self):
        self.tot_method = 0
        self.err_method = 0
        self.num_items = 0
        self.num_errs = 0
        self.num_module_err = collections.defaultdict(int)
        self.num_module_item = collections.defaultdict(int)


class DoxygenVerificationHandler(Cmd):
    def __init__(self):
        self.rules = {
            'enum': self.__check_enum,
            'method': self.__check_method
        }

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), cfg.get_recursive_depth(), cfg.get_extensions())
        if not locations:
            return False, None

        enum_rules = cfg.get_enum_rules()
        parsers = collections.defaultdict(None)
        parsers[FileType.CPP_HEADER] = SyntaxParserFactory.create('hpp')
        if not parsers[FileType.CPP_HEADER]:
            print('ERROR: not supported extension')
            return False, None

        err_stats = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
        stat = DoxygenErrorStats()
        tot_err = 0

        for directory, files in locations.items():
            if not files:
                continue

            dir_errs = collections.defaultdict(lambda: collections.defaultdict(list))
            for file, file_type in files:
                if file_type not in parsers:
                    continue

                parser = parsers[file_type]

                whole_code = parser.get_code(file)
                if not whole_code:
                    continue

                pos_line = parser.get_line_pos(whole_code)

                for rule in enum_rules:
                    acc, rule = rule.split('::')
                    if acc != 'must':
                        continue

                    if rule not in self.rules:
                        print('Not supported rule.')
                        continue

                    self.rules[rule](parsers[file_type], directory, file, whole_code, \
                        pos_line, dir_errs, stat, err_stats, cfg)

            num_err = sum(freq for file, clzs in err_stats[directory].items() \
                for clz, freq in clzs.items())

            if num_err:
                self.print_doxy_analysis_stats(directory, dir_errs, directory, num_err)
                self.print_detail_err_info(directory, err_stats, dir_errs)
            tot_err += num_err

        if tot_err:
            self.print_doxy_analysis_dir_stats(err_stats, stat, 'each')
            self.print_doxy_analysis_overall_stats(err_stats, stat, 'overall')

            if 'graph' in opts and opts['graph']:
                self.draw_err_ratio_distplot(err_stats, stat)
                # self.draw_bar_chart(err_stats, stat)
                self.draw_err_pie_charts(err_stats, stat)
        
        print(tot_err)
        return 0 == tot_err
    
    def __check_enum(self, parser, directory, file, whole_code, pos_line, dir_errs, \
            stat, err_stats, cfg):
        non_clz_code = parser.get_non_class_code(whole_code)
        enum_codes = parser.get_enum_codes(non_clz_code, whole_code, pos_line)

        comment_codes = parser.get_doxy_comment_enum_chunks(non_clz_code)
        commented_enum = set()
        for line, comment_code, name in comment_codes:
            commented_enum.add(name)
        
        num_not_doc = 0
        for name, code, line in enum_codes:
            if name not in commented_enum:
                dir_errs[file][''] += (line, 'enum: {} is not documented'.format(name)),
                err_stats[directory][file][''] += 1
                num_not_doc += 1
            stat.num_items += 1
            stat.num_module_item[directory] += 1

        stat.num_errs += num_not_doc
        stat.num_module_err[directory] += num_not_doc
        
        for name, code, line in enum_codes:
            num_lines, errs = parser.verify_doxycomment_enum(\
                code, line, whole_code, pos_line, cfg)
            dir_errs[file][''] += errs
            err_stats[directory][file][''] += len(errs)

            num_item = max(num_lines, len(errs))
            stat.num_items += num_item
            stat.num_module_item[directory] += num_item
            stat.num_errs += len(errs)
            stat.num_module_err[directory] += len(errs)
    
    def __check_method(self, parser, directory, file, whole_code, pos_line, dir_errs, \
            stat, err_stats, cfg):
        clz_idxs, clz_codes = parser.get_each_class_code(whole_code)

        for clz, code in clz_codes.items():
            dir_errs[file][clz] = dir_errs[file][clz]
            comment_codes = parser.get_doxy_comment_method_chunks(code.code, clz)
            all_methods = set(parser.get_methods_in_class(clz, code.code, 
                whole_code, pos_line, cfg.is_deleted_method_ignorable()))

            commented_methods = set()
            for line, comment_code, method_name in comment_codes:
                commented_methods.add(parser.remove_comment_in_method(comment_code))
            
            # print('commented methods')
            # print(commented_methods)
            # print('all_method')
            # for m in all_methods:
            #     print(m)

            num_no_commented = 0
            for method, method_code, line, num_sig in all_methods:
                stat.num_items += num_sig
                stat.num_module_item[directory] += num_sig
                if method_code not in commented_methods:
                    dir_errs[file][clz] += (line, 'method: {} is not documented'.format(method)),
                    num_no_commented += 1

            stat.num_module_item[directory] += len(all_methods)
            stat.tot_method += len(all_methods)
            stat.err_method += num_no_commented
            stat.num_errs += num_no_commented
            stat.num_module_err[directory] += num_no_commented

            err_stats[directory][file][clz] += num_no_commented

            if not comment_codes:
                continue

            for line, comment_code, method_name in comment_codes:
                res, errs = parser.verify_doxycoment_methods(\
                    comment_code, whole_code, clz, pos_line,
                    cfg.is_duplicate_param_permitted())

                if res is not RetType.SUCCESS and res is not RetType.WARN:
                    errs.sort(key=lambda p: p[0])
                    dir_errs[file][clz] += errs

                if errs:
                    err_stats[directory][file][clz] += \
                        max(len(errs) - 1, 0)
                    stat.err_method += 1
                    stat.num_module_item[directory] += max(1, len(errs) - 1)
                    stat.num_errs += max(len(errs) - 1, 0)
                    stat.num_module_err[directory] += max(len(errs) - 1, 0)

    def print_detail_err_info(self, directory, err_stats, dir_errs):
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

    def print_doxy_analysis_overall_stats(self, err_stats, stat, title=''):
        cols = ['# dirs', '# class', '# items', '# err', 'err %', \
            '# method', '# err method', \
            'err method %']
        #cols = ['dir name', 'class name', '# err']
        rows = []
        col_widths = [6, 9, 7, 5, 6, 8, 12, 12]
        tot_num_dir = len(err_stats.keys())
        num_clzs    = sum(len(clzs.keys()) for dir, stat in err_stats.items() for file, clzs in stat.items())
        if not stat.num_items:
            return

        row = []
        row += ('{:<6d}', tot_num_dir),
        row += ('{:<8d}', num_clzs),
        row += ('{:<7d}', stat.num_items),
        row += ('{:<5d}', stat.num_errs),
        row += ('{:<0.2f}%', (stat.num_errs/stat.num_items if stat.num_items > 0 else 0)*100),
        row += ('{:<8d}', stat.tot_method),
        row += ('{:<12d}', stat.err_method),
        row += ('{:<0.2f}%', (stat.err_method/stat.tot_method if stat.tot_method > 0 else 0)*100),
        rows += row,

        UtilPrint.print_lines_with_custome_lens(' * stats: {}'.format(title), 
            col_widths, cols, rows)

    def print_doxy_analysis_dir_stats(self, err_stats, stat, title=''):
        cols = ['pkg', '# err classes', '# errs (%)', '# items']
        #cols = ['dir name', 'class name', '# err']
        rows = []
        col_widths = [35, 14, 16, 12]

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
            row += ('{:<5d} ({:<6.2f} %)', [stat.num_module_err[dir], \
                stat.num_module_err[dir]/stat.num_module_item[dir]*100 \
                if stat.num_module_item[dir] else 0]),
            row += ('{:<12d}', stat.num_module_item[dir]),
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
    
    def draw_err_ratio_distplot(self, err_stats, stat):
        values = []
        for dir, files in err_stats.items():
            values += stat.num_module_err[dir]/stat.num_module_item[dir]*100 \
                if stat.num_module_item[dir] else 0,

        data = pd.DataFrame(values, columns=['Mu'])
        plt.figure()
        dist_plot = sbn.distplot(data['Mu'], label='mu')
        plt.axvline(data['Mu'].median(), color='blue', ls=':', \
            label='median: ' + '{:.2f} %'.format(data['Mu'].median()))
        plt.axvline(data['Mu'].mean(), color='red', ls=':', \
            label='mean: ' + '{:.2f} %'.format(data['Mu'].mean()))
        #plt.legend(loc=2)
        #plt.legend(('envelop', 'median', 'mean', 'err %'))
        plt.legend()
        plt.show()

    def draw_err_pie_charts(self, err_stats, stat, cut_off=None):
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

        values = list(zip(labels, ratios))
        values.sort(key=lambda p: p[1], reverse=True)
        print(len(values))
        if cut_off:
            values = values[:cut_off]

        explode = len(values)*[0.05]

        color_tbl = ['#ff9999', '#ffc000', '#8fd9b6', \
            '#d395d0', 'blue', 'red', 'magenta', 'yellow', 'cyan', \
            'purple', 'pink', 'olive', 'green', 'blue', 'brown']
        colors = [random.choice(color_tbl) for i in range(len(labels))]

        labels, ratios = zip(*values)
        
        plt.pie(ratios, labels=labels, autopct='%.1f%%', \
            startangle=260, counterclock=False, \
            explode=explode, shadow=True, colors=colors)
        plt.show()




