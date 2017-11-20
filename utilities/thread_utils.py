# thread_utils.py
#
# D.C.-G. 2017
#
# Utilities to deal with threads.
#
import threading

class ThreadRS(threading.Thread):
    # This class comes from: http://stackoverflow.com/questions/6893968/how-to-get-the-return-value-from-a-thread-in-python
    # And may have been tweaked ;)
    """
    This class uses a _return instance member to store the result of the underlying Thread object.
    If 'callbacks' objects are send to the constructor, this '_result' object will be sent to all of them
    at the end of the 'run' and 'join' method. The latest one also returns '_return' object.
    """
    def __init__(self, group=None, target=None, name=None, callbacks=[],
                 args=(), kwargs={}, Verbose=None):
        """
        :callbacks: list: callable objects to send the thread result to.
        For other arguments, see threading.Thread documentation.
        """
        self.target = target
        self.callbacks = callbacks
        threading.Thread.__init__(self, group, target, name, args, kwargs, Verbose)
        self._return = None

    def run(self):
        if self._Thread__target is not None:
            self._return = self._Thread__target(*self._Thread__args,
                                                **self._Thread__kwargs)
            for callback in self.callbacks:
                callback(self._return)

    def join(self):
        try:
            threading.Thread.join(self)
        except Exception as e:
            print e
        for callback in self.callbacks:
            callback(self._return)
        return self._return

    def __repr__(self, *args, **kwargs):
        return '%s::%s' % (ThreadRS, self.target)


def threadable(func):
    def wrapper(*args, **kwargs):
#         instance = None
#         for arg in args:
#             if isinstance(arg, klass):
#                 instance = arg
#                 break
        # ! func MUST ALWAYS be an instance method !
        # And the instace MUST ALWS have a 'targets' function list (or tuple) member.
        instance = args[0]
        with instance.cache_lock:
            t = ThreadRS(target=func, args=args, kwargs=kwargs, callbacks=instance.targets)
            t.daemon = True
            t.start()
            return t
    return wrapper
