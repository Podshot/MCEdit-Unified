# !/usr/bin/env python2.7
# -*- coding: utf_8 -*-
# import resource_packs # not the right place, moving it a bit further

#-# Modified by D.C.-G. for translation purpose

"""
mcedit.py

Startup, main menu, keyboard configuration, automatic updating.
"""
import resource_packs
import OpenGL
import sys
import os
import directories
import keys

if "-debug" not in sys.argv:
    OpenGL.ERROR_CHECKING = False

import logging

# Setup file and stderr logging.
logger = logging.getLogger()

# Set the log level up while importing OpenGL.GL to hide some obnoxious warnings about old array handlers
logger.setLevel(logging.WARN)
from OpenGL import GL

logger.setLevel(logging.DEBUG)

logfile = 'mcedit.log'

# if hasattr(sys, 'frozen'):
#     if sys.platform == "win32":
#         import esky
#         app = esky.Esky(sys.executable)

#         logfile = os.path.join(app.appdir, logfile)
#
if sys.platform == "darwin":
    logfile = os.path.expanduser("~/Library/Logs/mcedit.log")
fh = logging.FileHandler(logfile, mode="w")
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.WARN)

if "-v" in sys.argv:
    ch.setLevel(logging.INFO)
if "-vv" in sys.argv:
    ch.setLevel(logging.DEBUG)


class FileLineFormatter(logging.Formatter):
    def format(self, record):
        record.__dict__['fileline'] = "%(module)s.py:%(lineno)d" % record.__dict__
        record.__dict__['nameline'] = "%(name)s.py:%(lineno)d" % record.__dict__
        return super(FileLineFormatter, self).format(record)


fmt = FileLineFormatter(
    '[%(levelname)8s][%(nameline)30s]:%(message)s'
)
fh.setFormatter(fmt)
ch.setFormatter(fmt)

logger.addHandler(fh)
logger.addHandler(ch)

import albow
import locale
DEF_ENC = locale.getdefaultlocale()[1]
if DEF_ENC is None:
    DEF_ENC = "UTF-8"
from albow.translate import _, getPlatInfo

from albow.dialogs import Dialog
from albow.openglwidgets import GLViewport
from albow.root import RootWidget

from config import config

albow.resource.resource_dir = directories.getDataDir()

import panels
import functools
import glutils
import leveleditor

# Building translation template
if "-tt" in sys.argv:
    albow.translate.buildTemplate = True
    albow.translate.loadTemplate()


import mceutils
import mcplatform
from mcplatform import platform_open
import numpy
from pymclevel.minecraft_server import ServerJarStorage

import os
import os.path
import pygame
from pygame import display, rect
import pymclevel
import release
import shutil
import sys
import traceback
import threading

from utilities.gl_display_context import GLDisplayContext

getPlatInfo(OpenGL=OpenGL, numpy=numpy, pygame=pygame)

ESCAPE = '\033'


class MCEdit(GLViewport):
    #debug_resize = True

    def __init__(self, displayContext, *args):
        ws = displayContext.getWindowSize()
        r = rect.Rect(0, 0, ws[0], ws[1])
        GLViewport.__init__(self, r)
        self.displayContext = displayContext
        self.bg_color = (0, 0, 0, 1)
        self.anchor = 'tlbr'

        if not config.config.has_section("Recent Worlds"):
            config.config.add_section("Recent Worlds")
            self.setRecentWorlds([""] * 5)

        self.optionsPanel = panels.OptionsPanel(self)
        if not albow.translate.buildTemplate:
            self.optionsPanel.getLanguageChoices()
            lng = config.settings.langCode.get()
            if lng not in self.optionsPanel.sgnal:
                lng = "en_US"
                config.settings.langCode.set(lng)
            albow.translate.setLang(lng)
        self.optionsPanel.initComponents()
        self.graphicsPanel = panels.GraphicsPanel(self)

        self.keyConfigPanel = keys.KeyConfigPanel()

        self.droppedLevel = None
        self.reloadEditor()

        """
        check command line for files dropped from explorer
        """
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                f = arg.decode(sys.getfilesystemencoding())
                if os.path.isdir(os.path.join(pymclevel.minecraftSaveFileDir, f)):
                    f = os.path.join(pymclevel.minecraftSaveFileDir, f)
                    self.droppedLevel = f
                    break
                if os.path.exists(f):
                    self.droppedLevel = f
                    break

        self.fileOpener = albow.FileOpener(self)
        self.add(self.fileOpener)

        self.fileOpener.focus()

        #-# LINUX resize and placement debug
#        if sys.platform == 'linux2':
#            print display.get_wm_info()
##            dis = display.get_wm_info()['display']
#            win = display.get_wm_info()['window']
#            print win
#            import Xlib.display
#            dis = Xlib.display.Display()
#            win = dis.create_resource_object('window', win)
#            print dir(win)
#            print win.get_attributes()
#            print win.get_geometry()
#            wmClass = win.get_wm_class()
#            print dir(dis)
#            wParent = win.query_tree().parent
#            print wParent.get_geometry()
#            print self.root.size
#            razear
#            import Xlib.protocol.request
#            winAttributes = Xlib.protocol.request.GetWindowAttributes(dis, 0, win)
#            print winAttributes
#            print mcplatform.gtk.window_list_toplevels()

    editor = None

    def reloadEditor(self):
        reload(leveleditor)
        level = None

        pos = None

        if self.editor:
            level = self.editor.level
            self.remove(self.editor)
            c = self.editor.mainViewport
            pos, yaw, pitch = c.position, c.yaw, c.pitch

        self.editor = leveleditor.LevelEditor(self)
        self.editor.anchor = 'tlbr'
        if level:
            self.add(self.editor)
            self.editor.gotoLevel(level)
            self.focus_switch = self.editor

            if pos is not None:
                c = self.editor.mainViewport

                c.position, c.yaw, c.pitch = pos, yaw, pitch

    def add_right(self, widget):
        w, h = self.size
        widget.centery = h // 2
        widget.right = w
        self.add(widget)

    def showOptions(self):
        self.optionsPanel.present()

    def showGraphicOptions(self):
        self.graphicsPanel.present()

    def showKeyConfig(self):
        self.keyConfigPanel.presentControls()

    def loadRecentWorldNumber(self, i):
        worlds = list(self.recentWorlds())
        if i - 1 < len(worlds):
            self.loadFile(worlds[i - 1])

    numRecentWorlds = 5

    def removeLevelDat(self, filename):
        if filename.endswith("level.dat"):
            filename = os.path.dirname(filename)
        return filename

    def recentWorlds(self):
        worlds = []
        for i in range(self.numRecentWorlds):
            if config.config.has_option("Recent Worlds", str(i)):
                try:
                    filename = (config.config.get("Recent Worlds", str(i)).decode('utf-8'))
                    worlds.append(self.removeLevelDat(filename))
                except Exception, e:
                    logging.error(repr(e))

        return list((f for f in worlds if f and os.path.exists(f)))

    def addRecentWorld(self, filename):
        filename = self.removeLevelDat(filename)
        rw = list(self.recentWorlds())
        if filename in rw:
            return
        rw = [filename] + rw[:self.numRecentWorlds - 1]
        self.setRecentWorlds(rw)

    def setRecentWorlds(self, worlds):
        for i, filename in enumerate(worlds):
            config.config.set("Recent Worlds", str(i), filename.encode('utf-8'))

    def makeSideColumn(self):
        def showLicense():
            platform_open(os.path.join(directories.getDataDir(), "LICENSE.txt"))
        def showCacheDir():
            platform_open(directories.getCacheDir())

        def showScreenshotsDir():
            platform_open(os.path.join(directories.parentDir, "screenshots"))

        readmePath = os.path.join(directories.getDataDir(), "README.html")

        hotkeys = ([("",
                     "Controls",
                     self.showKeyConfig),
                    ("",
                     "Graphics",
                     self.showGraphicOptions),
                    ("",
                     "Options",
                     self.showOptions),
                    ("",
                     "Homepage",
                     lambda: platform_open("http://khroki.github.io/MCEdit-Unified")),
                    ("",
                     "About MCEdit",
                     lambda: platform_open("http://khroki.github.io/MCEdit-Unified/about.html")),
                    ("",
                     "Recent Changes",
                     lambda: platform_open("http://khroki.github.io/MCEdit-Unified")),
                    ("",
                     "License",
                     showLicense),
                    ("",
                     "Config Files Folder",
                     showCacheDir),
                    ("",
                     "Screenshots Folder",
                     showScreenshotsDir)
                   ])

        c = mceutils.HotkeyColumn(hotkeys)

        return c

    def resized(self, dw, dh):
        """
        Handle window resizing events.
        """
        GLViewport.resized(self, dw, dh)

        (w, h) = self.size
        if w == 0 and h == 0:
            # The window has been minimized, no need to draw anything.
            self.editor.renderer.render = False
            return

        if not self.editor.renderer.render:
            self.editor.renderer.render = True

        dis = None
        if sys.platform == 'linux2' and mcplatform.hasXlibDisplay:
            dis = mcplatform.Xlib.display.Display()
            win = dis.create_resource_object('window', display.get_wm_info()['window'])
            geom = win.query_tree().parent.get_geometry()

        if w >= 1000 and h >= 700:
            config.settings.windowWidth.set(w)
            config.settings.windowHeight.set(h)
            config.save()
            if dis:
                win.configure(height=geom.height, width=geom.width)
        elif w !=0 and h !=0:
            config.settings.windowWidth.set(1000)
            config.settings.windowHeight.set(700)
            config.save()
            if dis:
                win.configure(height=700, width=1000)
        if dw > 20 or dh > 20:
            if not hasattr(self, 'resizeAlert'):
                self.resizeAlert = self.shouldResizeAlert
            if self.resizeAlert:
                albow.alert(
                    "Window size increased. You may have problems using the cursor until MCEdit is restarted.")
                self.resizeAlert = False
        if dis:
            dis.sync()

    shouldResizeAlert = config.settings.shouldResizeAlert.property()

    def loadFile(self, filename):
        if os.path.exists(filename):
            try:
                self.editor.loadFile(filename)
            except Exception, e:
                logging.error(u'Failed to load file {0}: {1!r}'.format(
                    filename, e))
                return None

            self.remove(self.fileOpener)
            self.fileOpener = None
            if self.editor.level:
                self.editor.size = self.size
                self.add(self.editor)
                self.focus_switch = self.editor

    def createNewWorld(self):
        level = self.editor.createNewLevel()
        if level:
            self.remove(self.fileOpener)
            self.editor.size = self.size

            self.add(self.editor)

            self.focus_switch = self.editor
            albow.alert(
                "World created. To expand this infinite world, explore the world in Minecraft or use the Chunk Control tool to add or delete chunks.")

    def removeEditor(self):
        self.remove(self.editor)
        self.fileOpener = albow.FileOpener(self)
        self.add(self.fileOpener)
        self.focus_switch = self.fileOpener

    def confirm_quit(self):
        #-# saving language template
        if hasattr(albow.translate, "saveTemplate"):
            albow.translate.saveTemplate()
        #-#
        self.saveWindowPosition()
        config.save()
        if self.editor.unsavedEdits:
            result = albow.ask(_("There are {0} unsaved changes.").format(self.editor.unsavedEdits),
                               responses=["Save and Quit", "Quit", "Cancel"])
            if result == "Save and Quit":
                self.saveAndQuit()
            elif result == "Quit":
                self.justQuit()
            elif result == "Cancel":
                return False
        else:
            raise SystemExit

    def saveAndQuit(self):
        self.editor.saveFile()
        raise SystemExit

    def justQuit(self):
        raise SystemExit

    @classmethod
    def fetch_version(self):
        with self.version_lock:
            self.version_info = release.fetch_new_version_info()

    def check_for_version(self):
        new_version = release.check_for_new_version(self.version_info)
        if new_version is not False:
            answer = albow.ask(
                _('Version {} is available').format(new_version["tag_name"]),
                [
                    'Download',
                    'View',
                    'Ignore'
                ],
                default=1,
                cancel=2
            )
            if answer == "View":
                platform_open(new_version["html_url"])
            elif answer == "Download":
                platform_open(new_version["asset"]["browser_download_url"])
                albow.alert(_(' {} should now be downloading via your browser. You will still need to extract the downloaded file to use the updated version.').format(new_version["asset"]["name"]))

    @classmethod
    def main(self):
        displayContext = GLDisplayContext()

        rootwidget = RootWidget(displayContext.display)
        mcedit = MCEdit(displayContext)
        rootwidget.displayContext = displayContext
        rootwidget.confirm_quit = mcedit.confirm_quit
        rootwidget.mcedit = mcedit

        rootwidget.add(mcedit)
        rootwidget.focus_switch = mcedit
        if 0 == len(pymclevel.alphaMaterials.yamlDatas):
            albow.alert("Failed to load minecraft.yaml. Check the console window for details.")

        if mcedit.droppedLevel:
            mcedit.loadFile(mcedit.droppedLevel)

        self.version_lock = threading.Lock()
        self.version_info = None
        self.version_checked = False

        fetch_version_thread = threading.Thread(target=self.fetch_version)
        fetch_version_thread.start()


# Disabled old update code
#       if hasattr(sys, 'frozen'):
#           # We're being run from a bundle, check for updates.
#           import esky
#
#           app = esky.Esky(
#               sys.executable.decode(sys.getfilesystemencoding()),
#               'https://bitbucket.org/codewarrior0/mcedit/downloads'
#           )
#           try:
#               update_version = app.find_update()
#           except:
#               # FIXME: Horrible, hacky kludge.
#               update_version = None
#               logging.exception('Error while checking for updates')
#
#           if update_version:
#               answer = albow.ask(
#                   'Version "%s" is available, would you like to '
#                   'download it?' % update_version,
#                   [
#                       'Yes',
#                       'No',
#                   ],
#                   default=0,
#                   cancel=1
#               )
#               if answer == 'Yes':
#                   def callback(args):
#                       status = args['status']
#                       status_texts = {
#                           'searching': u"Finding updates...",
#                           'found':  u"Found version {new_version}",
#                           'downloading': u"Downloading: {received} / {size}",
#                           'ready': u"Downloaded {path}",
#                           'installing': u"Installing {new_version}",
#                           'cleaning up': u"Cleaning up...",
#                           'done': u"Done."
#                       }
#                       text = status_texts.get(status, 'Unknown').format(**args)
#
#                       panel = Dialog()
#                       panel.idleevent = lambda event: panel.dismiss()
#                       label = albow.Label(text, width=600)
#                       panel.add(label)
#                       panel.size = (500, 250)
#                       panel.present()
#
#                   try:
#                       app.auto_update(callback)
#                   except (esky.EskyVersionError, EnvironmentError):
#                       albow.alert(_("Failed to install update %s") % update_version)
#                   else:
#                       albow.alert(_("Version %s installed. Restart MCEdit to begin using it.") % update_version)
#                       raise SystemExit()

        if config.settings.closeMinecraftWarning.get():
            answer = albow.ask(
                "Warning: Only open a world in one program at a time. If you open a world at the same time in MCEdit and in Minecraft, you will lose your work and possibly damage your save file.\n\n If you are using Minecraft 1.3 or earlier, you need to close Minecraft completely before you use MCEdit.",
                ["Don't remind me again.", "OK"], default=1, cancel=1)
            if answer == "Don't remind me again.":
                config.settings.closeMinecraftWarning.set(False)

# Disabled Crash Reporting Option
#       if not config.settings.reportCrashesAsked.get():
#           answer = albow.ask(
#               "When an error occurs, MCEdit can report the details of the error to its developers. "
#               "The error report will include your operating system version, MCEdit version, "
#               "OpenGL version, plus the make and model of your CPU and graphics processor. No personal "
#               "information will be collected.\n\n"
#               "Error reporting can be enabled or disabled in the Options dialog.\n\n"
#               "Enable error reporting?",
#               ["Yes", "No"],
#               default=0)
#           config.settings.reportCrashes.set(answer == "Yes")
#           config.settings.reportCrashesAsked.set(True)
        config.settings.reportCrashes.set(False)
        config.settings.reportCrashesAsked.set(True)

        config.save()
        if "update" in config.version.version.get():
            answer = albow.ask("There are new default controls. Do you want to replace your current controls with the new ones?", ["Yes", "No"])
            if answer == "Yes":
                for configKey, k in keys.KeyConfigPanel.presets["WASD"]:
                    config.keys[config.convert(configKey)].set(k)
        config.version.version.set("1.1.2.0")
        config.save()
        if "-causeError" in sys.argv:
            raise ValueError, "Error requested via -causeError"

        while True:
            try:
                rootwidget.run()
            except SystemExit:
                if sys.platform == "win32" and config.settings.setWindowPlacement.get():
                    (flags, showCmd, ptMin, ptMax, rect) = mcplatform.win32gui.GetWindowPlacement(
                        display.get_wm_info()['window'])
                    X, Y, r, b = rect
                    #w = r-X
                    #h = b-Y
                    if (showCmd == mcplatform.win32con.SW_MINIMIZE or
                                showCmd == mcplatform.win32con.SW_SHOWMINIMIZED):
                        showCmd = mcplatform.win32con.SW_SHOWNORMAL

                    config.settings.windowX.set(X)
                    config.settings.windowY.set(Y)
                    config.settings.windowShowCmd.set(showCmd)

                config.save()
                mcedit.editor.renderer.discardAllChunks()
                mcedit.editor.deleteAllCopiedSchematics()
                raise
            except MemoryError:
                traceback.print_exc()
                mcedit.editor.handleMemoryError()

    def saveWindowPosition(self):
        """Save the window position in the configuration handler."""
        if sys.platform == "win32" and config.settings.setWindowPlacement.get():
            (flags, showCmd, ptMin, ptMax, rect) = mcplatform.win32gui.GetWindowPlacement(
                display.get_wm_info()['window'])
            X, Y, r, b = rect
            #w = r-X
            #h = b-Y
            if (showCmd == mcplatform.win32con.SW_MINIMIZE or
                        showCmd == mcplatform.win32con.SW_SHOWMINIMIZED):
                showCmd = mcplatform.win32con.SW_SHOWNORMAL

            config.settings.windowX.set(X)
            config.settings.windowY.set(Y)
            config.settings.windowShowCmd.set(showCmd)
        elif sys.platform == 'linux2' and mcplatform.hasXlibDisplay:
            win = display.get_wm_info()['window']
            dis = mcplatform.Xlib.display.Display()
            win = dis.create_resource_object('window', win)
            curDesk = os.environ.get('XDG_CURRENT_DESKTOP')
            if curDesk in ('GNOME', 'X-Cinnamon'):
                wParent = win.query_tree().parent.query_tree().parent
            elif curDesk == 'KDE':
                wParent = win.query_tree().parent.query_tree().parent.query_tree().parent
            if wParent:
                geom = wParent.get_geometry()
                config.settings.windowX.set(geom.x)
                config.settings.windowY.set(geom.y)

    def restart(self):
        self.saveWindowPosition()
        config.save()
        self.editor.renderer.discardAllChunks()
        self.editor.deleteAllCopiedSchematics()
        python = sys.executable
        if sys.argv[0].endswith('.exe') or hasattr(sys, 'frozen'):
            os.execl(python, python, * sys.argv[1:])
        else:
            os.execl(python, python, * sys.argv)

def main(argv):
    """
    Setup display, bundled schematics. Handle unclean
    shutdowns.
    """

# This should eventually be revived, what is "squash_python"?
#    try:
#        import squash_python
#
#        squash_python.uploader.SquashUploader.headers.pop("Content-encoding", None)
#        squash_python.uploader.SquashUploader.headers.pop("Accept-encoding", None)
#
#        version = release.get_version()
#        client = squash_python.get_client()
#        client.APIKey = "6ea52b17-ac76-4fd8-8db4-2d7303473ca2"
#        client.environment = "unknown"
#        client.host = "http://pixelhost.ezekielelin.com"
#        client.notifyPath = "/mcedit_bugs.php"
#        client.build = version
#        client.timeout = 5
#
# Disabled Crash Reporting Option
#       client.disabled = not config.settings.reportCrashesNew.get()
#       client.disabled = True
#
#       def _reportingChanged(val):
#           client.disabled = not val
#
#       config.settings.reportCrashes.addObserver(client, '_enabled', _reportingChanged)
#       client.reportErrors()
#       client.hook()
#   except (ImportError, UnicodeError) as e:
#       pass

    try:
        display.init()
    except pygame.error, e:
        os.environ['SDL_VIDEODRIVER'] = 'directx'
        try:
            display.init()
        except pygame.error:
            os.environ['SDL_VIDEODRIVER'] = 'windib'
            display.init()

    pygame.font.init()

    try:
        if not os.path.exists(directories.schematicsDir):
            shutil.copytree(
                os.path.join(directories.getDataDir(), u'stock-schematics'),
                directories.schematicsDir
            )
    except Exception, e:
        logging.warning('Error copying bundled schematics: {0!r}'.format(e))
        try:
            os.mkdir(directories.schematicsDir)
        except Exception, e:
            logging.warning('Error creating schematics folder: {0!r}'.format(e))

    try:
        if not os.path.exists(directories.brushesDir):
            shutil.copytree(
                os.path.join(directories.getDataDir(), u'Brushes'),
                directories.brushesDir
            )
    except Exception, e:
        logging.warning('Error copying bundled Brushes: {0!r}'.format(e))
        try:
            os.mkdir(directories.brushesDir)
        except Exception, e:
            logging.warning('Error creating Brushes folder: {0!r}'.format(e))

    try:
        if not os.path.exists(directories.filtersDir):
            shutil.copytree(
                os.path.join(directories.getDataDir(), u'stock-filters'),
                directories.filtersDir
            )
        else:
            # Start hashing the filter dir
            mceutils.compareMD5Hashes(directories.getAllOfAFile(directories.filtersDir, ".py"))
    except Exception, e:
        logging.warning('Error copying bundled filters: {0!r}'.format(e))
        try:
            os.mkdir(directories.filtersDir)
        except Exception, e:
            logging.warning('Error creating filters folder: {0!r}'.format(e))

    if directories.filtersDir not in [s.decode(sys.getfilesystemencoding())
                          if isinstance(s, str)
                          else s
                          for s in sys.path]:
        sys.path.append(directories.filtersDir.encode(sys.getfilesystemencoding()))

    try:
        ServerJarStorage()
    except Exception, e:
        logging.warning('Error creating server jar storage folder: {0!r}'.format(e))

    try:
        MCEdit.main()
    except Exception as e:
        logging.error("MCEdit version %s", release.get_version())
        display.quit()
        if hasattr(sys, 'frozen') and sys.platform == 'win32':
            logging.exception("%s", e)
            print "Press RETURN or close this window to dismiss."
            raw_input()

        raise

    return 0


def getSelectedMinecraftVersion():
    profile = directories.getMinecraftProfileJSON()[directories.getSelectedProfile()]
    if 'lastVersionId' in profile:
        return profile['lastVersionId']
    else:
        return '1.8'

def getLatestMinecraftVersion(snapshots=False):
    import urllib2
    import json
    versioninfo = json.loads(urllib2.urlopen("http://s3.amazonaws.com/Minecraft.Download/versions/versions.json ").read())
    if snapshots:
        return versioninfo['latest']['snapshot']
    else:
        return versioninfo['latest']['release']

def weird_fix():
    try:
        from OpenGL.platform import win32

        win32
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main(sys.argv))
