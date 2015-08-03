'''
Created on Jul 22, 2011

@author: Rio
'''

from contextlib import contextmanager
from logging import getLogger

log = getLogger(__name__)


@contextmanager
def notclosing(f):
    yield f


class PlayerNotFound(Exception):
    pass


class ChunkNotPresent(Exception):
    pass


class RegionMalformed(Exception):
    pass


class ChunkMalformed(ChunkNotPresent):
    pass


class ChunkConcurrentException(Exception):
    """Exception that is raised when a chunk is being modified while
    saving is taking place"""
    pass


class ChunkAccessDenied(ChunkNotPresent):
    """Exception that is raised when a chunk is trying to be read from disk while
    saving is taking place"""
    pass


def exhaust(_iter):
    """Functions named ending in "Iter" return an iterable object that does
    long-running work and yields progress information on each call. exhaust()
    is used to implement the non-Iter equivalents"""
    i = None
    for i in _iter:
        pass
    return i