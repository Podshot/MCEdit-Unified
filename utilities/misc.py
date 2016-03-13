
# Taken from: http://stackoverflow.com/a/7346105
class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)
    
    
def deprecated(func):
    '''
    Function decorator to denote that a function shouldn't be used
    
    :param func: The function that is deprecated
    '''
    def new_func(*args, **kwargs):
        #logger.warn("Function \""+str(func.__name__)+"\" is deprecated and should not be used")
        return func(*args, **kwargs)   
    new_func.__name__ = func.__name__
    if func.__doc__ is not None:
        new_func.__doc__ = '''*Deprecated*\n%s'''%func.__doc__
    else:
        new_func.__doc__ = '''*Deprecated*'''
    new_func.__dict__.update(func.__dict__)
    return new_func