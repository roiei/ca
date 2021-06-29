import collections


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
    def get_line_delimeter(item_lens):
        line_delimeter = '+'
        for item_len in item_lens:
            line_delimeter += '-'*(item_len + 2) + '+'

        return line_delimeter

    @staticmethod
    def print_lines_with_custome_lens(title, item_lens, titles, lines):
        if '' != title:
            print(title)

        fmt, label, dash_line = UtilPrint.get_line_fmt_with_custome_lens(item_lens, titles)
        print(dash_line + '\n' + label + '\n' + dash_line)
        num_cols = len(titles)
        line_delimeter = UtilPrint.get_line_delimeter(item_lens)

        for line in lines:
            cols = collections.defaultdict(lambda: collections.defaultdict(str))
            mx_lines = 0

            for idx, val in enumerate(zip(item_lens, line)):
                item_len, item_value = val
                each_fmt, param = item_value
                if type(param) is list:
                    item = each_fmt.format(*param)
                else:
                    item = each_fmt.format(param)
                n = len(item)

                num_lines = n//item_len
                if n%item_len:
                    num_lines += 1

                #print(mx_lines, num_lines, n, item_len)
                mx_lines = max(mx_lines, num_lines)

                line_cnt = 0
                for i in range(0, n, item_len):
                    cols[idx][line_cnt] = item[i:i + item_len]
                    line_cnt += 1

            for l in range(mx_lines):
                print_line = []
                for c in range(num_cols):
                    print_line += cols[c][l],

                arg = list(map(str, print_line))
                print(fmt.format(*arg))

            print(line_delimeter)
