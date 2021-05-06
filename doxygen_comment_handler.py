from cmd_interface import *
from util.util_file import *
from syntax_parser_factory import *


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

        for directory, files in locations.items():
            if not files:
                continue

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
                            #print(' * file = {} / line = {}'.format(file, line))
                            print(' * file = {}'.format(file))
                            for line, err in errs:
                                print('>>', err + ' @ ' + str(line))
                            print('\n')

        return True
