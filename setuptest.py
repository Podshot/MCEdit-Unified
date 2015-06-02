try:
    from pymclevel import _nbt
    print "Succesfully imported _nbt"
except ImportError as err:
    print "An error occurred while importing _nbt.c ({0})".format(err)
