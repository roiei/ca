
class UtilPrint:
    def __init__(self):
        pass

    def __del__(self):
        pass

    @staticmethod
    def get_line_fmt(item_len, titles):
        fmt = '| ' + ' | '.join(['{:<#item_len#s}']*len(titles)) + ' |'
        fmt = fmt.replace('#item_len#', str(item_len))
        line = fmt.format(*titles)
        dash_line = '+' + '-'*(len(line) - 2) + '+'
        return fmt, line, dash_line

    @staticmethod
    def get_line_fmt_with_custome_lens(item_lens, titles):
        if len(item_lens) != len(titles):
            return None, None, None

        fmt = '| '
        for item_len in item_lens:
            fmt += '{:<' + str(item_len) + 's}' + ' | '

        line = fmt.format(*titles)
        dash_line = '+' + '-'*(len(line) - 3) + '+'
        return fmt, line, dash_line

    @staticmethod
    def print_lines(title, item_len, titles, lines):
        if '' != title:
            print(title)

        fmt, label, dash_line = UtilPrint.get_line_fmt(item_len, titles)
        print(dash_line + '\n' + label + '\n' + dash_line)

        for line in lines:
            print_line = []
            for each_fmt, param in line:
                print_line += each_fmt.format(param),

            arg = list(map(str, print_line))
            print(fmt.format(*arg))

        print(dash_line)

    @staticmethod
    def print_lines_with_custome_lens(title, item_lens, titles, lines):
        if '' != title:
            print(title)

        fmt, label, dash_line = UtilPrint.get_line_fmt_with_custome_lens(item_lens, titles)
        print(dash_line + '\n' + label + '\n' + dash_line)

        for line in lines:
            print_line = []
            for each_fmt, param in line:
                print_line += each_fmt.format(param),

            arg = list(map(str, print_line))
            print(fmt.format(*arg))

        print(dash_line)
