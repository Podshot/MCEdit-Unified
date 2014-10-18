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

import sys
import os
import json
import glob


def win32_utf8_argv():
    """Uses shell32.GetCommandLineArgvW to get sys.argv as a list of UTF-8
    strings.

    Versions 2.5 and older of Python don't support Unicode in sys.argv on
    Windows, with the underlying Windows API instead replacing multi-byte
    characters with '?'.

    Returns None on failure.

    Example usage:

    >>> def main(argv=None):
    ...    if argv is None:
    ...        argv = win32_utf8_argv() or sys.argv
    ...
    """

    try:
        from ctypes import POINTER, byref, cdll, c_int, windll
        from ctypes.wintypes import LPCWSTR, LPWSTR

        GetCommandLineW = cdll.kernel32.GetCommandLineW
        GetCommandLineW.argtypes = []
        GetCommandLineW.restype = LPCWSTR

        CommandLineToArgvW = windll.shell32.CommandLineToArgvW
        CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
        CommandLineToArgvW.restype = POINTER(LPWSTR)

        cmd = GetCommandLineW()
        argc = c_int(0)
        argv = CommandLineToArgvW(cmd, byref(argc))
        if argc.value > 0:
            # # Remove Python executable if present
            #            if argc.value - len(sys.argv) == 1:
            #                start = 1
            #            else:
            #                start = 0
            return [argv[i] for i in
                    xrange(0, argc.value)]
    except Exception:
        pass


def getDataDir():
    """Returns the folder where the executable is located."""
    if sys.platform == "win32":
        def fsdecode(x):
            return x.decode(sys.getfilesystemencoding())

        argzero = fsdecode(os.path.abspath(sys.argv[0]))
        if hasattr(sys, 'frozen'):
            dataDir = os.path.dirname(fsdecode(sys.executable))
        else:
            dataDir = os.path.dirname(argzero)
        dataDir = os.getcwdu()
    else:
        dataDir = os.getcwdu()

    return dataDir

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


def getCacheDir():
    """Returns the path to the cache folder. This folder is used to store files the user doesn't need to access."""
    if sys.platform == "win32":
        return os.path.join(win32_appdata(), "pymclevel")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/pymclevel")
    else:
        return os.path.expanduser("~/.pymclevel")


def getMinecraftProfileJSON():
    """Returns a dictionary object with the minecraft profile information"""
    if os.path.isfile(os.path.join(getMinecraftLauncherDirectory(), "launcher_profiles.json")):
        try:
            with open(os.path.join(getMinecraftLauncherDirectory(), "launcher_profiles.json")) as jsonString:
                minecraftProfilesJSON = json.load(jsonString)
            return minecraftProfilesJSON
        except:
            return None


def getMinecraftProfileDirectory(profileName):
    """Returns the path to the sent minecraft profile directory"""
    try:
        profileDir = getMinecraftProfileJSON()['profiles'][profileName][
            'gameDir']  # profileDir update to correct location.
        return profileDir
    except:
        return os.path.join(getMinecraftLauncherDirectory())


def getMinecraftLauncherDirectory():
    """Returns the /minecraft directory, note: may not contain the /saves folder!"""
    if sys.platform == "win32":
        return os.path.join(win32_appdata(), "minecraft")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/minecraft")
    else:
        return os.path.expanduser("~/.minecraft")

def getDocumentsFolder():
    docsFolder = None

    if sys.platform == "win32":
        try:
            objShell = win32com.client.Dispatch("WScript.Shell")
            docsFolder = objShell.SpecialFolders("MyDocuments")

        except Exception, e:
            print e
            try:
                docsFolder = shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, 0, 0)
            except Exception, e:
                userprofile = os.environ['USERPROFILE'].decode(sys.getfilesystemencoding())
                docsFolder = os.path.join(userprofile, _("Documents"))

    elif sys.platform == "darwin":
        docsFolder = os.path.expanduser("~/Documents")
    else:
        docsFolder = os.path.expanduser("~/.mcedit")
    try:
        os.mkdir(docsFolder)
    except:
        pass

    return docsFolder

def getSelectedProfile():
    try:
        selectedProfile = getMinecraftProfileJSON()['selectedProfile']
        return selectedProfile
    except:
        return None

def getAllFilters(filters_dir):
    return glob.glob(filters_dir+"/*.py")

# Create pymclevel folder as needed    
if not os.path.exists(self.getCacheDir()):
    os.makedirs(self.getCacheDir())

# set userCachePath
userCachePath = os.path.join(getCacheDir(),'usercache.json')
# Make sure it exists
try:
    if not os.path.exists(userCachePath):
        f = open(userCachePath,'w')
        f.write('{}')
        f.close()
except:
    print "Unable to make usercache.json at {}".format(userCachePath)

minecraftSaveFileDir = os.path.join(getMinecraftProfileDirectory(getSelectedProfile()), "saves")