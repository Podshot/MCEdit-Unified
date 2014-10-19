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
#-# Modified by D.C.-G. for translation purpose
from pymclevel.minecraft_server import ServerJarStorage, MCServerChunkGenerator

"""
mcplatform.py

Platform-specific functions, folder paths, and the whole fixed/portable nonsense.
"""

import directories
import os
from os.path import dirname, exists, join
import sys
import platform

enc = sys.getfilesystemencoding()

if sys.platform == "win32":
    if platform.architecture()[0] == "32bit":
        plat = "win32"
    if platform.architecture()[0] == "64bit":
        plat = "win-amd64"
    sys.path.append(join(directories.getDataDir(), "pymclevel", "build", "lib." + plat + "-2.6").encode(enc))

os.environ["YAML_ROOT"] = join(directories.getDataDir(), "pymclevel").encode(enc)

from pygame import display

from albow import request_new_filename, request_old_filename
from albow.translate import tr
from pymclevel import minecraftSaveFileDir, getMinecraftProfileDirectory, getSelectedProfile
from pymclevel import items

import shutil

texturePacksDir = os.path.join(getMinecraftProfileDirectory(getSelectedProfile()), "texturepacks")


def getTexturePacks():
    try:
        return os.listdir(texturePacksDir)
    except:
        return []

# for k,v in os.environ.iteritems():
# try:
#        os.environ[k] = v.decode(sys.getfilesystemencoding())
#    except:
#        continue
if sys.platform == "win32":
    try:
        from win32 import win32gui
        from win32 import win32api

        from win32.lib import win32con
    except ImportError:
        import win32gui
        import win32api

        import win32con

    try:
        import win32com.client
        from win32com.shell import shell, shellcon  # @UnresolvedImport
    except:
        pass

AppKit = None

if sys.platform == 'darwin':
    try:
        import AppKit
    except ImportError:
        pass

    cmd_name = "Cmd"
    option_name = "Opt"
else:
    cmd_name = "Ctrl"
    option_name = "Alt"

def OSXVersionChecker(name,compare):
    """Rediculously complicated function to compare current System version to inputted version."""
    if compare != 'gt' and compare != 'lt' and compare != 'eq' and compare != 'gteq' and compare != 'lteq':
        print "Invalid version check {}".format(compare)
        return False
    if sys.platform == 'darwin':
        try:
            systemVersion = platform.mac_ver()[0].split('.')
            if len(systemVersion) == 2:
                systemVersion.append('0')

            major, minor, patch = 10, 0, 0

            if (name.lower() == 'cheetah'):
                minor = 0
                patch = 4
            elif (name.lower() == 'puma'):
                minor = 1
                patch = 5
            elif (name.lower() == 'jaguar'):
                minor = 2
                patch = 8
            elif (name.lower() == 'panther'):
                minor = 3
                patch = 9
            elif (name.lower() == 'tiger'):
                minor = 4
                patch = 11
            elif (name.lower() == 'snow_leopard'):
                minor = 5
                patch = 8
            elif (name.lower() == 'snow_leopard'):
                minor = 6
                patch = 8
            elif (name.lower() == 'lion'):
                minor = 7
                patch = 5
            elif (name.lower() == 'mountain_lion'):
                minor = 8
                patch = 5
            elif (name.lower() == 'mavericks'):
                minor = 9
                patch = 5
            elif (name.lower() == 'yosemite'):
                minor = 10
                patch = 0
            else:
                major = 0

            ret_val = 0
            if int(systemVersion[0]) > int(major):
                ret_val = 1
            elif int(systemVersion[0]) < int(major):
                ret_val = -1
            else:
                if int(systemVersion[1]) > int(minor):
                    ret_val = 1
                elif int(systemVersion[1]) < int(minor):
                    ret_val = -1
                else:
                    if int(systemVersion[2]) > int(patch):
                        ret_val = 1
                    elif int(systemVersion[2]) < int(patch):
                        ret_val = -1
                    else:
                        ret_val = 0

            if ret_val == 0 and (compare == 'eq' or compare == 'gteq' or compare == 'lteq'):
                return True
            elif ret_val == -1 and (compare == 'lt' or compare == 'lteq'):
                return True
            elif ret_val == 1 and (compare == 'gt' or compare == 'gteq'):
                return True
        except:
            print "An error occured determining the system version"
            return False
    else:
        return False

lastSchematicsDir = None
lastSaveDir = None


def askOpenFile(title='Select a Minecraft level....', schematics=False):
    global lastSchematicsDir, lastSaveDir

    initialDir = lastSaveDir or minecraftSaveFileDir
    if schematics:
        initialDir = lastSchematicsDir or schematicsDir

    def _askOpen():
        suffixes = ["mclevel", "dat", "mine", "mine.gz"]
        if schematics:
            suffixes.append("schematic")
            suffixes.append("schematic.gz")
            suffixes.append("zip")

            suffixes.append("inv")

        if sys.platform == "win32":
            return askOpenFileWin32(title, schematics, initialDir)
        elif sys.platform == "darwin" and AppKit is not None:
            print "Open File"
            op = AppKit.NSOpenPanel.openPanel()
            op.setTitle_(title)
            op.setAllowedFileTypes_(suffixes)
            op.setAllowsOtherFileTypes_(True)

            op.setDirectory_(initialDir)
            if op.runModal() == 0:
                return  # pressed cancel

            AppKit.NSApp.mainWindow().makeKeyWindow()

            return op.filename()

        else:  # linux
            return request_old_filename(suffixes=suffixes, directory=initialDir)

    filename = _askOpen()
    if filename:
        if schematics:
            lastSchematicsDir = dirname(filename)
        else:
            lastSaveDir = dirname(filename)

    return filename


def askOpenFileWin32(title, schematics, initialDir):
    try:
        # if schematics:
        f = ('Levels and Schematics\0*.mclevel;*.dat;*.mine;*.mine.gz;*.schematic;*.zip;*.schematic.gz;*.inv\0' +
             '*.*\0*.*\0\0')
        #        else:
        #            f = ('Levels (*.mclevel, *.dat;*.mine;*.mine.gz;)\0' +
        #                 '*.mclevel;*.dat;*.mine;*.mine.gz;*.zip;*.lvl\0' +
        #                 '*.*\0*.*\0\0')

        (filename, customfilter, flags) = win32gui.GetOpenFileNameW(
            hwndOwner=display.get_wm_info()['window'],
            InitialDir=initialDir,
            Flags=(win32con.OFN_EXPLORER
                   | win32con.OFN_NOCHANGEDIR
                   | win32con.OFN_FILEMUSTEXIST
                   | win32con.OFN_LONGNAMES
                   # |win32con.OFN_EXTENSIONDIFFERENT
            ),
            Title=title,
            Filter=f,
        )
    except Exception, e:
        #print "Open File: ", e
        pass
    else:
        return filename


def askSaveSchematic(initialDir, displayName, fileFormat):
    return askSaveFile(initialDir,
                       title=tr('Save this schematic...'),
                       defaultName=displayName + "." + fileFormat,
                       filetype=tr('Minecraft Schematics (*.{0})\0*.{0}\0\0').format(fileFormat),
                       suffix=fileFormat,
    )


def askCreateWorld(initialDir):
    defaultName = name = tr("Untitled World")
    i = 0
    while exists(join(initialDir, name)):
        i += 1
        name = defaultName + " " + str(i)

    return askSaveFile(initialDir,
                       title=tr('Name this new world.'),
                       defaultName=name,
                       filetype=tr('Minecraft World\0*.*\0\0'),
                       suffix="",
    )


def askSaveFile(initialDir, title, defaultName, filetype, suffix):
    if sys.platform == "win32":
        try:
            (filename, customfilter, flags) = win32gui.GetSaveFileNameW(
                hwndOwner=display.get_wm_info()['window'],
                InitialDir=initialDir,
                Flags=win32con.OFN_EXPLORER | win32con.OFN_NOCHANGEDIR | win32con.OFN_OVERWRITEPROMPT,
                File=defaultName,
                DefExt=suffix,
                Title=title,
                Filter=filetype,
            )
        except Exception, e:
            print "Error getting file name: ", e
            return

        try:
            filename = filename[:filename.index('\0')]
            filename = filename.decode(sys.getfilesystemencoding())
        except:
            pass

    elif sys.platform == "darwin" and AppKit is not None:
        sp = AppKit.NSSavePanel.savePanel()
        sp.setDirectory_(initialDir)
        sp.setTitle_(title)
        sp.setAllowedFileTypes_([suffix])

        if sp.runModal() == 0:
            return # pressed cancel

        filename = sp.filename()
        AppKit.NSApp.mainWindow().makeKeyWindow()

    else:
        filename = request_new_filename(prompt=title,
                                        suffix=("." + suffix) if suffix else "",
                                        directory=initialDir,
                                        filename=defaultName,
                                        pathname=None)

    return filename



#   if sys.platform == "win32":
#       try:
#
#           (filename, customfilter, flags) = win32gui.GetSaveFileNameW(
#               hwndOwner = display.get_wm_info()['window'],
#               # InitialDir=minecraftSaveFileDir,
#               Flags=win32con.OFN_EXPLORER | win32con.OFN_NOCHANGEDIR | win32con.OFN_OVERWRITEPROMPT,
#               File=initialDir + os.sep + displayName,
#               DefExt=fileFormat,
#               Title=,
#               Filter=,
#               )
#       except Exception, e:
#           print "Error getting filename: {0!r}".format(e)
#           return
#
#   elif sys.platform == "darwin" and AppKit is not None:
#       sp = AppKit.NSSavePanel.savePanel()
#       sp.setDirectory_(initialDir)
#       sp.setAllowedFileTypes_([fileFormat])
#       # sp.setFilename_(self.editor.level.displayName)
#
#       if sp.runModal() == 0:
#           return;  # pressed cancel
#
#       filename = sp.filename()
#       AppKit.NSApp.mainWindow().makeKeyWindow()
#
#   else:
#
#       filename = request_new_filename(prompt = "Save this schematic...",
#                                       suffix = ".{0}".format(fileFormat),
#                                       directory = initialDir,
#                                       filename = displayName,
#                                       pathname = None)
#
#   return filename

def platform_open(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)
            # os.system('start ' + path + '\'')
        elif sys.platform == "darwin":
            # os.startfile(path)
            os.system('open "' + path + '"')
        else:
            os.system('xdg-open "' + path + '"')

    except Exception, e:
        print "platform_open failed on {0}: {1}".format(sys.platform, e)


win32_window_size = True

ini = u"mcedit.ini"
parentDir = dirname(directories.getDataDir())
docsFolder = os.path.join(directories.getDocumentsFolder(),'MCEdit')

portableConfigFilePath = os.path.join(parentDir, ini)
portableSchematicsDir = os.path.join(parentDir, u"Schematics")
portableFiltersDir = os.path.join(parentDir, u"Filters")
if not os.path.exists(parentDir):
    os.makedirs(parentDir)

fixedConfigFilePath = os.path.join(docsFolder, ini)
fixedSchematicsDir = os.path.join(docsFolder, u"Schematics")
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

if portable:
    serverJarStorageDir = (os.path.join(parentDir, "ServerJarStorage"))
    ServerJarStorage.defaultCacheDir = serverJarStorageDir
    jarStorage = ServerJarStorage(serverJarStorageDir)
else:
    jarStorage = ServerJarStorage()

