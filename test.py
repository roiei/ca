def get_method_end_pos(code):
    i = 0
    n = len(code)

    print('code = ', code)

    while i < n:
        if code[i] == '(':
            break
        i += 1

    if i == n:
        return None

    opn_cnt = 1
    i += 1

    while i < n and opn_cnt:
        if code[i] == '(':
            opn_cnt += 1
        elif code[i] == ')':
            opn_cnt -= 1
        i += 1

    print('method name only = ', code[:i])
    return i

get_method_end_pos('HAudioSettingSDV getSDV() const {\
        __TRACE_CALL__()')