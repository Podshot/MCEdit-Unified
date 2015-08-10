# -*- coding: utf-8 -*-
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
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

------------------------------------------------------------------------------------------------------------------------

FOR USERS:
To use this file, you should never interact with the classes directly. The interface is provided
at the methods below. They wil automatically take care of all loading and caching stuff.

FOR EDITORS:
What is going on in this file:

Little bit of history:
This file used to take about 1.4 seconds to import. One of the main goals was to bring this down to the bare minimum.
Right now, it takes about 0.5 seconds to import instead.

In the past, all directories got looked up on import. Right now, importing the file does almost no work.
There's 2 classes, MinecraftDirectories and MCEditDirectories.
MinecraftDirectories contains all "read-only" directories. Those are (usually) created by Minecraft.
They get looked up once needed the first time, and cached for the lifetime of the module.

MCEditDirectories contains all directories and files created by mcedit, such as the mcedit.ini file,
and the Filters/Schematics folder. On import, the class doesn't exist.
To get access to all other methods, setupMCEditDirectories() has to be called. This will look up all
of mcedit's user files, create an MCEditDirectories instance and create any missing files or folders.
After that, the class is fully functional.

There's also some loose methods that are essential to the behavior of the program itself
and can always be used, such as getDataDir()
"""

import logging
log = logging.getLogger(__name__)

import sys
import os
import json
import glob
import shutil


def _unicodify(text):
    """Converts any basestring to a utf-8 encoded string.
    :param text: String to convert
    :type text: basestring
    :return: Converted string
    :rtype: unicode
    """
    if type(text) is not unicode:
        return unicode(text, 'utf-8')
    return text


def _move_displace(src, dst):
    dstFolder = os.path.basename(os.path.dirname(dst))
    if not os.path.exists(dst):

        print "Moving {0} to {1}".format(os.path.basename(src), dstFolder)
        shutil.move(src, dst)
    else:
        olddst = dst + ".old"
        i = 0
        while os.path.exists(olddst):
            olddst = dst + ".old" + str(i)
            i += 1

        print "{0} already found in {1}! Renamed it to {2}.".format(os.path.basename(src), dstFolder, dst)
        os.rename(dst, olddst)
        shutil.move(src, dst)
    return True


class _MinecraftDirectories(object):

    _dataDirectory = u""
    _minecraftSaveFileDirectory = u""
    _minecraftLauncherDirectory = u""
    _minecraftProfileJson = None

    @property
    def minecraftSaveFileDirectory(self):
        if self._minecraftSaveFileDirectory == u"":
            self._minecraftSaveFileDirectory = self._getSaveFileDirectory()
        return self._minecraftSaveFileDirectory

    @property
    def minecraftLauncherDirectory(self):
        if self._minecraftLauncherDirectory == u"":
            self._minecraftLauncherDirectory = self._getMinecraftLauncherDirectory()
        return self._minecraftLauncherDirectory

    @property
    def selectedProfile(self):
        j = self.minecraftProfileJSON
        return None if j is None else j["selectedProfile"]

    @property
    def minecraftProfileJSON(self):
        if self._minecraftProfileJson is None:
            self._minecraftProfileJson = self._getMinecraftProfileJSON()
        return self._minecraftProfileJson

    def getMinecraftProfileDirectory(self, profileName):
        try:
            profileDir = self.minecraftProfileJSON['profiles'][profileName]['gameDir']
            # profileDir update to correct location.
            return profileDir
        except (IOError, OSError, KeyError):
            return self.minecraftLauncherDirectory

    def _getSaveFileDirectory(self):
        return os.path.join(self.getMinecraftProfileDirectory(self.selectedProfile), "saves")

    @staticmethod
    def _getMinecraftLauncherDirectory():
        if sys.platform == "win32":
            return os.path.join(os.getenv('APPDATA'), ".minecraft")
        elif sys.platform == "darwin":
            return os.path.expanduser("~/Library/Application Support/minecraft")
        else:
            return os.path.expanduser("~/.minecraft")

    def _getMinecraftProfileJSON(self):
        try:
            with open(os.path.join(self.minecraftLauncherDirectory, "launcher_profiles.json")) as jsonString:
                minecraftProfilesJSON = json.load(jsonString)
            return minecraftProfilesJSON
        except (IOError, ValueError, OSError):
            return None


class _MCEditDirectories(object):

    _INI = u"mcedit.ini"
    _USERCACHE = u"usercache.json"
    _FILES = [u"brushes", u"schematics", u"filters", u"serverJarStorage", u"config", u"usercache"]

    def __init__(self):
        self.setup = False
        self._portable = None
        self._dataDirectory = ""

    def __getitem__(self, item):
        if not self.setup:
            self._setupMCEditDirectories()
        return _unicodify(getattr(self, "_" + item))

    def _setupMCEditDirectories(self):
        log.info(u"Setting up MCEdit directories")
        self._renameLegacyDirs()
        self._portable = not self._fixedFilesExist()
        if not self._portable:
            print u"Running in fixed mode. Support files can be found at %s" % self._getFixedMCEditDirectory()
        else:
            print u"Running in portable mode. Support files can be found at %s" % self._getPortableMCEditDirectory()
        self.setup = True
        for f in self._FILES:
            path = self[f]
            if f not in (u"config", u"usercache"):
                if os.path.exists(path):
                    continue
                os.makedirs(path)
            else:
                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                if not os.path.exists(path):
                    _f = open(path, 'w')
                    _f.close()

    @staticmethod
    def _renameLegacyDirs():
        u = os.path.expanduser
        if sys.platform == 'darwin':
            if os.path.exists(u(u"~/Library/Application Support/pymclevel")):
                os.rename(u(u"~/Library/Application Support/pymclevel"),
                          u(u"~/Library/Application Support/MCEdit"))
        elif sys.platform != 'win32':  # Linux etc.
            if os.path.exists(u(u"~/.pymclevel")):
                os.rename(u(u"~/.pymclevel"),
                          u(u"~/.mcedit"))

    @property
    def portable(self):
        if not self.setup:
            self._setupMCEditDirectories()
        return self._portable

    @property
    def _parentDirectory(self):
        return os.path.dirname(getDataDirectory())

    @property
    def _filters(self):
        return os.path.join(self._getSupportDir(), u"Filters")

    @property
    def _schematics(self):
        return os.path.join(self._getSupportDir(), u"Schematics")

    @property
    def _serverJarStorage(self):
        return os.path.join(self._getSupportDir(), u"ServerJarStorage")

    @property
    def _brushes(self):
        return os.path.join(self._getSupportDir(), u"Brushes")

    @property
    def _usercache(self):
        return os.path.join(self._getSupportDir(), self._USERCACHE)

    @property
    def _config(self):
        if sys.platform == "darwin":
            return os.path.join(os.path.expanduser(u"~/Library/Preferences"), self._INI)
        return os.path.join(self._getSupportDir(), self._INI)

    @property
    def userCacheFilePath(self):
        return self._usercache

    def _getSupportDir(self):
        if sys.platform == "darwin":
            return os.path.expanduser(u"~/Library/Application Support/MCEdit")
        return self._getPortableMCEditDirectory() if self._portable else self._getFixedMCEditDirectory()

    def goFixed(self):
        assert self._portable is True
        if not self.setup:
            self._setupMCEditDirectories()
        self._setPortable(False)

    def goPortable(self):
        assert self._portable is False
        if not self.setup:
            self._setupMCEditDirectories()
        self._setPortable(True)

    def _setPortable(self, value):
        if sys.platform == 'darwin':
            return
        if not value:
            print u"Moving to fixed mode. Support files can be found at %s" % self._getFixedMCEditDirectory()
        else:
            print u"Moving to portable mode. Support files can be found at %s" % self._getPortableMCEditDirectory()
        old_paths = [self[key] for key in self._FILES]
        self._portable = value
        new_paths = [self[key] for key in self._FILES]
        for o, n in zip(old_paths, new_paths):
            if os.path.exists(o):
                _move_displace(o, n)

    @staticmethod
    def _getFixedMCEditDirectory():
        if sys.platform == "darwin":
            return ""
        elif sys.platform == "win32":
            folder = os.path.join(os.path.expanduser(os.path.join(u"~", u"Documents")), u"MCEdit")
        else:
            folder = os.path.expanduser(u"~/.mcedit")
        return folder

    def _getPortableMCEditDirectory(self):
        if sys.platform == "darwin":
            return ""
        return self._parentDirectory

    def _fixedFilesExist(self):
        return os.path.exists(os.path.join(self._getFixedMCEditDirectory(), self._INI)) or not os.path.exists(
            os.path.join(self._getPortableMCEditDirectory(), self._INI)) or sys.platform == "darwin"


_mcdirs = _MinecraftDirectories()
_mceditdirs = _MCEditDirectories()


def getDataDirectory(path=""):
    """
    MCEdit's executable root data directory.
    Note that for windows PyInstaller, this directory is temporary.
    Files should never be written here, but it can be used
    to access data files (like images or fonts).
    :return: MCEdit's main data directory.
    :rtype: unicode
    """
    if sys.platform == "win32":
        dataDir = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
    else:
        dataDir = os.path.dirname(os.path.abspath(__file__))
    dataDir = _unicodify(dataDir)
    if len(path) > 0:
        dataDir = os.path.join(dataDir, path)
    return dataDir


def getMinecraftLauncherDirectory():
    """
    Use this to obtain the path to MC's launcher directory.
    Can be used to access minecraft's assets, version etc.
    :return: Path to minecraft launcher directory
    :rtype: unicode
    """
    return _unicodify(_mcdirs.minecraftLauncherDirectory)


def getMinecraftProfileJSON():
    """
    Use this to obtain the json file in minecraft_profiles.json.
    :return: Minecrafts profile json.
    :rtype: dict
    """
    return _mcdirs.minecraftProfileJSON


def getSelectedProfile():
    """
    Returns the name of minecrafts selected profile.
    :return: Name of the selected profile
    :rtype: unicode
    """
    assert(type(_mcdirs.selectedProfile)) == unicode
    return _mcdirs.selectedProfile


def getMinecraftSaveFileDirectory():
    return _unicodify(_mcdirs.minecraftSaveFileDirectory)


def getMinecraftProfileDirectory(profileName):
    return _unicodify(_mcdirs.getMinecraftProfileDirectory(profileName))


def getFiltersDirectory():
    return _mceditdirs['filters']


def getSchematicsDirectory():
    return _mceditdirs['schematics']


def getBrushesDirectory():
    return _mceditdirs['brushes']


def getJarStorageDirectory():
    return _mceditdirs['serverJarStorage']


def getConfigFilePath():
    return _mceditdirs['config']


def getUserCacheFilePath():
    return _mceditdirs['usercache']


def getScreenShotDir():
    return _mceditdirs['screenshots']


def goFixed():
    _mceditdirs.goFixed()


def goPortable():
    _mceditdirs.goPortable()


def isPortable():
    return _mceditdirs.portable


def getAllOfAFile(file_dir, ext):
    """Returns a list of all the files the directory with the specified file extension.
    :param file_dir: Directory to search
    :param ext: The file extension (IE: ".py")
    """
    return _unicodify(glob.glob(file_dir + u"/*" + ext))
