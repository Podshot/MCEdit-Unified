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
elif sys.platform == 'linux2':
    try:
        import Xlib.display
        import Xlib.X
        hasXlibDisplay = True
    except ImportError:
        hasXlibDisplay = None

os.environ["YAML_ROOT"] = join(directories.getDataDir(), "pymclevel").encode(enc)

from pygame import display

from albow import request_new_filename, request_old_filename
from albow.translate import _
from pymclevel import minecraftSaveFileDir, getMinecraftProfileDirectory, getSelectedProfile

try:
    import gtk
    if gtk.pygtk_version < (2,3,90):
        raise ImportError
    hasGtk = True
except ImportError:
    hasGtk = False #Using old method as fallback


texturePacksDir = os.path.join(getMinecraftProfileDirectory(getSelectedProfile()), "texturepacks")
#Compatibility layer for filters:
filtersDir = directories.filtersDir
schematicsDir = directories.schematicsDir

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
        initialDir = lastSchematicsDir or directories.schematicsDir

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

        elif hasGtk: #Linux (When GTK 2.4 or newer is installed)
            return askOpenFileGtk(title, suffixes, initialDir)

        else:
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

def askOpenFileGtk(title, suffixes, initialDir):
    chooser = gtk.FileChooserDialog(title,
                                    None, gtk.FILE_CHOOSER_ACTION_SAVE,
                                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                    gtk.STOCK_OPEN, gtk.RESPONSE_OK))

    chooser.set_default_response(gtk.RESPONSE_OK)
    chooser.set_current_folder(initialDir)
    chooser.set_current_name("world") #For some reason the Windows isn't closing if this line ins missing or the parameter is ""

    #Add custom Filter
    filter = gtk.FileFilter()
    filter.set_name("Levels and Schematics")
    for suffix in suffixes:
        filter.add_pattern("*."+suffix)
    chooser.add_filter(filter)

    #Add "All files" Filter
    filter = gtk.FileFilter()
    filter.set_name("All files")
    filter.add_pattern("*")
    chooser.add_filter(filter)

    response = chooser.run()
    if response == gtk.RESPONSE_OK:
        filename = chooser.get_filename()
    else:
        chooser.destroy()
        return # pressed cancel
    chooser.destroy()

    return filename

def askSaveSchematic(initialDir, displayName, fileFormat):
    return askSaveFile(initialDir,
                       title=_('Save this schematic...'),
                       defaultName=displayName + "." + fileFormat,
                       filetype=_('Minecraft Schematics (*.{0})\0*.{0}\0\0').format(fileFormat),
                       suffix=fileFormat,
    )


def askCreateWorld(initialDir):
    defaultName = name = _("Untitled World")
    i = 0
    while exists(join(initialDir, name)):
        i += 1
        name = defaultName + " " + str(i)

    return askSaveFile(initialDir,
                       title=_('Name this new world.'),
                       defaultName=name,
                       filetype=_('Minecraft World\0*.*\0\0'),
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

    elif hasGtk: #Linux (When GTK 2.4 or newer is installed)
        chooser = gtk.FileChooserDialog(title,
                                        None, gtk.FILE_CHOOSER_ACTION_SAVE,
                                        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_SAVE, gtk.RESPONSE_OK))

        chooser.set_default_response(gtk.RESPONSE_OK)
        chooser.set_current_folder(initialDir)
        chooser.set_current_name(defaultName)

        #Add custom Filter
        filter = gtk.FileFilter()
        filter.set_name(filetype[:filetype.index("\0")])
        filter.add_pattern("*." + suffix)
        chooser.add_filter(filter)

        #Add "All files" Filter
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        chooser.add_filter(filter)

        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
        else:
            chooser.destroy()
            return # pressed cancel

        chooser.destroy()

    else: #Fallback
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
