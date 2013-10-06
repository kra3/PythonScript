try:
    # any thing before the exception is executed
    raise "Object"
    print 'FAIL'
except:
    print 'OK'
