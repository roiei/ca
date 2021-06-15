for i in range(10):
    print('i = ', i)
    for j in range(10):
        if i == 1:
            print('break')
            break
    print('j = ', j)

print('exited')