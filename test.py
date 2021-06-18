


instr = \
'   a ,  /**< test \n, \
              test */\n \
    b'


# 현재 line에서 /**< 으로 시작하고, */이 없을 시, 
# 다음 라인들에서 */까지 찾아  이를 모두 현재 line으로 합침


items = instr.split('\n')
lines = []
i = 0
print(items)

while i < len(items):
    line = ''
    if not items[i].find('/**<'):
        lines += items[i],
        i += 1
        continue

    while i < len(items) and -1 == items[i].rfind('*/'):
        line += items[i]
        i += 1
    
    if i < len(items):
        line += items[i]

    lines += line,
    i += 1

for line in lines:
    print(line)