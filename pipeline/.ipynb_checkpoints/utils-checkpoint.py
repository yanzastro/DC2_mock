def list2string(alist, prefix='', suffix=''):
    st = ''
    for l in alist:
        st += ' ' + prefix + str(l) + suffix
    return st