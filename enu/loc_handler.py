from cmd_interface import *
from util.util_file import *
from util.util_print import *
from syntax_parser.syntax_parser_factory import *


class FileLoCInfo:
    def __init__(self):
        self.loc = 0
        self.loc_wo_comment = 0


class LoCStat:
    def __init__(self):
        self.tot_loc = 0
        self.tot_loc_wo_comment = 0
        self.loc_info = collections.defaultdict(lambda: collections.defaultdict(lambda: FileLoCInfo()))


class LoCHandler(Cmd):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def execute(self, opts, cfg):
        depth = int(opts['depth']) if 'depth' in opts else None
        locations = UtilFile.get_dirs_files(opts["path"], \
            cfg.get_recursive(), depth, ['cpp'])
        if not locations:
            return False, None

        parsers = SyntaxParserFactory.get_parsers(['cpp'])
        loc_stat = LoCStat()

        for directory, files in locations.items():
            if not files:
                continue

            for file, file_type in files:
                ext = UtilFile.get_extension(file)
                if ext not in parsers:
                    continue

                parser = parsers[ext]

                code = parser.get_code_lines(file)
                loc = parser.get_loc(code)
                loc_stat.loc_info[directory][file].loc = loc
                loc_stat.tot_loc += loc

                code = parser.remove_comment(code)
                loc = parser.get_loc(code)
                loc_stat.loc_info[directory][file].loc_wo_comment = loc
                loc_stat.tot_loc_wo_comment += loc

        self.print_loc_stats(loc_stat)
        return True

    def print_loc_stats(self, loc_stat):
        cols = ['file name', 'class name', '# err']
        rows = []
        col_widths = [60, 10, 10]

        for d, files in loc_stat.loc_info.items():
            print('directory = ', d)
            rows = []

            for file, file_loc in files.items():
                row = []
                row += ('{:<25s}', file),
                row += ('{:<12d}', file_loc.loc),
                row += ('{:<12d}', file_loc.loc_wo_comment),
                rows += row,

            UtilPrint.print_lines_with_custome_lens(\
                ' * complexity of dir = {}'.format(d), 
                col_widths, cols, rows)
            print()

        print(' tot loc = ', loc_stat.tot_loc)
        print(' tot loc wo comment = ', loc_stat.tot_loc_wo_comment)
