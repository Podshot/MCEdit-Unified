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


def exhaust(_iter):
    """Functions named ending in "Iter" return an iterable object that does
    long-running work and yields progress information on each call. exhaust()
    is used to implement the non-Iter equivalents"""
    i = None
    for i in _iter:
        pass
    return i