# full featured function
def func(a, b, c=3, d=4, *args, **kwargs):
    print a
    print b
    print c
    print d
    print len(args)
    print len(kwargs)
    return a+b+c+d

print '>>> func(1,2)'
print func(1,2)
print '>>> func(5,6)'
print func(5, 6)
print '>>> func(10, 20, 30, 40)'
print func(10, 20, 30, 40)
print '>>> func(10, 20, 30, 40, 50, 60, 70)'
print func(10, 20, 30, 40, 50, 60, 70)
print '>>> func(11, 22, c=33, d=44)'
print func(11, 22, c=33, d=44)
print '>>> func(11, 22, e=55, f=66)'
print func(11, 22, e=55, f=66)
