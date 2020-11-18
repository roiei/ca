from cmd_interface import *
from util.util_file import *
from syntax_parser_factory import *


class DoxygenVerificationHandler(Cmd):
    def __init__(self):
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

                code = parsers[file_type].get_code(file)
                if not code:
                    continue

                comment_codes = parsers[file_type].get_doxy_comment_method_chunks(code)
                if not comment_codes:
                    continue

                for line, comment_code in comment_codes:
                    res, errs = parsers[file_type].verify_doxycoment_methods(comment_code, 
                        cfg.is_duplicate_param_permitted())
                    if res is not RetType.SUCCESS and res is not RetType.WARN:
                        print(' * file = {} / line = {}'.format(file, line))
                        for err in errs:
                            print(err)
                        print('\n')

        return True
