


class CommonCppParser:
    def __init__(self):
        pass

    def find_line(self, pos_line, pos):
        l = 0
        end = r = len(pos_line)

        while l <= r:
            m = (l + r)//2
            if pos_line[max(0, m - 1)][0] <= pos <= pos_line[min(end, m)][0]:
                return pos_line[m][1]

            if pos_line[m][0] < pos:
                l = m + 1
            else:
                r = m - 1

        return -1

    def find_pos(self, pos_line, line, offset=0) -> int:
        l = 0
        end = r = len(pos_line) - 1

        #print(pos_line)

        while l <= r:
            m = (l + r)//2
            #print(m)

            if pos_line[m][1] == line:
                return pos_line[max(m + offset, 0)][0]

            if pos_line[m][1] < line:
                l = m + 1
            else:
                r = m - 1

        return pos_line[min(l, end)][0]

    def get_line_pos(self, code):
        n = len(code)
        i = 0
        line = 1
        pos_line = [(0, 0)]

        while i < n:
            if code[i] == '\n':
                pos_line += (i, line),
                line += 1
            i += 1

        pos_line += (i, line),
        return pos_line
