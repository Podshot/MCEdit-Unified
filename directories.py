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


def findDataDir():
    def fsdecode(x):
        return x.decode(sys.getfilesystemencoding())

    argzero = fsdecode(os.path.abspath(sys.argv[0]))

    if sys.platform == "win32":
        if hasattr(sys, 'frozen'):
            dataDir = os.path.dirname(fsdecode(sys.executable))
        else:
            dataDir = os.path.dirname(argzero)

    elif sys.platform == "darwin":
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
                minecraftProfilesJSON = json.load(jsonString)
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

def getAllFilters(filters_dir):
    return glob.glob(filters_dir+"/*.py")
    


saveFileDir = os.path.join(getMinecraftProfileDirectory(getSelectedProfile()), u"saves")
dataDir = findDataDir()
