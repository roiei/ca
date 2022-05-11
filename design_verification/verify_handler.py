from cmd_interface import *
from util import UtilFile, FileType
from syntax_parser import SyntaxParserFactory
from design_verification.verify import FileResult, Report
import collections
import typing


def print_missing_rules(res_dirs, num_missings, cfg):
    if not res_dirs:
        print(num_missings)
        return

    if cfg.get_jsonoutput_on():
        ret = JSonSerializer.convert_to_dict(res_dirs)
        JSonSerializer.serialize_to_json(ret)

    print('MISS {}:'.format(num_missings))

    for d, files in res_dirs.items():
        print('directory = {}'.format(d))
        for file in files:
            if not file.get_missing_num():
                continue

            print('\tfile = {}:'.format(file.get_name()))
            for clz, missing_rules in file.clzs.items():
                print('\t\tclass = {} / {} : missing num = {}'.format(clz, file.get_clz_type(clz), len(missing_rules)))
                print('\t\tmisisng rules = ', missing_rules)


def print_rule_miss_result_table(reports):
    dir_item_len = 25
    item_len = 12
    titles = ['directory', 'files', 'vio. files', 'classes', \
              'vio. classes', 'vio. count', 'rank']
    fmt = '| {:<#dir_item_len#s} | {:<#item_len#s} | {:<#item_len#s}' + \
         ' | {:<#item_len#s} | {:<#item_len#s} | {:<#item_len#s} | {:<#item_len#s} |'
    fmt = fmt.replace('#dir_item_len#', str(dir_item_len))
    fmt = fmt.replace('#item_len#', str(item_len))
    line = fmt.format(*titles)
    dash_line = '+' + '-'*(len(line) - 2) + '+'

    print(dash_line)
    print(line)
    print(dash_line)

    rank = collections.defaultdict(int)
    for report in reports:
        rank[report.directory] = report.violate_cnt
    rank = sorted(rank.items(), reverse=True, key=lambda p: p[1])
    ranking = collections.defaultdict(int)
    rank_cnt = 1

    for dirname, violate_cnt in rank:
        ranking[dirname] = (rank_cnt, violate_cnt)
        rank_cnt += 1

    for report in reports:
        path = report.directory
        if len(path) > dir_item_len:
            path = path[len(path) - dir_item_len + 2:]
            path = '..' + path

        rank_str = '.'
        if report.violate_cnt:
            rank_str, violate_cnt = ranking[report.directory]

        arg = map(str, [path, report.files, report.violate_files, report.num_classes, \
            report.violate_classes, report.violate_cnt, rank_str])
        line = fmt.format(*arg)

        print(line)

    print(dash_line)


def print_rule_miss_result(reports, res_dirs, cfg):
    report_detail = cfg.isDetailReportOn()
    report_table = cfg.isAnalysisReportOn()

    num_missings = sum(report.violate_cnt for report in reports)
    if num_missings:
        if report_detail:
            print_missing_rules(res_dirs, num_missings, cfg)

        if report_table:
            print_rule_miss_result_table(reports)

    print(num_missings)


class CPPVerificationHandler(Cmd):
    def __init__(self):
        pass

    def execute(self, opts: typing.Dict, cfg) -> bool:
        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), cfg.get_recursive_depth(), cfg.get_extensions())
        if not locations:
            return False

        syntax_parsers = collections.defaultdict(None)
        syntax_parsers[FileType.CPP_HEADER] = SyntaxParserFactory.create('hpp')
        if not syntax_parsers[FileType.CPP_HEADER]:
            print('ERROR: not supported extension')
            return False

        coverage = opts['cover']
        syntax_parsers[FileType.CPP_HEADER].set_suffix_filter(cfg.get_suffix_filter_names())
        syntax_parsers[FileType.CPP_HEADER].set_filter_keyword(cfg.get_filter_keyword())

        res_dirs = collections.defaultdict(list)
        reports = []
        violate_cnt = 0

        for directory, files in locations.items():
            if not files:            
                continue

            report = Report(directory)
            report.files = len(files)

            for file, file_type in files:
                if file_type not in syntax_parsers:
                    continue

                parser = syntax_parsers[file_type]

                whole_code = parser.get_code_without_comment(file)
                if not whole_code:
                    continue

                missing_rules = parser.check_rules(whole_code, report, cfg, coverage)
                if not missing_rules:
                    continue

                file_res = FileResult(file)

                for clz, info in missing_rules.items():
                    clz_name, clz_type = clz
                    file_res.push_missing_infos(clz_name, clz_type, info)
                    report.violate_classes += 1
                    report.violate_cnt += len(info)

                if file_res.get_missing_num():
                    res_dirs[directory] += file_res,

                report.violate_files += 1

            reports += report,
            violate_cnt += report.violate_cnt
        
        print_rule_miss_result(reports, res_dirs, cfg)
        return 0 == violate_cnt
