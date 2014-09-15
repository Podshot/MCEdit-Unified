import plyvel
import collections
import itertools
import logging
import struct
import zlib
from cStringIO import StringIO
import numpy
from numpy import array, zeros, fromstring

db = plyvel.DB('/tmp/testdb/', create_if_missing=True)