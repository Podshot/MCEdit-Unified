'''
Created on Jul 22, 2011

@author: Rio
'''

from contextlib import contextmanager
from logging import getLogger
import sys
import os
import json

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


def win32_appdata():
    # try to use win32 api to get the AppData folder since python doesn't populate os.environ with unicode strings.

    try:
        import win32com.client

        objShell = win32com.client.Dispatch("WScript.Shell")
        return objShell.SpecialFolders("AppData")
    except Exception, e:
        print "Error while getting AppData folder using WScript.Shell.SpecialFolders: {0!r}".format(e)
        try:
            from win32com.shell import shell, shellcon

            return shell.SHGetPathFromIDListEx(
                shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_APPDATA)
            )
        except Exception, e:
            print "Error while getting AppData folder using SHGetSpecialFolderLocation: {0!r}".format(e)

            return os.environ['APPDATA'].decode(sys.getfilesystemencoding())


def getAppDataDirectory():
    if sys.platform == "win32":
        return win32_appdata()
    elif sys.platform == "darwin":
        return os.path.expanduser(u"~/Library/Application Support")
    else:
        return os.path.expanduser(u"~")


def getMinecraftLauncherDirectory():
    if sys.platform == "darwin":
        return os.path.join(getAppDataDirectory(), u"minecraft")
    else:
        return os.path.join(getAppDataDirectory(), u".minecraft")


def getPYMCAppDataDirectory():
    if sys.platform == "win32" or "darwin":
        return os.path.join(getAppDataDirectory(), u"pymclevel")
    else:
        return os.path.join(getAppDataDirectory(), u".pymclevel")


def getMinecraftProfileJSON():
    if os.path.isfile(os.path.join(getMinecraftLauncherDirectory(), u"launcher_profiles.json")):
        try:
            with open(os.path.join(getMinecraftLauncherDirectory(), u"launcher_profiles.json")) as jsonString:
                minecraftProfilesJSON = json.load(jsonString.read())
            return minecraftProfilesJSON
        except:
            return None


def getMinecraftProfileDirectory(profileName):
    try:
        profileDir = getMinecraftProfileJSON()['profiles'][profileName][
            'gameDir']  # profileDir update to correct location.
        return profileDir
    except:
        return os.path.join(getMinecraftLauncherDirectory())


def getSelectedProfile():
    try:
        selectedProfile = getMinecraftProfileJSON()['selectedProfile']
        return selectedProfile
    except:
        return None


saveFileDir = os.path.join(getMinecraftProfileDirectory(getSelectedProfile()), u"saves")
