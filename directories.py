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
    """Returns the path to the cache folder. This folder is the Application Support folder on OS X, and the Documents Folder on Windows."""
    if sys.platform == "win32":
        return os.path.join(os.path.join(getDocumentsFolder(),'MCEdit'))
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
        return os.path.join(win32_appdata(), ".minecraft")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/minecraft")
    else:
        return os.path.expanduser("~/.minecraft")

def getDocumentsFolder():
    docsFolder = None

    if sys.platform == "win32":
        try:
            import win32com.client
            objShell = win32com.client.Dispatch("WScript.Shell")
            docsFolder = objShell.SpecialFolders("MyDocuments")

        except Exception, e:
            print e
            try:
                docsFolder = shell.SHGetFolderPath(0, shellcon.CSIDL_MYDOCUMENTS, 0, 0)
            except Exception, e:
                userprofile = os.environ['USERPROFILE'].decode(sys.getfilesystemencoding())
                docsFolder = os.path.join(userprofile, "Documents")

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
if not os.path.exists(getCacheDir()):
    os.makedirs(getCacheDir())

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


ini = u"mcedit.ini"
cache = u"usercache.json"

parentDir = os.path.dirname(getDataDir())
docsFolder = os.path.join(getDocumentsFolder(),'MCEdit')

portableConfigFilePath = os.path.join(parentDir, cache)
portableCacheFilePath = os.path.join(parentDir, ini)
portableSchematicsDir = os.path.join(parentDir, u"Schematics")
portableJarStorageDir = os.path.join(parentDir, u"ServerJarStorage")
portableFiltersDir = os.path.join(parentDir, u"Filters")
if not os.path.exists(parentDir):
    os.makedirs(parentDir)

fixedCacheFilePath = os.path.join(docsFolder, cache)
fixedConfigFilePath = os.path.join(docsFolder, ini)
fixedSchematicsDir = os.path.join(docsFolder, u"Schematics")
FixedJarStorageDir = os.path.join(docsFolder, u"ServerJarStorage")
fixedFiltersDir = os.path.join(docsFolder, u"Filters")
if not os.path.exists(docsFolder):
    os.makedirs(docsFolder)

if sys.platform == "darwin":
    # parentDir is MCEdit.app/Contents/
    if ".app" in parentDir:
        folderContainingAppPackage = dirname(dirname(parentDir)) # Running frmo app bundle
    else:
        folderContainingAppPackage = parentDir # Running from source
    oldPath = fixedConfigFilePath

    fixedConfigFilePath = os.path.expanduser("~/Library/Preferences/mcedit.ini")
    fixedSchematicsDir = os.path.join(directories.getCacheDir(), u"Schematics")
    fixedFiltersDir = os.path.join(directories.getCacheDir(), u"Filters")
    if not os.path.exists(directories.getCacheDir()):
        os.makedirs(directories.getCacheDir())

    if os.path.exists(oldPath):
        try:
            os.rename(oldPath, fixedConfigFilePath)
        except Exception, e:
            print repr(e)

    portableConfigFilePath = os.path.join(folderContainingAppPackage, ini)
    portableSchematicsDir = os.path.join(folderContainingAppPackage, u"MCEdit/Schematics")
    portableFiltersDir = os.path.join(folderContainingAppPackage, u"MCEdit/Filters")
    try:
        if not os.path.exists(os.path.join(folderContainingAppPackage,"MCEdit")):
            os.makedirs(os.path.join(folderContainingAppPackage,"MCEdit"))
    except:
        print "Error making {}".format(os.path.join(folderContainingAppPackage,"MCEdit"))

print portableFiltersDir

def goPortable():
    global configFilePath, schematicsDir, filtersDir, portable

    if os.path.exists(fixedSchematicsDir):
        move_displace(fixedSchematicsDir, portableSchematicsDir)
    if os.path.exists(fixedConfigFilePath):
        move_displace(fixedConfigFilePath, portableConfigFilePath)
    if os.path.exists(fixedFiltersDir):
        move_displace(fixedFiltersDir, portableFiltersDir)

    schematicsDir = portableSchematicsDir
    configFilePath = portableConfigFilePath
    filtersDir = portableFiltersDir
    portable = True


def move_displace(src, dst):
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


def goFixed():
    global configFilePath, schematicsDir, filtersDir, portable

    if os.path.exists(portableSchematicsDir):
        move_displace(portableSchematicsDir, fixedSchematicsDir)
    if os.path.exists(portableConfigFilePath):
        move_displace(portableConfigFilePath, fixedConfigFilePath)
    if os.path.exists(portableFiltersDir):
        move_displace(portableFiltersDir, fixedFiltersDir)

    schematicsDir = fixedSchematicsDir
    configFilePath = fixedConfigFilePath
    filtersDir = fixedFiltersDir
    portable = False


def portableConfigExists():
    return (os.path.exists(portableConfigFilePath)  # mcedit.ini in MCEdit folder
            or (sys.platform != 'darwin' and not os.path.exists(
        fixedConfigFilePath)))  # no mcedit.ini in Documents folder (except on OS X when we always want it in Library/Preferences


if portableConfigExists():
    print "Running in portable mode. MCEdit/Schematics, MCEdit/Filters, and mcedit.ini are stored alongside " + (
    sys.platform == "darwin" and "MCEdit.app" or "MCEditData")
    portable = True
    schematicsDir = portableSchematicsDir
    configFilePath = portableConfigFilePath
    filtersDir = portableFiltersDir

else:
    print "Running in fixed install mode. MCEdit/Schematics, MCEdit/Filters, and mcedit.ini are in your " + (
    sys.platform == "darwin" and "App Support Folder (Available from the main menu of MCEdit)" or "Documents folder.")
    schematicsDir = fixedSchematicsDir
    configFilePath = fixedConfigFilePath
    filtersDir = fixedFiltersDir
    portable = False
    

#if portable:
#    serverJarStorageDir = (os.path.join(parentDir, "ServerJarStorage"))
#    ServerJarStorage.defaultCacheDir = serverJarStorageDir
#    jarStorage = ServerJarStorage(serverJarStorageDir)
#else:
#    jarStorage = ServerJarStorage()


