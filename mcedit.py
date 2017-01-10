# !/usr/bin/env python2.7
# -*- coding: utf_8 -*-
# import resource_packs # not the right place, moving it a bit further

#-# Modified by D.C.-G. for translation purpose
#.# Marks the layout modifications. -- D.C.-G.

"""
mcedit.py

Startup, main menu, keyboard configuration, automatic updating.
"""
import splash
import OpenGL
import sys
import os

if "--debug-ogl" not in sys.argv:
    OpenGL.ERROR_CHECKING = False

import logging

# Setup file and stderr logging.
logger = logging.getLogger()

# Set the log level up while importing OpenGL.GL to hide some obnoxious warnings about old array handlers
logger.setLevel(logging.WARN)
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
else:
    logfile = os.path.join(os.getcwdu(), logfile)
fh = logging.FileHandler(logfile, mode="w")
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.WARN)

if "--log-info" in sys.argv:
    ch.setLevel(logging.INFO)
if "--log-debug" in sys.argv:
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
import release
start_msg = 'Starting MCEdit-Unified v%s'%release.TAG
logger.info(start_msg)
print '[ ****** ] ~~~~~~~~~~ %s'%start_msg

#---------------------------------------------------------------------
# NEW FEATURES HANDLING
#
# The idea is to be able to implement and test/use new code without stripping off the current one.
# These features/new code will be in the released stuff, but unavailable until explicitly requested.
#
# The new features which are under development can be enabled using the 'new_features.def' file.
# This file is a plain text file with one feature to enable a line.
# The file is parsed and each feature is added to the builtins using the pattern 'mcenf_<feature>'.
# The value for these builtins is 'True'.
# Then, in the code, just check if the builtins has the key 'mcenf_<feature>' to use the new version of the code: 
#
# ```
# def foo_old():
#     # Was 'foo', code here is the one used unless the new version is wanted.
#     [...]
#
# def foo_new():
#     # This is the new version of the former 'foo' (current 'foo_old').
#     [...]
#
# if __builtins__.get('mcenf_foo', False):
#     foo = foo_new
# else:
#     foo = foo_old
#
# ```
#
if '--new-features' in sys.argv:
    if not os.path.exists('new_features.def'):
        logger.warn("New features requested, but file 'new_features.def' not found!")
    else:
        logger.warn("New features mode requested.")
        lines = [a.strip() for a in open('new_features.def', 'r').readlines()]
        for line in lines:
            setattr(__builtins__, 'mcenf_%s'%line, True)
        logger.warn("New features list loaded.")


from version_utils import PlayerCache
import directories
import keys

import albow
import locale
DEF_ENC = locale.getdefaultlocale()[1]
if DEF_ENC is None:
    DEF_ENC = "UTF-8"
from albow.translate import _, getPlatInfo

from albow.openglwidgets import GLViewport
from albow.root import RootWidget

from config import config

albow.resource.resource_dir = directories.getDataDir()

import panels
import leveleditor

# Building translation template
if "-tt" in sys.argv:
    sys.argv.remove('-tt')
    # Overwrite the default marker to have one adapted to our specific needs.
    albow.translate.buildTemplateMarker = """
### THE FOLLOWING LINES HAS BEEN ADDED BY THE TEMPLATE UPDATE FUNCTION.
### Please, consider to analyze them and remove the entries referring
### to ones containing string formatting.
###
### For example, if you have a line already defined with this text:
### My %{animal} has %d legs.
### you may find lines like these below:
### My parrot has 2 legs.
### My dog has 4 legs.
###
### You also may have unwanted partial strings, especially the ones 
### used in hotkeys. Delete them too. 
### And, remove this paragraph, or it will be displayed in the program...
"""
    albow.translate.buildTemplate = True
    albow.translate.loadTemplate()
    # Save the language defined in config and set en_US as current one.
    logging.warning('MCEdit is invoked to update the translation template.')
    orglang = config.settings.langCode.get()
    logging.warning('The actual language is %s.'%orglang)
    logging.warning('Setting en_US as language for this session.')
    config.settings.langCode.set('en_US')


import mceutils
import mcplatform

# The two next switches '--debug-wm' and '--no-wm' are used to debug/disable the internal window handler.
# They are exclusive. You can't debug if it is disabled.
if "--debug-wm" in sys.argv:
    mcplatform.DEBUG_WM = True
if "--no-wm" in sys.argv:
    mcplatform.DEBUG_WM = False
    mcplatform.USE_WM = False
else:
    mcplatform.setupWindowHandler()

DEBUG_WM = mcplatform.DEBUG_WM
USE_WM = mcplatform.USE_WM


#-# DEBUG
if mcplatform.hasXlibDisplay and DEBUG_WM:
    print '*** Xlib version', str(mcplatform.Xlib.__version__).replace(' ', '').replace(',', '.')[1:-1], 'found in',
    if os.path.expanduser('~/.local/lib/python2.7/site-packages') in mcplatform.Xlib.__file__:
        print 'user\'s',
    else:
        print 'system\'s',
    print 'libraries.'
#-#
from mcplatform import platform_open
import numpy
from pymclevel.minecraft_server import ServerJarStorage

import os
import os.path
import pygame
from pygame import display, rect
import pymclevel
# import release
import shutil
import sys
import traceback
import threading

from utilities.gl_display_context import GLDisplayContext

#&# Prototype fro blocks/items names
import mclangres
#&#

getPlatInfo(OpenGL=OpenGL, numpy=numpy, pygame=pygame)

ESCAPE = '\033'


class MCEdit(GLViewport):
    def_enc = DEF_ENC

    def __init__(self, displayContext, *args):
        if DEBUG_WM:
            print "############################ __INIT__ ###########################"
        self.resizeAlert = config.settings.showWindowSizeWarning.get()
        self.maximized = config.settings.windowMaximized.get()
        self.saved_pos = config.settings.windowX.get(), config.settings.windowY.get()
        if displayContext.win and DEBUG_WM:
            print "* self.displayContext.win.state", displayContext.win.get_state()
            print "* self.displayContext.win.position", displayContext.win.get_position()
            self.dis = None
            self.win = None
            self.wParent = None
            self.wGrandParent = None
            self.linux = False
            if sys.platform == 'linux2' and mcplatform.hasXlibDisplay:
                self.linux = True
                self.dis = dis = mcplatform.Xlib.display.Display()
                self.win = win = dis.create_resource_object('window', display.get_wm_info()['window'])
                curDesk = os.environ.get('XDG_CURRENT_DESKTOP')
                if curDesk in ('GNOME', 'X-Cinnamon', 'Unity'):
                    self.geomReciever = self.maximizeHandler = wParent = win.query_tree().parent
                    self.geomSender = wGrandParent = wParent.query_tree().parent
                elif curDesk == 'KDE':
                    self.maximizeHandler = win.query_tree().parent
                    wParent = win.query_tree().parent.query_tree().parent
                    wGrandParent = wParent.query_tree().parent.query_tree().parent
                    self.geomReciever = self.geomSender = win.query_tree().parent.query_tree().parent.query_tree().parent
                else:
                    self.maximizeHandler = self.geomReciever = self.geomSender = wGrandParent = wParent = None
                self.wParent = wParent
                self.wGrandParent = wGrandParent
                root = dis.screen().root
                windowID = root.get_full_property(dis.intern_atom('_NET_ACTIVE_WINDOW'), mcplatform.Xlib.X.AnyPropertyType).value[0]
                print "###\nwindowID", windowID
                window = dis.create_resource_object('window', windowID)
                print "###\nwindow.get_geometry()", window.get_geometry()
                print "###\nself.win", self.win.get_geometry()
                print "###\nself.wParent.get_geometry()", self.wParent.get_geometry()
                print "###\nself.wGrandParent.get_geometry()", self.wGrandParent.get_geometry()
                try:
                    print "###\nself.wGrandParent.query_tree().parent.get_geometry()", self.wGrandParent.query_tree().parent.get_geometry()
                except:
                    pass
                print "###\nself.maximizeHandler.get_geometry()", self.maximizeHandler.get_geometry()
                print "###\nself.geomReciever.get_geometry()", self.geomReciever.get_geometry()
                print "###\nself.geomSender.get_geometry()", self.geomSender.get_geometry()
                print "###\nself.win", self.win
                print "###\nself.wParent", self.wParent
                print "###\nself.wGrandParent", self.wGrandParent
                print "###\nself.maximizeHandler", self.maximizeHandler
                print "###\nself.geomReciever", self.geomReciever
                print "###\nself.geomSender", self.geomSender

        ws = displayContext.getWindowSize()
        r = rect.Rect(0, 0, ws[0], ws[1])
        GLViewport.__init__(self, r)
        if DEBUG_WM:
            print "self.size", self.size, "ws", ws
        if displayContext.win and self.maximized:
            # Send a maximize event now
            displayContext.win.set_state(mcplatform.MAXIMIZED)
            # Flip pygame.display to avoid to see the splash un-centered.
            pygame.display.flip()
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
        # Set the window caption here again, since the initialization is done through several steps...
        display.set_caption(('MCEdit ~ ' + release.get_version()%_("for")).encode('utf-8'), 'MCEdit')
        self.optionsPanel.initComponents()
        self.graphicsPanel = panels.GraphicsPanel(self)

        #&# Prototype for blocks/items names
        mclangres.buildResources(lang=albow.translate.getLang())
        #&#

        #.#
        self.keyConfigPanel = keys.KeyConfigPanel(self)
        #.#

        self.droppedLevel = None

        self.nbtCopyBuffer = None

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

    #-# Translation live updtate preparation
    def set_update_ui(self, v):
        GLViewport.set_update_ui(self, v)
        if v:
            #&# Prototype for blocks/items names
            mclangres.buildResources(lang=albow.translate.getLang())
            #&#
            self.keyConfigPanel = keys.KeyConfigPanel(self)
            self.graphicsPanel = panels.GraphicsPanel(self)
            if self.fileOpener in self.subwidgets:
                idx = self.subwidgets.index(self.fileOpener)
                self.remove(self.fileOpener)
                self.fileOpener = albow.FileOpener(self)
                if idx is not None:
                    self.add(self.fileOpener)
                self.fileOpener.focus()
    #-#

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

    @staticmethod
    def removeLevelDat(filename):
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

    @staticmethod
    def setRecentWorlds(worlds):
        for i, filename in enumerate(worlds):
            config.config.set("Recent Worlds", str(i), filename.encode('utf-8'))

    def makeSideColumn1(self):
        def showLicense():
            platform_open(os.path.join(directories.getDataDir(), "LICENSE.txt"))
            
        def refresh():
            PlayerCache().force_refresh()

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
                     lambda: platform_open("http://www.mcedit-unified.net"),
                     "http://www.mcedit-unified.net"),
                    ("",
                     "About MCEdit",
                     lambda: platform_open("http://www.mcedit-unified.net/about.html"),
                     "http://www.mcedit-unified.net/about.html"),
                    ("",
                     "License",
                     showLicense,
                     os.path.join(directories.getDataDir(), "LICENSE.txt")),
                    ("",
                     "Refresh Player Names",
                     refresh)
                   ])

        c = albow.HotkeyColumn(hotkeys)

        return c

    def makeSideColumn2(self):
        def showCacheDir():
            try:
                os.mkdir(directories.getCacheDir())
            except OSError:
                pass
            platform_open(directories.getCacheDir())

        def showScreenshotsDir():
            try:
                os.mkdir(os.path.join(directories.getCacheDir(), "screenshots"))
            except OSError:
                pass
            platform_open(os.path.join(directories.getCacheDir(), "screenshots"))

        hotkeys = ([("",
                     "Config Files",
                     showCacheDir,
                     directories.getCacheDir()),
                    ("",
                     "Screenshots",
                     showScreenshotsDir,
                     os.path.join(directories.getCacheDir(), "screenshots"))
                   ])

        c = albow.HotkeyColumn(hotkeys)

        return c

    def resized(self, dw, dh):
        """
        Handle window resizing events.
        """
        if DEBUG_WM:
            print "############################ RESIZED ############################"

        (w, h) = self.size
        config_w, config_h = config.settings.windowWidth.get(), config.settings.windowHeight.get()
        win = self.displayContext.win

        if DEBUG_WM and win:
            print "dw", dw, "dh", dh
            print "self.size (w, h) 1", self.size, "win.get_size", win.get_size()
            print "size 1", config_w, config_h
        elif DEBUG_WM and not win:
            print "win is None, unable to print debug messages"

        if win:
            x, y =  win.get_position()
            if DEBUG_WM:
                print "position", x, y
                print "config pos", (config.settings.windowX.get(), config.settings.windowY.get())

        if w == 0 and h == 0:
            # The window has been minimized, no need to draw anything.
            self.editor.renderer.render = False
            return

        # Mac window handling works better now, but `win`
        # doesn't exist. So to get this alert to show up
        # I'm checking if the platform is darwin. This only
        # works because the code block never actually references
        # `win`, otherwise it WOULD CRASH!!!
        # You cannot change further if statements like this
        # because they reference `win`
        if win or sys.platform == "darwin":
            # Handling too small resolutions.
            # Dialog texts.
            # "MCEdit does not support window resolutions below 1000x700.\nYou may not be able to access all functions at this resolution."
            # New buttons:
            # "Don't warn me again": disable the window popup across sessions.
            #     Tooltip: "Disable this message. Definitively. Even the next time you start MCEdit."
            # "OK": dismiss the window and let go, don't pop up again for the session
            #     Tooltip: "Continue and not see this message until you restart MCEdit"
            # "Cancel": resizes the window to the minimum size
            #     Tooltip: "Resize the window to the minimum recommended resolution."

            # If the config showWindowSizeWarning is true and self.resizeAlert is true, show the popup
            if (w < 1000 or h < 680) and config.settings.showWindowSizeWarning.get():
                _w = w
                _h = h
                if self.resizeAlert:
                    answer = "_OK"

                    # Force the size only for the dimension that needs it.
                    if w < 1000 and h < 680:
                        _w = 1000
                        _h = 680
                    elif w < 1000:
                        _w = 1000
                    elif h < 680:
                        _h = 680
                    if not albow.dialogs.ask_tied_to:
                        answer = albow.ask(
                                           "MCEdit does not support window resolutions below 1000x700.\nYou may not be able to access all functions at this resolution.",
                                           ["Don't remind me again.", "OK", "Cancel"], default=1, cancel=1,
                                           responses_tooltips = {"Don't remind me again.": "Disable this message. Definitively. Even the next time you start MCEdit.",
                                                                 "OK": "Continue and not see this message until you restart MCEdit",
                                                                 "Cancel": "Resize the window to the minimum recommended resolution."},
                                           tie_widget_to=True)
                    else:
                        if not albow.dialogs.ask_tied_to._visible:
                            albow.dialogs.ask_tied_to._visible = True
                            answer = albow.dialogs.ask_tied_to.present()
                    if answer == "Don't remind me again.":
                        config.settings.showWindowSizeWarning = False
                        self.resizeAlert = False
                    elif answer == "OK":
                        w, h = self.size
                        self.resizeAlert = False
                    elif answer == "Cancel":
                        w, h = _w, _h
                else:
                    if albow.dialogs.ask_tied_to:
                        albow.dialogs.ask_tied_to.dismiss("_OK")
                        del albow.dialogs.ask_tied_to
                        albow.dialogs.ask_tied_to = None
            elif (w >= 1000 or h >= 680):
                if albow.dialogs.ask_tied_tos:
                    for ask_tied_to in albow.dialogs.ask_tied_tos:
                        ask_tied_to._visible = False
                        ask_tied_to.dismiss("_OK")
                        ask_tied_to.set_parent(None)
                        del ask_tied_to

        if not win:
            if w < 1000:
                config.settings.windowWidth.set(1000)
                w = 1000
                x = config.settings.windowX.get()

            if h < 680:
                config.settings.windowHeight.set(680)
                h = 680
                y = config.settings.windowY.get()

        if not self.editor.renderer.render:
            self.editor.renderer.render = True

        save_geom = True

        if win:
            maximized = win.get_state() == mcplatform.MAXIMIZED
            sz = map(max, win.get_size(), (w, h))

            if DEBUG_WM:
                print "sz", sz
                print "maximized", maximized, "self.maximized", self.maximized

            if maximized:
                if DEBUG_WM:
                    print "maximize, saving maximized size"
                config.settings.windowMaximizedWidth.set(sz[0])
                config.settings.windowMaximizedHeight.set(sz[1])
                config.save()
                self.saved_pos = config.settings.windowX.get(), config.settings.windowY.get()
                save_geom = False
                self.resizing = 0
                win.set_mode(sz, self.displayContext.displayMode())
            else:
                if DEBUG_WM:
                    print "size 2", config.settings.windowWidth.get(), config.settings.windowHeight.get()
                    print "config_w", config_w, "config_h", config_h
                    print "pos", config.settings.windowX.get(), config.settings.windowY.get()
                if self.maximized != maximized:
                    if DEBUG_WM:
                        print "restoring window pos and size"
                        print "(config.settings.windowX.get(), config.settings.windowY.get())", (config.settings.windowX.get(), config.settings.windowY.get())
                    (w, h) = (config_w, config_h)
                    win.set_state(1, (w, h), self.saved_pos)
                else:
                    if DEBUG_WM:
                        print "window resized"
                        print "setting size to", (w, h), "and pos to", (x,y)
                    win.set_mode((w, h), self.displayContext.displayMode())
                    win.set_position((x, y))
                config.settings.windowMaximizedWidth.set(0)
                config.settings.windowMaximizedHeight.set(0)
                config.save()
            self.maximized = maximized

        if DEBUG_WM:
            print "self.size (w, h) 2", self.size, (w, h)
            surf = pygame.display.get_surface()
            print "display surf rect", surf.get_rect()
            if win:
                if hasattr(win.base_handler, 'get_geometry'):
                    print "win.base_handler geometry", win.base_handler.get_geometry()
                    print "win.base_handler.parent geometry", win.base_handler.query_tree().parent.get_geometry()
                    print "win.base_handler.parent.parent geometry", win.base_handler.query_tree().parent.query_tree().parent.get_geometry()

        if save_geom:
            config.settings.windowWidth.set(w)
            config.settings.windowHeight.set(h)
            config.save()

        # The alert window is disabled if win is not None
        if not win and (dw > 20 or dh > 20):
            if not hasattr(self, 'resizeAlert'):
                self.resizeAlert = self.shouldResizeAlert
            if self.resizeAlert:
                albow.alert(
                    "Window size increased. You may have problems using the cursor until MCEdit is restarted.")
                self.resizeAlert = False
        if win:
            win.sync()

        GLViewport.resized(self, dw, dh)

    shouldResizeAlert = config.settings.shouldResizeAlert.property()

    def loadFile(self, filename, addToRecent=True):
        if os.path.exists(filename):
            try:
                self.editor.loadFile(filename, addToRecent=addToRecent)
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
#             if config.settings.savePositionOnClose.get():
#                 self.editor.waypointManager.saveLastPosition(self.editor.mainViewport, self.editor.level.getPlayerDimension())
#             self.editor.waypointManager.save()
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

    @staticmethod
    def justQuit():
        raise SystemExit

    @classmethod
    def fetch_version(cls):
        with cls.version_lock:
            cls.version_info = release.fetch_new_version_info()

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
    def main(cls):
        PlayerCache().load()
        displayContext = GLDisplayContext(splash.splash, caption=(('MCEdit ~ ' + release.get_version()%_("for")).encode('utf-8'), 'MCEdit'))

        os.environ['SDL_VIDEO_CENTERED'] = '0'

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

        cls.version_lock = threading.Lock()
        cls.version_info = None
        cls.version_checked = False

        fetch_version_thread = threading.Thread(target=cls.fetch_version)
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
            raise ValueError("Error requested via -causeError")

        while True:
            try:
                rootwidget.run()
            except (SystemExit, KeyboardInterrupt):
                print "Shutting down..."
                exc_txt = traceback.format_exc()
                if mcedit.editor.level:
                    if config.settings.savePositionOnClose.get():
                        mcedit.editor.waypointManager.saveLastPosition(mcedit.editor.mainViewport, mcedit.editor.level.dimNo)
                    mcedit.editor.waypointManager.save()
                # The following Windows specific code won't be executed if we're using '--debug-wm' switch.
                if not USE_WM and sys.platform == "win32" and config.settings.setWindowPlacement.get():
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

                # Restore the previous language if we ran with '-tt' (update translation template).
                if albow.translate.buildTemplate:
                    logging.warning('Restoring %s.'%orglang)
                    config.settings.langCode.set(orglang)
                #
                config.save()
                mcedit.editor.renderer.discardAllChunks()
                mcedit.editor.deleteAllCopiedSchematics()
                if mcedit.editor.level:
                    mcedit.editor.level.close()
                mcedit.editor.root.RemoveEditFiles()
                if 'SystemExit' in traceback.format_exc() or 'KeyboardInterrupt' in traceback.format_exc():
                    raise
                else:
                    if 'SystemExit' in exc_txt:
                        raise SystemExit
                    if 'KeyboardInterrupt' in exc_txt:
                        raise KeyboardInterrupt
            except MemoryError:
                traceback.print_exc()
                mcedit.editor.handleMemoryError()

    def saveWindowPosition(self):
        """Save the window position in the configuration handler."""
        if DEBUG_WM:
            print "############################ EXITING ############################"
        win = self.displayContext.win
        # The following Windows specific code will not be executed if we're using '--debug-wm' switch.
        if not USE_WM and sys.platform == "win32" and config.settings.setWindowPlacement.get():
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
        elif win:
            config.settings.windowMaximized.set(self.maximized)
            if not self.maximized:
                x, y = win.get_position()
            else:
                x, y = self.saved_pos
            if DEBUG_WM:
                print "x", x, "y", y
            config.settings.windowX.set(x)
            config.settings.windowY.set(y)
            

    def restart(self):
        self.saveWindowPosition()
        config.save()
        self.editor.renderer.discardAllChunks()
        self.editor.deleteAllCopiedSchematics()
        if self.editor.level:
            self.editor.level.close()
        self.editor.root.RemoveEditFiles()
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
    except pygame.error:
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
        ServerJarStorage()
    except Exception, e:
        logging.warning('Error creating server jar storage folder: {0!r}'.format(e))
        
    try:
        MCEdit.main()
    except Exception as e:
        print "mcedit.main MCEdit exited with errors."
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
    except Exception:
        pass


class FakeStdOutErr:
    """Fake file object to redirect very last Python output.
    Used to track 'errors' not handled in MCEdit.
    Mimics 'write' and 'close' file objects methods.
    Used on Linux only."""
    mode = 'a'
    def __init__(self, *args, **kwargs):
        """*args and **kwargs are ignored.
        Deletes the 'logger' object and reopen 'logfile' in append mode."""
        global logger
        global logfile
        del logger
        self.fd = open(logfile, 'a')

    def write(self, msg):
        self.fd.write(msg)

    def close(self, *args, **kwargs):
        self.fd.flush()
        self.fd.close()

if __name__ == "__main__":
    try:
        main(sys.argv)
    except (SystemExit, KeyboardInterrupt):
        # It happens that on Linux, Python tries to kill already dead processes and display errors in the console.
        # Redirecting them to the log file preserve them and other errors which may occur.
        if sys.platform == "linux2":
            logger.debug("MCEdit is exiting normally.")
            logger.debug("Lines below this one are pure Python output.")
            sys.stdout = sys.stderr = FakeStdOutErr()
        pass
    except:
        traceback.print_exc()
        print ""
        print "=================================="
        print "\t\t\t  MCEdit has crashed"
        print "=================================="
        raw_input("Press the Enter key to close this window")
        pass
    #sys.exit(main(sys.argv))
