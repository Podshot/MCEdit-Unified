'''
This python file is not accual code, it is just a layout of how I will
document MCEdit.
Documentation tags:
@param ____: A parameter to a function. '____' is the parameter name and
what the parameter should be (Like an int, string, level object, or albow widget)
@return: What the function returns (Like a boolean, string, or exception
@raises ____: What error the function could throw
@what-it-does: What the function accomplishes
'''

'''
@param arg: Argument to print to console
@what-it-does: Prints the argument to console 
'''


def paramFunction(arg):
    print "Arg: " + str(arg)


'''
@raises Exception: This function should always raise a generic Exception
@what-it-does: Raises a generic Exception
'''


def throwsError():
    raise Exception()


'''
@return: Returns a boolean with the value of True
@what-it-does: Returns True
'''


def returnFunction():
    return True
