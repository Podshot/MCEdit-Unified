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
# -# Modified by D.C.-G. for translation purpose
# !# Tests for file chooser

"""
mcplatform.py

Platform-specific functions, folder paths, and the whole fixed/portable nonsense.
"""

import logging
log = logging.getLogger(__name__)

import directories
import os
from os.path import dirname, exists, join
import sys
import platform

enc = sys.getfilesystemencoding()

hasXlibDisplay = False
if sys.platform == "win32":
    if platform.architecture()[0] == "32bit":
        plat = "win32"
    if platform.architecture()[0] == "64bit":
        plat = "win-amd64"
    sys.path.append(join(directories.getDataDir(), "pymclevel", "build", "lib." + plat + "-2.6").encode(enc))
elif sys.platform in ['linux2', 'darwin']:
    try:
        import Xlib.display
        import Xlib.X
        import Xlib.protocol
        hasXlibDisplay = True
    except ImportError:
        hasXlibDisplay = None

os.environ["YAML_ROOT"] = join(directories.getDataDir(), "pymclevel").encode(enc)

from pygame import display

from albow import request_new_filename, request_old_filename
from albow.translate import _
from pymclevel import minecraftSaveFileDir, getMinecraftProfileDirectory, getSelectedProfile
from datetime import datetime

import re
import subprocess

try:
    import pygtk
    pygtk.require('2.0')
    import gtk
    if gtk.pygtk_version < (2, 3, 90):
        raise ImportError
    hasGtk = True
except ImportError:
    hasGtk = False  # Using old method as fallback


texturePacksDir = os.path.join(getMinecraftProfileDirectory(getSelectedProfile()), "texturepacks")
# Compatibility layer for filters:
filtersDir = directories.filtersDir
schematicsDir = directories.schematicsDir

# !# Disabling platform specific file chooser:
# !# Please, don't touch these two lines and the 'platChooser' stuff. -- D.C.-G.
# platChooser = sys.platform in ('linux2', 'darwin')
platChooser = sys.platform == 'darwin'

def dynamic_arguments(func_to_replace, askFile_func):
    def wrapper(initialDir, displayName, fileFormat):
        if isinstance(fileFormat, tuple):
            return func_to_replace(initialDir, displayName, fileFormat)
        else:
            
            def old_askSaveSchematic(initialDir, displayName, fileFormat):
                dt = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
                return askFile_func(initialDir,
                                   title=_('Save this schematic...'),
                                   defaultName=displayName + "_" + dt + "." + fileFormat,
                                   filetype=_('Minecraft Schematics (*.{0})\0*.{0}\0\0').format(fileFormat),
                                   suffix=fileFormat,
                                   )
            return old_askSaveSchematic(initialDir, displayName, fileFormat)
    return wrapper

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
    
    try:
        import pywintypes
    except:
        pass

if sys.platform == 'darwin':
    cmd_name = "Cmd"
    option_name = "Opt"
else:
    cmd_name = "Ctrl"
    option_name = "Alt"


def OSXVersionChecker(name, compare):
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

            if name.lower() == 'cheetah':
                minor = 0
                patch = 4
            elif name.lower() == 'puma':
                minor = 1
                patch = 5
            elif name.lower() == 'jaguar':
                minor = 2
                patch = 8
            elif name.lower() == 'panther':
                minor = 3
                patch = 9
            elif name.lower() == 'tiger':
                minor = 4
                patch = 11
            elif name.lower() == 'snow_leopard':
                minor = 5
                patch = 8
            elif name.lower() == 'snow_leopard':
                minor = 6
                patch = 8
            elif name.lower() == 'lion':
                minor = 7
                patch = 5
            elif name.lower() == 'mountain_lion':
                minor = 8
                patch = 5
            elif name.lower() == 'mavericks':
                minor = 9
                patch = 5
            elif name.lower() == 'yosemite':
                minor = 10
                patch = 0
            else:
                major = 0

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

def buildFileTypes(filetypes):
    result = ""
    for key in filetypes[0]:
        ftypes = []
        result += key + " ("
        for ftype in filetypes[0][key]:
            ftypes.append("*." + ftype)
        result += ",".join(ftypes) + ")\0"
        result += ";".join(ftypes) + "\0"
    return result + "\0"

def askOpenFile(title='Select a Minecraft level....', schematics=False, suffixes=None):
    title = _(title)
    global lastSchematicsDir, lastSaveDir

    if not suffixes:
        suffixes = ["mclevel", "dat", "mine", "mine.gz"]
        suffixesChanged = False
    else:
        suffixesChanged = True
    initialDir = lastSaveDir or minecraftSaveFileDir
    if schematics:
        initialDir = lastSchematicsDir or directories.schematicsDir

    def _askOpen(_suffixes):
        if schematics:
            _suffixes.append("schematic")
            _suffixes.append("schematic.gz")
            _suffixes.append("zip")

            _suffixes.append("inv")
            
            _suffixes.append("nbt")

            # BO support
            _suffixes.append("bo2")
            _suffixes.append("bo3")
            _suffixes.sort()

        if sys.platform == "win32":  # !#
            if suffixesChanged:
                sendSuffixes = _suffixes
            else:
                sendSuffixes = None
            return askOpenFileWin32(title, schematics, initialDir, sendSuffixes)

        elif hasGtk and not platChooser:  # !# #Linux (When GTK 2.4 or newer is installed)
            return askOpenFileGtk(title, _suffixes, initialDir)

        else:
            log.debug("Calling internal file chooser.")
            log.debug("'initialDir' is %s (%s)" % (repr(initialDir), type(initialDir)))
            try:
                iDir = initialDir.encode(enc)
            except Exception, e:
                iDir = initialDir
                log.debug("Could not encode 'initialDir' %s" % repr(initialDir))
                log.debug("Encode function returned: %s" % e)
            return request_old_filename(suffixes=_suffixes, directory=iDir)

    filename = _askOpen(suffixes)
    if filename:
        if schematics:
            lastSchematicsDir = dirname(filename)
        else:
            lastSaveDir = dirname(filename)

    return filename


def askOpenFileWin32(title, schematics, initialDir, suffixes=None):
    try:
        # if schematics:
        if not suffixes:
            f = (_('Levels and Schematics') + '\0*.mclevel;*.dat;*.mine;*.mine.gz;*.schematic;*.zip;*.schematic.gz;*.inv;*.nbt\0' + 
             '*.*\0*.*\0\0')
        else:
            f = "All\0"
            for suffix in suffixes:
                f += "*." + suffix + ";"
            f += "\0*.*\0\0"
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
    except Exception:
        # print "Open File: ", e
        pass
    else:
        return filename


def askOpenFileGtk(title, suffixes, initialDir):
    fls = []
    def run_dlg():
        chooser = gtk.FileChooserDialog(title,
                                        None, gtk.FILE_CHOOSER_ACTION_SAVE,
                                        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    
        chooser.set_default_response(gtk.RESPONSE_OK)
        chooser.set_current_folder(initialDir)
        chooser.set_current_name("world")  # For some reason the Windows isn't closing if this line ins missing or the parameter is ""

        # Add custom Filter
        file_filter = gtk.FileFilter()
        file_filter.set_name(_("Levels and Schematics"))
        for suffix in suffixes:
            file_filter.add_pattern("*." + suffix)
        chooser.add_filter(file_filter)

        # Add "All files" Filter
        file_filter = gtk.FileFilter()
        file_filter.set_name("All files")
        file_filter.add_pattern("*")
        chooser.add_filter(file_filter)

        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            fls.append(chooser.get_filename())
        else:
            fls.append(None)
        chooser.destroy()
        gtk.main_quit()

    gtk.idle_add(run_dlg)
    gtk.main()

    return fls[0]

def askSaveSchematic(initialDir, displayName, fileFormats):
    fileFormat = buildFileTypes(fileFormats)
    
    dt = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
    return askSaveFile(initialDir,
                       title=_('Save this schematic...'),
                       defaultName=displayName + "_" + dt + "." + fileFormats[0][fileFormats[0].keys()[0]][0],
                       filetype=fileFormat,
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
    if sys.platform == "win32":  # !#
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

    else:
        # Reformat the Windows stuff
        if "\0" in suffix and suffix.count("*.") > 1:
            _suffix = suffix.split("\0")[:-2]
        else:
            _suffix = suffix
        if "\0" in filetype and filetype.count("*.") > 1:
            _filetype = filetype.split("\0")[:-2]
        else:
            _filetype = filetype

        if hasGtk and not platChooser:  # !# #Linux (When GTK 2.4 or newer is installed)

            fls = []
            def run_dlg():
                chooser = gtk.FileChooserDialog(title,
                                                None, gtk.FILE_CHOOSER_ACTION_SAVE,
                                                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                gtk.STOCK_SAVE, gtk.RESPONSE_OK))

                chooser.set_default_response(gtk.RESPONSE_OK)
                chooser.set_current_folder(initialDir)
                chooser.set_current_name(defaultName)

                # Add custom Filter
                if type(_filetype) in (list, tuple):
                    for i, filet in enumerate(_filetype):
                        if i % 2 == 0:
                            file_filter = gtk.FileFilter()
                            file_filter.set_name(filet)
                            if ";" in _suffix[i + 1]:
                                for _suff in _suffix.split(";"):
                                    if _suff:
                                        file_filter.add_pattern(_suff)
                            else:
                                file_filter.add_pattern(_suffix[i + 1])
                            chooser.add_filter(file_filter)
                else:
                    file_filter = gtk.FileFilter()
                    file_filter.set_name(filetype[:filetype.index("\0")])
                    if "\0" in suffix and suffix.count("*.") > 1:
                        __suffix = suffix.split("\0")[:-2]
                    else:
                        __suffix = suffix
                    if type(__suffix) in (list, tuple):
                        for suff in __suffix:
                            file_filter.add_pattern("*." + suff)
                    else:
                        file_filter.add_pattern("*." + __suffix)
                    chooser.add_filter(file_filter)

                # Add "All files" Filter
                file_filter = gtk.FileFilter()
                file_filter.set_name("All files")
                file_filter.add_pattern("*")
                chooser.add_filter(file_filter)

                response = chooser.run()
                if response == gtk.RESPONSE_OK:
                    fls.append(chooser.get_filename())
                else:
                    fls.append(None)
                chooser.destroy()
                gtk.main_quit()

            gtk.idle_add(run_dlg)
            gtk.main()

            filename = fls[0]

        else:  # Fallback
            log.debug("Calling internal file chooser.")
            log.debug("'initialDir' is %s (%s)" % (repr(initialDir), type(initialDir)))
            log.debug("'defaultName' is %s (%s)" % (repr(defaultName), type(defaultName)))
            try:
                iDir = initialDir.encode(enc)
            except:
                iDir = initialDir
                log.debug("Could not encode 'initialDir' %s" % repr(initialDir))
                log.debug("Encode function returned: %s" % e)
            try:
                dName = defaultName.encode(enc)
            except:
                dName = defaultName
                log.debug("Could not encode 'defaultName' %s" % repr(defaultName))
                log.debug("Encode function returned: %s" % e)
            if type(_suffix) in (list, tuple):
                sffxs = [a[1:] for a in _suffix[1::2]]
                sffx = sffxs.pop(0)
                sffxs.append('.*')
            else:
                sffx = _suffix
                sffxs = []

            filename = request_new_filename(prompt=title,
                                        suffix=sffx,
                                        extra_suffixes=sffxs,
                                        directory=iDir,
                                        filename=dName,
                                        pathname=None)
    return filename

askSaveSchematic = dynamic_arguments(askSaveSchematic, askSaveFile)

# Start Open Folder Dialogs
# TODO: Possibly get an OS X dialog
def askOpenFolderWin32(title, initialDir):
    try:
        desktop_pidl = shell.SHGetFolderLocation(0, shellcon.CSIDL_DESKTOP, 0, 0)
        pidl, display_name, image_list = shell.SHBrowseForFolder (
                                                              win32gui.GetDesktopWindow(),
                                                              desktop_pidl,
                                                              "Choose a folder",
                                                              0,
                                                              None,
                                                              None
                                                              )
        return shell.SHGetPathFromIDList(pidl)
    except pywintypes.com_error as e:
        if e.args[0] == -2147467259:
            print "Invalid folder selected"
        pass

def askOpenFolderGtk(title, initialDir):
    if hasGtk:
        fls = []
        def run_dlg():
            chooser = gtk.FileChooserDialog(title,
                                        None, gtk.FILE_CHOOSER_ACTION_SAVE,
                                        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))

            chooser.set_default_response(gtk.RESPONSE_OK)
            chooser.set_current_folder(initialDir)
            chooser.set_current_name("world")
            chooser.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)

            response = chooser.run()
            if response == gtk.RESPONSE_OK:
                fls.append(chooser.get_filename())  # Returns the folder path if gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER is the action
            else:
                fls.append(None)
            chooser.destroy()
            gtk.main_quit()

        gtk.idle_add(run_dlg)
        gtk.main()
        return fls[0]
    else:
        print "You currently need gtk to use an Open Folder Dialog!"

# End Open Folder Dialogs


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


#=============================================================================
#=============================================================================
# DESKTOP ENVIRONMENTS AND OS SIDE WINDOW MANAGEMENT.
#
# The idea is to have a single object to deal with underling OS specific window management interface.
# This will help to save/restore MCEdit window sate, position and size.
#
# TODO:
# * Test on the actually unsupported Linux DEs.
# * Review WWindowHandler class for Windows.
# * Create a DWindowHandler class for Darwin (OSX).

# Window states
MINIMIZED = 0
NORMAL = 1
MAXIMIZED = 2
FULLSCREEN = 3

#=============================================================================
# Linux desktop environment detection.
#
# source: http://stackoverflow.com/questions/2035657/what-is-my-current-desktop-environment (http://stackoverflow.com/a/21213358)
#
# Tweaked, of course ;)
#
def get_desktop_environment():
        # From http://stackoverflow.com/questions/2035657/what-is-my-current-desktop-environment
        # and http://ubuntuforums.org/showthread.php?t=652320
        # and http://ubuntuforums.org/showthread.php?t=652320
        # and http://ubuntuforums.org/showthread.php?t=1139057
        if sys.platform in ["win32", "cygwin"]:
            return "windows"
        elif sys.platform == "darwin":
            return "mac"
        else:  # Most likely either a POSIX system or something not much common
            ds = os.environ.get("DESKTOP_SESSION", None)
            if ds in ('default', None):
                ds = os.environ.get("XDG_CURRENT_DESKTOP", None)
            if ds is not None:  # easier to match if we doesn't have  to deal with caracter cases
                desktop_session = ds.lower()
                found = re.findall(r"gnome|unity|cinnamon|mate|xfce4|lxde|fluxbox|blackbox|openbox|icewm|jwm|afterstep|trinity|kde", desktop_session, re.I)
                if len(found) == 1:
                    return found[0]
                elif len(found) > 1:
                    print "Houston? We have a problem...\n\nThe desktop environment can't be found: '%s' has been detected to be %s alltogeteher." % (ds, " and ".join((", ".join(found[:-1]), found[-1])))
                    return 'unknown'
                # # Special cases ##
                # Canonical sets $DESKTOP_SESSION to Lubuntu rather than LXDE if using LXDE.
                # There is no guarantee that they will not do the same with the other desktop environments.
                elif "xfce" in desktop_session or desktop_session.startswith("xubuntu"):
                    return "xfce4"
                elif desktop_session.startswith("ubuntu"):
                    return "unity"       
                elif desktop_session.startswith("lubuntu"):
                    return "lxde" 
                elif desktop_session.startswith("kubuntu"): 
                    return "kde" 
                elif desktop_session.startswith("razor"):  # e.g. razorkwin
                    return "razor-qt"
                elif desktop_session.startswith("wmaker"):  # e.g. wmaker-common
                    return "windowmaker"
                
            if os.environ.get('KDE_FULL_SESSION', None) == 'true':
                return "kde"
            elif os.environ.get('GNOME_DESKTOP_SESSION_ID', None):
                if not "deprecated" in os.environ.get('GNOME_DESKTOP_SESSION_ID', None):
                    return "gnome2"
            # From http://ubuntuforums.org/showthread.php?t=652320
            elif is_running("xfce-mcs-manage"):
                return "xfce4"
            elif is_running("ksmserver"):
                return "kde"
        return "unknown"

def is_running(process):
    # From http://www.bloggerpolis.com/2011/05/how-to-check-if-a-process-is-running-using-python/
    # and http://richarddingwall.name/2009/06/18/windows-equivalents-of-ps-and-kill-commands/
    try:  # Linux/Unix
        s = subprocess.Popen(["ps", "axw"], stdout=subprocess.PIPE)
    except:  # Windows
        s = subprocess.Popen(["tasklist", "/v"], stdout=subprocess.PIPE)
    for x in s.stdout:
        if re.search(process, x):
            return True
    return False

#=============================================================================
# Window handling.
desktop_environment = get_desktop_environment()

DEBUG_WM = False
USE_WM = True

# Desktops settings
# Each entry in the platform sub-dictionaries represent which object is used to get/set the window metrics.
#
# For Linux:
# Valid entries are: position_gap, position_getter, position_setter, size_getter, size_setter and state.
# Entries can be omitted; default values will be used.
# For position_gap the default is (0, 0, False, False)
# For the other ones, the default is the Pygame window object.
#
# position_gap is used on some environment to restore the windows at the coords it was formerly.
# The two first values of the tuple are the amount of pixels to add to the window x and y coords.
# The two last ones tell whether these pixels shall be added only once (at program startup) or always.
#
desktops = {'linux2': {
        'cinnamon': {  # Actually, there's a bug when resizing on XCinnamon.
            'position_setter': 'parent',
            'position_getter': 'parent.parent',
            'position_gap': (9, 8, True, True),
            'state': 'parent'
            },
        'gnome': {
            'position_setter': 'parent',
            'position_getter': 'parent.parent',
            'size_setter': 'parent',
            'size_getter': 'parent',
            'state': 'parent'
        },
        'kde': {
            'position_setter': 'parent',
            'position_getter': 'parent.parent.parent',
            'state': 'parent'
        },
        'unity': {
            'position_setter': 'parent',
            'position_getter': 'parent.parent.parent',
            'position_gap': (10, 10, False, False),
            'size_setter': 'parent',
            'state': 'parent'
        }
    },
#     'win32': {},
#     'darwin': {}
}

# The environments in the next definition need to be tested.
linux_unsuported = ('afterstep',
                    'blackbox',
                    'fluxbox',
                    'gnome2',
                    'icewm',
                    'jwm',
                    'lxde',
                    'mate',
                    'openbox',
                    'razor-qt',
                    'trinity',
                    'windowmaker',
                    'xfce4')

# Window handlers classes
class BaseWindowHandler:
    """Abstract class for the platform specific window handlers.
    If initialized, this class casts a NotImplementedError."""
    desk_env = desktop_environment

    def __init__(self, *args, **kwargs):
        """..."""
        if not len(kwargs):
            raise NotImplementedError, "Abstract class."
        self.mode = kwargs['mode']

    def set_mode(self, size, mode):
        """Wrapper for pygame.display.set_mode()."""
        display.set_mode(size, mode)

    def get_root_rect(self):
        """..."""
        raise NotImplementedError, "Abstract method."

    def get_size(self):
        """..."""
        raise NotImplementedError, "Abstract method."

    def set_size(self, size, update=True):
        """..."""
        raise NotImplementedError, "Abstract method."

    def get_position(self):
        """..."""
        raise NotImplementedError, "Abstract method."

    def set_position(self, pos, update=True):
        """..."""
        raise NotImplementedError, "Abstract method."

    def get_state(self):
        """..."""
        raise NotImplementedError, "Abstract method."

    def set_state(self, state=NORMAL, size=(-1, -1), pos=(-1, -1), update=True):
        """..."""
        raise NotImplementedError, "Abstract method."

    def flush(self):
        """Just does nothing..."""
        return

    def sync(self):
        """Just does nothing..."""
        return


class XWindowHandler(BaseWindowHandler):
    """Object to deal with XWindow managers (Linux)."""
    desk_env = desktop_environment
    def __init__(self, pos=(0, 0), size=(0, 0), mode=None):
        """Set up the internal handlers."""
        BaseWindowHandler.__init__(self, pos=pos, size=size, mode=mode)
        self.mode = mode
        # setup the internal data, especially the Xlib object we need.
        # Tests
        if DEBUG_WM:
            print "#" * 72
            print "XWindowHandler.__init__"
            print "Desktop environment:", desktop_environment
        dis = self.display = Xlib.display.Display()
        pygame_win = dis.create_resource_object('window', display.get_wm_info()['window'])
        pygame_win_id = pygame_win.id
        if DEBUG_WM:
            root = dis.screen().root
            active_wid_id = root.get_full_property(dis.intern_atom('_NET_ACTIVE_WINDOW'), Xlib.X.AnyPropertyType).value[0]
            active_win = dis.create_resource_object('window', active_wid_id)
            # Print pygame_win and active_win styff
            for (win, name) in ((pygame_win, 'pygame_win'), (active_win, 'active_win')):
                print "=" * 72
                print "%s guts" % name, "(ID %s)" % win.id
                print "-" * 72
                print "* State"
                prop = win.get_full_property(dis.intern_atom("_NET_WM_STATE"), 4)
                print " ", prop
                if prop:
                    print dir(prop)
                print "* Geometry"
                print " ", win.get_geometry()
                parent = win.query_tree().parent
                p = '%s.parent' % name
                while parent.id != root.id:
                    print "-" * 72
                    print p, "ID", parent.id
                    print "* State"
                    prop = parent.get_full_property(dis.intern_atom("_NET_WM_STATE"), 4)
                    print " ", prop
                    if prop:
                        print dir(prop)
                    print "* Geometry"
                    print " ", parent.get_geometry()
                    parent = parent.query_tree().parent
                    p += ".parent"

        # Size handlers
        self.base_handler = pygame_win
        self.base_handler_id = pygame_win.id
        size = desktops['linux2'][self.desk_env].get('size_getter', None)
        if size:
            if DEBUG_WM:
                print "size_getter.split('.')", size.split('.')
            handler = pygame_win
            for item in size.split('.'):
                handler = getattr(handler.query_tree(), item)
            self.sizeGetter = handler
        else:
            self.sizeGetter = pygame_win
        size = desktops['linux2'][self.desk_env].get('size_setter', None)
        if size:
            if DEBUG_WM:
                print "size_setter.split('.')", size.split('.')
            handler = pygame_win
            for item in size.split('.'):
                handler = getattr(handler.query_tree(), item)
            self.sizeSetter = handler
        else:
            self.sizeSetter = pygame_win
        # Position handlers
        pos = desktops['linux2'][self.desk_env].get('position_getter', None)
        if pos:
            if DEBUG_WM:
                print "pos_getter.split('.')", pos.split('.')
            handler = pygame_win
            for item in pos.split('.'):
                handler = getattr(handler.query_tree(), item)
            self.positionGetter = handler
        else:
            self.positionGetter = pygame_win
        pos = desktops['linux2'][self.desk_env].get('position_setter', None)
        if pos:
            if DEBUG_WM:
                print "pos_setter.split('.')", pos.split('.')
            handler = pygame_win
            for item in pos.split('.'):
                handler = getattr(handler.query_tree(), item)
            self.positionSetter = handler
        else:
            self.positionSetter = pygame_win
        # Position gap. Used to correct wrong positions on some environments.
        self.position_gap = desktops['linux2'][self.desk_env].get('position_gap', (0, 0, False, False))
        self.starting = True
        self.gx, self.gy = 0, 0
        # State handler
        state = desktops['linux2'][self.desk_env].get('state', None)
        if state:
            if DEBUG_WM:
                print "state.split('.')", state.split('.')
            handler = pygame_win
            for item in state.split('.'):
                handler = getattr(handler.query_tree(), item)
            self.stateHandler = handler
        else:
            self.stateHandler = pygame_win

        if DEBUG_WM:
            print "self.positionGetter:", self.positionGetter, 'ID:', self.positionGetter.id
            print "self.positionSetter:", self.positionSetter, 'ID:', self.positionSetter.id
            print "self.sizeGetter:", self.sizeGetter, 'ID:', self.sizeGetter.id
            print "self.sizeSetter:", self.sizeSetter, 'ID:', self.sizeSetter.id
            print "self.stateHandler:", self.stateHandler, 'ID:', self.stateHandler.id
            print self.stateHandler.get_wm_state()

    def get_root_rect(self):
        """Return a four values tuple containing the position and size of the very first OS window object."""
        geom = self.display.screen().root.get_geometry()
        return (geom.x, geom.y, geom.width, geom.height)

    def get_size(self):
        """Return the window actual size as a tuple (width, height)."""
        geom = self.sizeGetter.get_geometry()
        if DEBUG_WM:
            print "Actual size is", geom.width, geom.height
        return (geom.width, geom.height)

    def set_size(self, size, update=True):
        """Set the window size.
        :size: list or tuple: the new size.
        Raises a TypeError if something else than a list or a tuple is sent."""
        if type(size) in (list, tuple):
            # Call the Xlib object handling the size to update it.
            if DEBUG_WM:
                print "Setting size to", size
                print "actual size", self.get_size()
            self.sizeSetter.configure(width=size[0], height=size[1])
            if update:
                self.sync()
        else:
            # Raise a Type error.
            raise TypeError, "%s is not a list or a tuple." % size

    def get_position(self):
        """Return the window actual position as a tuple."""
        geom = self.positionGetter.get_geometry()
        x, y = geom.x, geom.y
#         if DEBUG_WM:
#             print "Actual position is", x, y
        return (x, y)

    def set_position(self, pos, update=True):
        """Set the window position.
        :pos: list or tuple: the new position (x, y).
        :update: bool: wheteher to call the internal sync method."""
        if DEBUG_WM:
            print "Setting position to", pos
        if type(pos) in (list, tuple):
            gx, gy = 0 or self.gx, 0 or self.gy
            if self.starting:
                gx, gy = self.position_gap[:2]
                if self.position_gap[2]:
                    self.gx = gx
                if self.position_gap[3]:
                    self.gy = gy
                self.starting = False
            # Call the Xlib object handling the position to update it.
            self.positionSetter.configure(x=pos[0] + gx, y=pos[1] + gy)
            if update:
                self.sync()
        else:
            # Raise a Type error.
            raise TypeError, "%s is not a list or a tuple." % pos

    def get_state(self):
        """Return wheter the window is maximized or not, or minimized or full screen."""
        state = self.stateHandler.get_full_property(self.display.intern_atom("_NET_WM_STATE"), 4)
#         if DEBUG_WM:
#             print "state_1.value", state.value
#             print "max vert", self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT") ,self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT") in state.value
#             print "max horz", self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ"), self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ") in state.value
        if self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ") in state.value and self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT") in state.value:
#             if DEBUG_WM:
#                 print MAXIMIZED
            return MAXIMIZED
        elif self.display.intern_atom("_NET_WM_STATE_HIDEN") in state.value:
#             if DEBUG_WM:
#                 print MINIMIZED
            return MINIMIZED
        elif self.display.intern_atom("_NET_WM_STATE_FULLSCREEN") in state.value:
#             if DEBUG_WM:
#                 print FULLSCREEN
            return FULLSCREEN
#         if DEBUG_WM:
#             print NORMAL
        return NORMAL

    def set_state(self, state=NORMAL, size=(-1, -1), pos=(-1, -1), update=True):
        """Set wheter the window is maximized or not, or minimized or full screen.
        If no argument is given, assume the state will be windowed and not maximized.
        If arguments are given, only the first is relevant. The other ones are ignored.

        ** Only maximized and normal states are implemented for now. **

        :state: valid arguments:
        'minimized', MINIMIZED, 0.
        'normal', NORMAL, 1: windowed, not maximized.
        'maximized', MAXIMIZED, 2.
        'fullscreen, FULLSCREEN, 3.

        :size: list, tuple: the new size; if (-1, -1) self.get_size() is used.
               If one element is -1 it is replaced by the corresponding valur from self.get_size().
        :pos: list, tuple: the new position; if (-1, -1), self.get_position is used.
              If one element is -1 it is replaced by the corresponding valur from self.get_position().
        :update: bool: whether to call the internal flush method."""
        if state not in (0, MINIMIZED, 'minimized', 1, NORMAL, 'normal', 2, MAXIMIZED, 'maximized', 3, FULLSCREEN, 'fullscreen'):
            # Raise a value error.
            raise ValueError, "Invalid state argument: %s is not a correct value" % state
        if type(size) not in (list, tuple):
            raise TypeError, "Invalid size argument: %s is not a list or a tuple."
        if type(pos) not in (list, tuple):
            raise TypeError, "Invalid pos argument: %s is not a list or a tuple."

        if state in (1, NORMAL, 'normal'):
            size = list(size)
            sz = self.get_size()
            if size[0] == -1:
                size[0] = sz[0]
            if size[1] == -1:
                size[1] = sz[1]
            pos = list(pos)
            ps = self.get_position()
            if pos[0] == -1:
                pos[0] = ps[0]
            if pos[1] == -1:
                pos[1] = ps[1]
            self.set_mode(size, self.mode)
            self.set_position(pos)
        elif state in (0, MINIMIZED, 'minimized'):
            pass
        elif state in (2, MAXIMIZED, 'maximized'):
            data = [1, self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT", False), self.display.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ", False)]
            data = (data + ([0] * (5 - len(data))))[:5]
            if DEBUG_WM:
                print self.stateHandler.get_wm_state()
                print "creating event", Xlib.protocol.event.ClientMessage
                print dir(self.stateHandler)
            x_event = Xlib.protocol.event.ClientMessage(window=self.stateHandler, client_type=self.display.intern_atom("_NET_WM_STATE", False), data=(32, (data)))
            if DEBUG_WM:
                print "sending event"
            self.display.screen().root.send_event(x_event, event_mask=Xlib.X.SubstructureRedirectMask)

            if DEBUG_WM:
                print self.stateHandler.get_wm_state()
        elif state in (3, FULLSCREEN, 'fullscreen'):
            pass
        if update:
            self.flush()

    def flush(self):
        """Wrapper around Xlib.Display.flush()"""
        if DEBUG_WM:
            print "* flushing display"
        self.display.flush()

    def sync(self):
        """Wrapper around Xlib.Display.sync()"""
        if DEBUG_WM:
            print "* syncing display"
        self.display.sync()


#=======================================================================
# WARNING: This class has been built on Linux using wine.
# Please review this code and change it consequently before using it without '--debug-wm' switch!
class WWindowHandler(BaseWindowHandler):
    """Object to deal with Microsoft Window managers."""
    desk_env = desktop_environment
    def __init__(self, pos=(0, 0), size=(0, 0), mode=None):
        """Set up the internal handlers."""
        BaseWindowHandler.__init__(self, pos=pos, size=size, mode=mode)
        # Tests
        if DEBUG_WM:
            print "#" * 72
            print "WWindowHandler.__init__"
            print "Desktop environment:", desktop_environment
            for item in dir(win32con):
                if 'maxim' in item.lower() or 'minim' in item.lower() or 'full' in item.lower():
                    print item, getattr(win32con, item)
        self.base_handler = display
        self.base_handler_id = display.get_wm_info()['window']

    if platform.dist() == ('', '', ''):
        # We're running on a native Windows.
        def set_mode(self, size, mode):
            """Wrapper for pygame.display.set_mode()."""
            # Windows pygame implementation seem to work on the display mode and size on it's own...
            return
    else:
        # We're running on wine.
        def set_mode(self, size, mode):
            """Wrapper for pygame.display.set_mode()."""
            if getattr(self, 'wine_state_fix', False):
                self.set_size(size)
                self.wine_state_fix = True
            else:
                self.wine_state_fix = False

    def get_root_rect(self):
        """Return a four values tuple containing the position and size of the very first OS window object."""
        flags, showCmd, ptMin, ptMax, rect = win32gui.GetWindowPlacement(win32gui.GetDesktopWindow())
        return rect

    def get_size(self):
        """Return the window actual size as a tuple (width, height)."""
        flags, showCmd, ptMin, ptMax, rect = win32gui.GetWindowPlacement(self.base_handler_id)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        return (w, h)

    def set_size(self, size, update=True):
        """Set the window size.
        :size: list or tuple: the new size.
        :mode: bool: (re)set the pygame.display mode; self.mode must be a pygame display mode object.
        Raises a TypeError if something else than a list or a tuple is sent."""
        if type(size) in (list, tuple):
            w, h = size
            cx, cy = win32gui.GetCursorPos()
            if DEBUG_WM:
                print "Settin size to", size
                print "actual size", self.get_size()
                print "actual position", self.get_position()
                
                print 'cursor pos', cx, cy
            flags, showCmd, ptMin, ptMax, rect = win32gui.GetWindowPlacement(self.base_handler_id)
            if DEBUG_WM:
                print "set_size rect", rect, "ptMin", ptMin, "ptMax", ptMax, "flags", flags
            x = rect[0]
            y = rect[1]
            rect = (x, y, x + w, y + h)
            win32gui.SetWindowPlacement(self.base_handler_id, (0, showCmd, ptMin, ptMax, rect))
        else:
            # Raise a Type error.
            raise TypeError, "%s is not a list or a tuple." % repr(size)

    def get_position(self):
        """Return the window actual position as a tuple."""
        (flags, showCmd, ptMin, ptMax, rect) = win32gui.GetWindowPlacement(self.base_handler_id)
        x, y, r, b = rect
        return (x, y)

    def set_position(self, pos, update=True):
        """Set the window position.
        :pos: list or tuple: the new position (x, y)."""
        if DEBUG_WM:
            print "Setting position to", pos
        if type(pos) in (list, tuple):
            self.first_pos = False
            x, y = pos
            if update:
                flags, showCmd, ptMin, ptMax, rect = win32gui.GetWindowPlacement(self.base_handler_id)
                if DEBUG_WM:
                    print "set_position rect", rect, "ptMin", ptMin, "ptMax", ptMax
                realW = rect[2] - rect[0]
                realH = rect[3] - rect[1]
                if DEBUG_WM:
                    print 'rect[0]', rect[0], 'rect[1]', rect[1]
                    print 'realW', realW, 'realH', realH
                    print 'cursor pos', win32gui.GetCursorPos()

                rect = (x, y, x + realW, y + realH)

                win32gui.SetWindowPlacement(self.base_handler_id, (0, showCmd, ptMin, ptMax, rect))
        else:
            # Raise a Type error.
            raise TypeError, "%s is not a list or a tuple." % repr(pos)

    def get_state(self):
        """Return wheter the window is maximized or not, or minimized or full screen."""
        flags, state, ptMin, ptMax, rect = win32gui.GetWindowPlacement(self.base_handler_id)
        if DEBUG_WM:
            print "state", state
        if state == win32con.SW_MAXIMIZE:
            return MAXIMIZED
        elif state == win32con.SW_MINIMIZE:
            return MINIMIZED
        return NORMAL

    def set_state(self, state=NORMAL, size=(-1, -1), pos=(-1, -1), update=True):
        """Set wheter the window is maximized or not, or minimized or full screen.
        If no argument is given, assume the state will be windowed and not maximized.
        If arguments are given, only the first is relevant. The other ones are ignored.

        ** Only maximized and normal states are implemented for now. **

        :state: valid arguments:
        'minimized', MINIMIZED, 0.
        'normal', NORMAL, 1: windowed, not maximized.
        'maximized', MAXIMIZED, 2.
        'fullscreen, FULLSCREEN, 3.

        :size: list, tuple: the new size; if (-1, -1) self.get_size() is used.
               If one element is -1 it is replaced by the corresponding valur from self.get_size().
        :pos: list, tuple: the new position; if (-1, -1), self.get_position is used.
              If one element is -1 it is replaced by the corresponding valur from self.get_position().
        :update: bool: whether to call the internal flush method."""
        if state not in (0, MINIMIZED, 'minimized', 1, NORMAL, 'normal', 2, MAXIMIZED, 'maximized', 3, FULLSCREEN, 'fullscreen'):
            # Raise a value error.
            raise ValueError, "Invalid state argument: %s is not a correct value" % state
        if type(size) not in (list, tuple):
            raise TypeError, "Invalid size argument: %s is not a list or a tuple."
        if type(pos) not in (list, tuple):
            raise TypeError, "Invalid pos argument: %s is not a list or a tuple."

        if state in (1, NORMAL, 'normal'):
            size = list(size)
            sz = self.get_size()
            if size[0] == -1:
                size[0] = sz[0]
            if size[1] == -1:
                size[1] = sz[1]
            pos = list(pos)
            ps = self.get_position()
            if pos[0] == -1:
                pos[0] = ps[0]
            if pos[1] == -1:
                pos[1] = ps[1]
            self.set_mode(size, self.mode)
            self.set_position(pos)
        elif state in (0, MINIMIZED, 'minimized'):
            pass
        elif state in (2, MAXIMIZED, 'maximized'):
            win32gui.ShowWindow(self.base_handler_id, win32con.SW_MAXIMIZE)
        elif state in (3, FULLSCREEN, 'fullscreen'):
            pass




WindowHandler = None

def setupWindowHandler():
    """'Link' the corresponding window handler class to WindowHandler."""
    # Don't initialize the window handler here.
    # We need MCEdit display objects to get the right object.
    global WindowHandler
    if USE_WM:
        log.warn("Initializing window management...")
        if sys.platform == 'linux2':
            if XWindowHandler.desk_env == 'unknown':
                log.warning("Your desktop environment could not be determined. The support for window sizing/moving is not availble.")
            elif XWindowHandler.desk_env in linux_unsuported:
                log.warning("Your desktop environment is not yet supported for window sizing/moving.")
            else:
                WindowHandler = XWindowHandler
                log.info("XWindowHandler initialized.")
        elif sys.platform == 'win32':
            WindowHandler = WWindowHandler
            log.info("WWindowHandler initialized.")
    return WindowHandler

# setupWindowHandler()
