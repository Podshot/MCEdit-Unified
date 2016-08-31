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
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""
import time
import traceback
t= time.time()
import sys
import os
import json
import glob
import shutil


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
    
def getNewDataDir(path=""):
    '''
    Returns the directory where the executable is located (This function is only ran on Windows OS's)
    
    :param path: Additional directories/files to join to the data directory path
    
    :return unicode
    '''
    dataDir = os.path.dirname(os.path.abspath(__file__))
    #print "Dynamic: " + str(os.getcwdu())
    #print "Fixed: " + str(dataDir) 
    if len(path) > 0:
        return os.path.join(dataDir, path)
    return dataDir

getNewDataDir()

def getDataDir(path=""):
    '''
    Returns the folder where the executable is located. (This function is ran on non-Windows OS's)
    
    :param path: Additional directories/files to join to the data directory path
    
    :return unicode
    '''
    # if sys.platform == "win32":
    #     def fsdecode(x):
    #         return x.decode(sys.getfilesystemencoding())
    #
    #     dataDir = os.getcwdu()
    #     '''
    #     if getattr(sys, 'frozen', False):
    #         dataDir = os.path.dirname(sys._MEIPASS)
    #     else:
    #         dataDir = os.path.dirname(__file__)
    #     '''
    #
    # else:
    dataDir = os.getcwdu()
    if len(path) > 0:
        return os.path.join(dataDir, path)
    return dataDir

if sys.platform == "win32":
    getDataDir = getNewDataDir

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


def getMinecraftProfileJSON():
    """Returns a dictionary object with the minecraft profile information"""
    if os.path.isfile(os.path.join(getMinecraftLauncherDirectory(), u"launcher_profiles.json")):
        try:
            with open(os.path.join(getMinecraftLauncherDirectory(), u"launcher_profiles.json"), 'rb') as jsonString:
                minecraftProfilesJSON = json.loads(jsonString.read().decode(sys.getfilesystemencoding()))
            return minecraftProfilesJSON
        except:
            return None


def getMinecraftProfileDirectory(profileName):
    """Returns the path to the sent minecraft profile directory"""
    try:
        profileDir = getMinecraftProfileJSON()['profiles'][profileName]['gameDir']  # profileDir update to correct location.
        return profileDir
    except:
        return os.path.join(getMinecraftLauncherDirectory())


def getMinecraftLauncherDirectory():
    '''
    Returns the /minecraft directory, note: may not contain the /saves folder!
    '''
    if sys.platform == "win32":
        return os.path.join(win32_appdata(), ".minecraft")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/minecraft")
    else:
        return os.path.expanduser("~/.minecraft")


def getDocumentsFolder():
    if sys.platform == "win32":
        try:
            import win32com.client
            from win32com.shell import shell, shellcon
            objShell = win32com.client.Dispatch("WScript.Shell")
            docsFolder = objShell.SpecialFolders("MyDocuments")

        except Exception, e:
            print e
            try:
                docsFolder = shell.SHGetFolderPath(0, shellcon.CSIDL_MYDOCUMENTS, 0, 0)
            except Exception:
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
    """
    Gets the selected profile from the Minecraft Launcher
    """
    try:
        selectedProfile = getMinecraftProfileJSON()['selectedProfile']
        return selectedProfile
    except:
        return None

_minecraftSaveFileDir = None

def getMinecraftSaveFileDir():
    global _minecraftSaveFileDir
    if _minecraftSaveFileDir is None:
        _minecraftSaveFileDir = os.path.join(getMinecraftProfileDirectory(getSelectedProfile()), u"saves")
    return _minecraftSaveFileDir

minecraftSaveFileDir = getMinecraftSaveFileDir()

ini = u"mcedit.ini"
cache = u"usercache.json"

parentDir = os.path.dirname(getDataDir())
docsFolder = os.path.join(getDocumentsFolder(),'MCEdit')

if sys.platform != "darwin":

    portableConfigFilePath = os.path.join(parentDir, ini)
    portableCacheFilePath = os.path.join(parentDir, cache)
    portableGenericSupportPath = os.path.join(parentDir)
    portableSchematicsDir = os.path.join(parentDir, u"Schematics")
    portableBrushesDir = os.path.join(parentDir, u"Brushes")
    portableJarStorageDir = os.path.join(parentDir, u"ServerJarStorage")
    portableFiltersDir = os.path.join(parentDir, u"Filters")
    if not os.path.exists(parentDir):
        os.makedirs(parentDir)

    fixedCacheFilePath = os.path.join(docsFolder, cache)
    fixedConfigFilePath = os.path.join(docsFolder, ini)
    fixedGenericSupportPath = os.path.join(docsFolder)
    fixedSchematicsDir = os.path.join(docsFolder, u"Schematics")
    fixedBrushesDir = os.path.join(docsFolder, u"Brushes")
    fixedJarStorageDir = os.path.join(docsFolder, u"ServerJarStorage")
    fixedFiltersDir = os.path.join(docsFolder, u"Filters")
    if not os.path.exists(docsFolder):
        os.makedirs(docsFolder)
        
def hasPreviousPortableInstallation():
    portableDirectoriesFound = (os.path.exists(portableConfigFilePath) or os.path.exists(portableCacheFilePath) or
            os.path.exists(portableGenericSupportPath) or os.path.exists(portableSchematicsDir) or
            os.path.exists(portableBrushesDir) or os.path.exists(portableJarStorageDir) or
            os.path.exists(portableFiltersDir))
    return portableDirectoriesFound

def hasPreviousFixedInstallation():
    fixedDirectoriesFound = (os.path.exists(fixedConfigFilePath) or os.path.exists(fixedCacheFilePath) or
            os.path.exists(fixedGenericSupportPath) or os.path.exists(fixedSchematicsDir) or
            os.path.exists(fixedBrushesDir) or os.path.exists(fixedJarStorageDir) or
            os.path.exists(fixedFiltersDir))
    return fixedDirectoriesFound

def goPortable(useExisting):
    if sys.platform == "darwin":
        return False
    global configFilePath, schematicsDir, filtersDir, portable, brushesDir
    
    if not useExisting:
        if os.path.exists(fixedSchematicsDir):
            move_displace(fixedSchematicsDir, portableSchematicsDir)
        if os.path.exists(fixedBrushesDir):
            move_displace(fixedBrushesDir, portableBrushesDir)
        if os.path.exists(fixedConfigFilePath):
            move_displace(fixedConfigFilePath, portableConfigFilePath)
        if os.path.exists(fixedFiltersDir):
            move_displace(fixedFiltersDir, portableFiltersDir)
        if os.path.exists(fixedCacheFilePath):
            move_displace(fixedCacheFilePath, portableCacheFilePath)
        if os.path.exists(fixedJarStorageDir):
            move_displace(fixedJarStorageDir, portableJarStorageDir)

    if filtersDir in sys.path:
        sys.path.remove(filtersDir)

    schematicsDir = portableSchematicsDir
    brushesDir = portableBrushesDir
    configFilePath = portableConfigFilePath
    filtersDir = portableFiltersDir

    sys.path.append(filtersDir)

    portable = True
    return True


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
    return True

def goFixed(useExisting):
    if sys.platform == "darwin":
        return False
    global configFilePath, schematicsDir, filtersDir, portable, cacheDir, brushesDir
    
    if not useExisting:
        if os.path.exists(portableSchematicsDir):
            move_displace(portableSchematicsDir, fixedSchematicsDir)
        if os.path.exists(portableBrushesDir):
            move_displace(portableBrushesDir, fixedBrushesDir)
        if os.path.exists(portableConfigFilePath):
            move_displace(portableConfigFilePath, fixedConfigFilePath)
        if os.path.exists(portableFiltersDir):
            move_displace(portableFiltersDir, fixedFiltersDir)
        if os.path.exists(portableCacheFilePath):
            move_displace(portableCacheFilePath, fixedCacheFilePath)
        if os.path.exists(portableJarStorageDir):
            move_displace(portableJarStorageDir, fixedJarStorageDir)

    if filtersDir in sys.path:
        sys.path.remove(filtersDir)

    schematicsDir = fixedSchematicsDir
    brushesDir = fixedBrushesDir
    configFilePath = fixedConfigFilePath
    filtersDir = fixedFiltersDir

    sys.path.append(filtersDir)

    portable = False


def fixedConfigExists():
    if sys.platform == "darwin":
        return True
    # Check for files at portable locations. Cannot be Mac because config doesn't move
    return os.path.exists(fixedConfigFilePath) or not os.path.exists(portableConfigFilePath)


if fixedConfigExists():
    print "Running in fixed mode. Support files are in your " + (
        sys.platform == "darwin" and "App Support Folder (Available from the main menu of MCEdit)"
        or "Documents folder.")
    portable = False
    if not sys.platform == "darwin":
        schematicsDir = fixedSchematicsDir
        brushesDir = fixedBrushesDir
        configFilePath = fixedConfigFilePath
        filtersDir = fixedFiltersDir
        jarStorageDir = fixedJarStorageDir
        genericSupportDir = fixedGenericSupportPath

else:
    print "Running in portable mode. Support files are stored next to the MCEdit directory."
    if not sys.platform == "darwin":
        schematicsDir = portableSchematicsDir
        brushesDir = portableBrushesDir
        configFilePath = portableConfigFilePath
        filtersDir = portableFiltersDir
        jarStorageDir = portableJarStorageDir
        genericSupportDir = portableGenericSupportPath
    portable = True

#if portable:
#    serverJarStorageDir = portableJarStorageDir
#    ServerJarStorage.defaultCacheDir = serverJarStorageDir
#    jarStorage = ServerJarStorage(serverJarStorageDir)
#else:
#    serverJarStorageDir = fixedJarStorageDir


def getAllOfAFile(file_dir, ext):
    '''
    Returns a list of all the files the direcotry with the specified file extenstion
    :param file_dir: Directory to search
    :param ext: The file extension (IE: ".py")
    '''
    return glob.glob(file_dir+"/*"+ext)


def getCacheDir():
    """
    Returns the path to the cache folder.
    This folder is the Application Support folder on OS X, and the Documents Folder on Windows.
    :return unicode
    """
    if sys.platform == "win32":
        return genericSupportDir
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/pymclevel")
    else:
        try:
            return genericSupportDir
        except:
            return os.path.expanduser("~/.pymclevel")

if sys.platform == "darwin":
    configFilePath = os.path.expanduser("~/Library/Preferences/mcedit.ini")
    schematicsDir = os.path.join(getCacheDir(), u"Schematics")
    brushesDir = os.path.join(getCacheDir(), u"Brushes")
    filtersDir = os.path.join(getCacheDir(), u"Filters")
    if not os.path.exists(getCacheDir()):
        os.makedirs(getCacheDir())

# Create pymclevel folder as needed
if not os.path.exists(getCacheDir()):
    os.makedirs(getCacheDir())

# build the structures of directories if they don't exists
for directory in (filtersDir, brushesDir, schematicsDir):
    if not os.path.exists(directory):
        os.makedirs(directory)

bundledLibsDir = os.path.join(filtersDir, 'lib', 'Bundled Libraries')
if not os.path.exists(bundledLibsDir):
    os.makedirs(bundledLibsDir)

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


def getFiltersDir():
    return filtersDir
