"""Copyright (c) 2010-2012 David Rio Vierra

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""

"""
config.py
Configuration settings and storage.
"""
import os
import logging
import collections
import ConfigParser
from cStringIO import StringIO

import directories

from albow import alert

log = logging.getLogger(__name__)


def configFilePath():
    return directories.configFilePath


def loadConfig():
    class keyDict(collections.MutableMapping):
        def __init__(self, *args, **kwargs):
            self.dict = dict(*args, **kwargs)
            self.keyorder = []

        def keys(self):
            return list(self.keyorder)

        def items(self):
            return list(self.__iteritems__())

        def __iteritems__(self):
            return ((k, self.dict[k]) for k in self.keys())

        def __iter__(self):
            return self.keys().__iter__()

        def __getitem__(self, k):
            return self.dict[k]

        def __setitem__(self, k, v):
            self.dict[k] = v
            if not k in self.keyorder:
                self.keyorder.append(k)

        def __delitem__(self, k):
            del self.dict[k]
            if k in self.keyorder:
                self.keyorder.remove(k)

        def __contains__(self, k):
            return self.dict.__contains__(k)

        def __len__(self):
            return self.dict.__len__()

        def copy(self):
            k = keyDict()
            k.dict = self.dict.copy()
            k.keyorder = list(self.keyorder)
            return k

    config = ConfigParser.RawConfigParser([], keyDict)
    config.readfp(StringIO(configDefaults))
    try:
        config.read(configFilePath())

    except Exception, e:
        log.warn(u"Error while reading configuration file mcedit.ini: {0}".format(e))

    return config


def updateConfig():
    pass


def saveConfig():
    try:
        cf = file(configFilePath(), 'w')
        config.write(cf)
        cf.close()
    except Exception, e:
        try:
            alert(u"Error saving configuration settings to mcedit.ini: {0}".format(e))
        except:
            pass


configDefaults = """
[Keys]
forward = w
back = s
left = a
right = d
up = space
down = left shift
brake = c

rotate = e
roll = r
flip = f
mirror = g
swap = x

pan left = j
pan right = l
pan up = i
pan down = k

reset reach = mouse3
increase reach = scroll up
decrease reach = scroll down

confirm construction = return

open level = o
new level = n
delete blocks = delete

toggle fps counter = 0
toggle renderer = m

quit = q
swap view = f
select all = a
deselect = d 
cut = x
copy = c
paste = v
reload world = r
open = o
load = l
undo = z
save = s
new world = n
close world = w
world info = i
goto panel = g
export selection = e

"""

log.info("Loading config...")
config = loadConfig()
config.observers = {}

# TODO: The '_*' functions below (and prolly addObserver too) should be inside
# Setting class, as they are  not called anywhere else on code besides the
# wrappers there.

def _propertyRef(section, name, dtype, dsubtype, default):
    class PropRef(object):
        def get(self):
            return _getProperty(section, name, dtype, dsubtype, default)

        def set(self, val):
            _setProperty(section, name, val)

    return PropRef()


def _configProperty(section, name, dtype, dsubtype, setter, default):
    assert default is not None

    def _getter(self):
        return _getProperty(section, name, dtype, dsubtype, default)

    def _setter(self, val):
        _setProperty(section, name, val)
        if setter:
            setter(self, val)

    return property(_getter, _setter, None)


def _getProperty(section, name, dtype, dsubtype, default):
    try:
        if dtype is bool:
            return config.getboolean(section, name)
        if dtype in [list, tuple]:
            return dtype(dsubtype(x.strip()) for x in
                         config.get(section, name).translate(None, '[]()').split(','))
        else:
            return dtype(config.get(section, name))
    except:
        if default is None:
            raise
        _setProperty(section, name, default)
        return default


def _setProperty(section, name, value):
    log.debug("Property Change: %15s %30s = %s", section, name, value)
    config.set(section, name, str(value))
    _notifyObservers(section, name, value)


def _notifyObservers(section, name, value):
    observers = config.observers.get((section.lower(), name.lower()), {})
    newObservers = {}
    for targetref, attr in observers:
        target = targetref()
        if target:
            log.debug("Notifying %s", target)
            setattr(target, attr, value)
            callback = observers[targetref, attr]
            if callback:
                callback(value)

            newObservers[targetref, attr] = callback

    config.observers[(section, name)] = newObservers


import weakref


def addObserver(section, name, target, attr, dtype, dsubtype, callback, default):
    """ Register 'target' for changes in the config var named by section and name.
    When the config is changed, calls setattr with target and attr.
    attr may be None; it will be created from the name by lowercasing the first
    word, uppercasing the rest, and removing spaces.
    e.g. "block buffer" becomes "blockBuffer"
    """
    observers = config.observers.setdefault((section.lower(), name.lower()), {})
    if not attr:
        tokens = name.lower().split()
        attr = tokens[0] + "".join(t.title() for t in tokens[1:])
    log.debug("Subscribing %s.%s", target, attr)

    attr = intern(attr)
    targetref = weakref.ref(target)
    observers.setdefault((targetref, attr), callback)

    val = _getProperty(section, name, dtype, dsubtype, default)

    setattr(target, attr, val)
    if callback:
        callback(val)


class Setting(object):
    def __init__(self, section, name, dtype, dsubtype, default):
        self.section = section
        self.name = name
        self.default = default
        self.dtype = dtype
        self.dsubtype = dsubtype

    def __repr__(self):
        attrs = [self.section, self.name, self.dtype, self.default]
        if self.dtype in [list, tuple]:
            attrs.insert(-1, self.dsubtype)
        return "Setting(" + ", ".join(repr(s) for s in attrs) + ")"

    def addObserver(self, target, attr=None, callback=None):
        addObserver(self.section, self.name, target, attr, self.dtype, self.dsubtype, callback, self.default)

    def get(self):
        return _getProperty(self.section, self.name, self.dtype, self.dsubtype, self.default)

    def set(self, val):
        # Perhaps set() should simply assign val without any dtype inference or conversion
        # clients should be responsible for using data types compatible with default value
        if self.dtype in [list, tuple]:
            _setProperty(self.section, self.name, self.dtype(self.dsubtype(x) for x in val))
        else:
            _setProperty(self.section, self.name, self.dtype(val))

    def propertyRef(self):
        return _propertyRef(self.section, self.name, self.dtype, self.dsubtype, self.default)

    def configProperty(self, setter=None):
        return _configProperty(self.section, self.name, self.dtype, self.dsubtype, setter, self.default)

    def __int__(self):
        return int(self.get())

    def __float__(self):
        return float(self.get())

    def __bool__(self):
        return bool(self.get())


class Settings(object):
    Setting = Setting

    def __init__(self, section):
        self.section = section

    def __call__(self, name, default):
        assert default is not None

        section = self.section

        dtype = type(default)
        if dtype in [list, tuple] and len(default) > 0:
            dsubtype = type(default[0])
        else:
            dsubtype = str

        s = self.Setting(section, name, dtype, dsubtype, default)
        if not config.has_section(section):
            config.add_section(section)
        if not config.has_option(section, name):
            s.set(default)

        return s

    def __setattr__(self, attr, val):
        if hasattr(self, attr):
            old = getattr(self, attr)
            if isinstance(old, Setting):
                if isinstance(val, Setting):
                    raise ValueError("Attempting to reassign setting %s with %s" % (old, val))

                log.warn("Setting attr %s via __setattr__ instead of set()!", attr)
                return old.set(val)

        log.debug("Setting {%s => %s}" % (attr, val))
        return object.__setattr__(self, attr, val)
