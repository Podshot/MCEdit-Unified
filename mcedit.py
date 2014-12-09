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
#if hasattr(sys, 'frozen'):
#    if sys.platform == "win32":
#        import esky
#        app = esky.Esky(sys.executable)
#
#        logfile = os.path.join(app.appdir, logfile)
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
# TODO: Language Detection
import locale
DEF_ENC = locale.getdefaultlocale()[1]
from albow.translate import _
#!# for debugging
from albow.translate import getPlatInfo
#!#
from albow.dialogs import Dialog
from albow.openglwidgets import GLViewport
from albow.root import RootWidget
from config import config
import directories
#-#
albow.resource.resource_dir = directories.getDataDir()
#-#
import functools
import glutils
import leveleditor
#-# Building translation template
if "-tt" in sys.argv:
    albow.translate.buildTemplate = True
    albow.translate.loadTemplate()
#-#
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

getPlatInfo(OpenGL=OpenGL, numpy=numpy, pygame=pygame)

ESCAPE = '\033'


class FileOpener(albow.Widget):
    is_gl_container = True

    def __init__(self, mcedit, *args, **kwargs):
        kwargs['rect'] = mcedit.rect
        albow.Widget.__init__(self, *args, **kwargs)
        self.anchor = 'tlbr'
        self.mcedit = mcedit
        self.root = self.get_root()

        helpColumn = []

        label = albow.Label(_("{0}/{1}/{2}/{3}/{4}/{5} to move").format(
            config.keys.forward.get(),
            config.keys.left.get(),
            config.keys.back.get(),
            config.keys.right.get(),
            config.keys.up.get(),
            config.keys.down.get(),
        ))
        label.anchor = 'whrt'
        label.align = 'r'
        helpColumn.append(label)

        def addHelp(text):
            label = albow.Label(text)
            label.anchor = 'whrt'
            label.align = "r"
            helpColumn.append(label)

        addHelp(_("{0} to slow down").format(config.keys.brake.get()))
        addHelp("Right-click to toggle camera control")
        addHelp("Mousewheel to control tool distance")
        addHelp(_("Hold {0} for details").format(config.keys.showBlockInfo.get()))

        helpColumn = albow.Column(helpColumn, align="r")
        helpColumn.topright = self.topright
        helpColumn.anchor = "whrt"
        #helpColumn.is_gl_container = True
        self.add(helpColumn)

        keysColumn = [albow.Label("")]
        buttonsColumn = [leveleditor.ControlPanel.getHeader()]

        shortnames = []
        for world in self.mcedit.recentWorlds():
            shortname = os.path.basename(world)
            try:
                if pymclevel.MCInfdevOldLevel.isLevel(world):
                    lev = pymclevel.MCInfdevOldLevel(world, readonly=True)
                    shortname = lev.LevelName
                    if lev.LevelName != lev.displayName:
                        shortname = u"{0} ({1})".format(lev.LevelName, lev.displayName)
            except Exception, e:
                logging.warning(
                    'Couldn\'t get name from recent world: {0!r}'.format(e))

            if shortname == "level.dat":
                shortname = os.path.basename(os.path.dirname(world))

            if len(shortname) > 40:
                shortname = shortname[:37] + "..."
            shortnames.append(shortname)

        hotkeys = ([(config.keys.newWorld.get(), 'Create New World', self.createNewWorld),
                    (config.keys.quickLoad.get(), 'Quick Load', self.mcedit.editor.askLoadWorld),
                    (config.keys.open.get(), 'Open...', self.promptOpenAndLoad)] + [
                       ('F{0}'.format(i + 1), shortnames[i], self.createLoadButtonHandler(world))
                       for i, world in enumerate(self.mcedit.recentWorlds())])

        commandRow = mceutils.HotkeyColumn(hotkeys, keysColumn, buttonsColumn)
        commandRow.anchor = 'lrh'

        sideColumn = mcedit.makeSideColumn()
        sideColumn.anchor = 'wh'

        contentRow = albow.Row((commandRow, sideColumn))
        contentRow.center = self.center
        contentRow.anchor = "rh"
        self.add(contentRow)
        self.sideColumn = sideColumn

    def gl_draw_self(self, root, offset):
        #self.mcedit.editor.mainViewport.setPerspective();
        self.mcedit.editor.drawStars()

    def idleevent(self, evt):
        self.mcedit.editor.doWorkUnit(onMenu=True)
        #self.invalidate()

    def key_down(self, evt):
        keyname = self.root.getKey(evt)
        if keyname == 'Alt-F4':
            raise SystemExit
        if keyname in ('F1', 'F2', 'F3', 'F4', 'F5'):
            self.mcedit.loadRecentWorldNumber(int(keyname[1]))
        if keyname == config.keys.quickLoad.get():
            self.mcedit.editor.askLoadWorld()
        if keyname == config.keys.newWorld.get():
            self.createNewWorld()
        if keyname == config.keys.open.get():
            self.promptOpenAndLoad()
        if keyname == config.keys.quit.get():
            self.mcedit.confirm_quit()
        if keyname == config.keys.takeAScreenshot.get():
            self.mcedit.editor.take_screenshot()

        self.root.fix_sticky_ctrl()

    def promptOpenAndLoad(self):
        try:
            filename = mcplatform.askOpenFile()
            if filename:
                self.mcedit.loadFile(filename)
        except Exception, e:
            logging.error('Error during proptOpenAndLoad: {0!r}'.format(e))

    def createNewWorld(self):
        self.parent.createNewWorld()

    def createLoadButtonHandler(self, filename):
        return lambda: self.mcedit.loadFile(filename)

class graphicsPanel(Dialog):
    anchor = 'wh'

    def __init__(self, mcedit):
        Dialog.__init__(self)

        self.mcedit = mcedit

        fieldOfViewRow = mceutils.FloatInputRow("Field of View: ",
                                                ref=config.settings.fov, width=100, min=25, max=120)

        targetFPSRow = mceutils.IntInputRow("Target FPS: ",
                                            ref=config.settings.targetFPS, width=100, min=1, max=60)

        bufferLimitRow = mceutils.IntInputRow("Vertex Buffer Limit (MB): ",
                                              ref=config.settings.vertexBufferLimit, width=100, min=0)

        fastLeavesRow = mceutils.CheckBoxLabel("Fast Leaves",
                                               ref=config.settings.fastLeaves,
                                               tooltipText="Leaves are solid, like Minecraft's 'Fast' graphics")

        roughGraphicsRow = mceutils.CheckBoxLabel("Rough Graphics",
                                                  ref=config.settings.roughGraphics,
                                                  tooltipText="All blocks are drawn the same way (overrides 'Fast Leaves')")

        enableMouseLagRow = mceutils.CheckBoxLabel("Enable Mouse Lag",
                                                   ref=config.settings.enableMouseLag,
                                                 tooltipText="Enable choppy mouse movement for faster loading.")

        packs = resource_packs.packs.get_available_resource_packs()
        packs.remove('Default')
        packs.sort()
        packs.insert(0, 'Default')
        self.resourcePackButton = mceutils.ChoiceButton(packs, choose=self.change_texture)
        self.resourcePackButton.selectedChoice = resource_packs.packs.get_selected_resource_pack_name()

        settingsColumn = albow.Column((fastLeavesRow,
                                       roughGraphicsRow,
                                       enableMouseLagRow,
                                       #                                  texturePackRow,
                                       fieldOfViewRow,
                                       targetFPSRow,
                                       bufferLimitRow,
                                       self.resourcePackButton,
                                      ), align='r')

        settingsColumn = albow.Column((albow.Label("Settings"),
                                       settingsColumn))

        settingsRow = albow.Row((settingsColumn,))

        optionsColumn = albow.Column((settingsRow, albow.Button("OK", action=self.dismiss)))

        self.add(optionsColumn)
        self.shrink_wrap()

    def _reloadTextures(self, pack):
        if hasattr(pymclevel.alphaMaterials, "terrainTexture"):
            self.mcedit.displayContext.loadTextures()

    def change_texture(self):
        resource_packs.packs.set_selected_resource_pack_name(self.resourcePackButton.selectedChoice)
        self.mcedit.displayContext.loadTextures()
    texturePack = config.settings.skin.property(_reloadTextures)


class OptionsPanel(Dialog):
    anchor = 'wh'

    def __init__(self, mcedit):
        Dialog.__init__(self)

        self.mcedit = mcedit

        self.langs = {}
        self.sgnal = {}

    def initComponents(self):
        """Initilize the window components. Call this after translation hs been loaded."""
        autoBrakeRow = mceutils.CheckBoxLabel("Autobrake",
                                              ref=config.controls.autobrake,
                                              tooltipText="Apply brake when not pressing movement keys")

        swapAxesRow = mceutils.CheckBoxLabel("Swap Axes Looking Down",
                                             ref=config.controls.swapAxes,
                                             tooltipText="Change the direction of the Forward and Backward keys when looking down")

        cameraAccelRow = mceutils.FloatInputRow("Camera Acceleration: ",
                                                ref=config.controls.cameraAccel, width=100, min=5.0)

        cameraDragRow = mceutils.FloatInputRow("Camera Drag: ",
                                               ref=config.controls.cameraDrag, width=100, min=1.0)

        cameraMaxSpeedRow = mceutils.FloatInputRow("Camera Max Speed: ",
                                                   ref=config.controls.cameraMaxSpeed, width=100, min=1.0)

        cameraBrakeSpeedRow = mceutils.FloatInputRow("Camera Braking Speed: ",
                                                     ref=config.controls.cameraBrakingSpeed, width=100,
                                                     min=1.0)

        mouseSpeedRow = mceutils.FloatInputRow("Mouse Speed: ",
                                               ref=config.controls.mouseSpeed, width=100, min=0.1,
                                               max=20.0)

        undoLimitRow = mceutils.IntInputRow("Undo Limit: ",
                                            ref=config.settings.undoLimit, width=100, min=0)

        maxCopiesRow = mceutils.IntInputRow("Copy Stack Size: ",
                                            ref=config.settings.maxCopies, width=100, min=0,
                                            tooltipText="Maximum number of copied objects.")

        # FONT SIZE
#        fontProportion = mceutils.IntInputRow("Fonts Proportion (%): ",
#                                            ref=config.settings.fontProportion, width=100, min=0,
#                                            tooltipText="Fonts sizing proportion. The number is a percentage.")
#        albow.resource.font_proportion = config.settings.fontProportion.get()

        invertRow = mceutils.CheckBoxLabel("Invert Mouse",
                                           ref=config.controls.invertMousePitch,
                                           tooltipText="Reverse the up and down motion of the mouse.")

        spaceHeightRow = mceutils.IntInputRow(_("Low Detail Height"),
                                              ref=config.settings.spaceHeight,
                                              tooltipText="When you are this far above the top of the world, move fast and use low-detail mode.")

        blockBufferRow = mceutils.IntInputRow("Block Buffer (MB):",
                                              ref=albow.AttrRef(self, 'blockBuffer'), min=1,
                                              tooltipText="Amount of memory used for temporary storage.  When more than this is needed, the disk is used instead.")

        setWindowPlacementRow = mceutils.CheckBoxLabel("Set Window Placement",
                                                       ref=config.settings.setWindowPlacement,
                                                       tooltipText="Try to save and restore the window position.")

        rotateBlockBrushRow = mceutils.CheckBoxLabel("Rotate block with brush",
                                                        ref=config.settings.rotateBlockBrush,
                                                        tooltipText="When rotating your brush, also rotate the orientation of the block your brushing with")

        windowSizeRow = mceutils.CheckBoxLabel("Window Resize Alert",
                                               ref=config.settings.shouldResizeAlert,
                                               tooltipText="Reminds you that the cursor won't work correctly after resizing the window.")

        superSecretSettingsRow = mceutils.CheckBoxLabel("Super Secret Settings",
                                                ref=config.settings.superSecretSettings,
                                                tooltipText="Weird stuff happen!")

        longDistanceRow = mceutils.CheckBoxLabel("Long-Distance Mode",
                                                 ref=config.settings.longDistanceMode,
                                                 tooltipText="Always target the farthest block under the cursor, even in mouselook mode.")

        flyModeRow = mceutils.CheckBoxLabel("Fly Mode",
                                            ref=config.settings.flyMode,
                                            tooltipText="Moving forward and Backward will not change your altitude in Fly Mode.")

        lng = config.settings.langCode.get()

        langs = sorted(self.getLanguageChoices().items())

        langNames = [k for k, v in langs]

        self.languageButton = mceutils.ChoiceButton(langNames, choose=self.changeLanguage)
        if self.sgnal[lng] in self.languageButton.choices:
            self.languageButton.selectedChoice = self.sgnal[lng]

        langButtonRow = albow.Row((albow.Label("Language", tooltipText="Choose your language."), self.languageButton))

        staticCommandsNudgeRow = mceutils.CheckBoxLabel("Static Coords While Nudging",
                                            ref=config.settings.staticCommandsNudge,
                                            tooltipText="Change static coordinates in command blocks while nudging.")

        moveSpawnerPosNudgeRow = mceutils.CheckBoxLabel("Change Spawners While Nudging",
                                            ref=config.settings.moveSpawnerPosNudge,
                                            tooltipText="Change the position of the mobs in spawners while nudging.")

        self.goPortableButton = goPortableButton = albow.Button("Change", action=self.togglePortable)

        goPortableButton.tooltipText = self.portableButtonTooltip()
        goPortableRow = albow.Row(
            (albow.ValueDisplay(ref=albow.AttrRef(self, 'portableLabelText'), width=250, align='r'), goPortableButton))

# Disabled Crash Reporting Option
#       reportRow = mceutils.CheckBoxLabel("Report Errors",
#                                          ref=config.settings.reportCrashes,
#                                          tooltipText="Automatically report errors to the developer.")

        inputs = (
            spaceHeightRow,
            cameraAccelRow,
            cameraDragRow,
            cameraMaxSpeedRow,
            cameraBrakeSpeedRow,
            blockBufferRow,
            mouseSpeedRow,
            undoLimitRow,
            maxCopiesRow,
#            fontProportion, # FONT SIZE
        )

        options = (
                    longDistanceRow,
                    flyModeRow,
                    autoBrakeRow,
                    swapAxesRow,
                    invertRow,
                    superSecretSettingsRow,
                    staticCommandsNudgeRow,
                    moveSpawnerPosNudgeRow,
                    rotateBlockBrushRow,
                    langButtonRow,
                    ) + (
                        ((sys.platform == "win32" and pygame.version.vernum == (1, 9, 1)) and (windowSizeRow,) or ())
                    ) + (
                        (sys.platform == "win32") and (setWindowPlacementRow,) or ()
                    ) + (
                        (not sys.platform == "darwin") and (goPortableRow,) or ()
                    )

        rightcol = albow.Column(options, align='r')
        leftcol = albow.Column(inputs, align='r')

        optionsColumn = albow.Column((albow.Label("Options"),
                                      albow.Row((leftcol, rightcol), align="t")))

        settingsRow = albow.Row((optionsColumn,))

        optionsColumn = albow.Column((settingsRow, albow.Button("OK", action=self.dismiss)))

        self.add(optionsColumn)
        self.shrink_wrap()

    @property
    def blockBuffer(self):
        return config.settings.blockBuffer.get() / 1048576

    @blockBuffer.setter
    def blockBuffer(self, val):
        config.settings.blockBuffer.set(int(val * 1048576))

    def getLanguageChoices(self, current=None):
        files = os.listdir(albow.translate.langPath)
        langs = {}
        sgnal = {}
        for file in files:
            name, ext = os.path.splitext(file)
            if ext == ".trn" and len(name) == 5 and name[2] == "_":
                langName = albow.translate.getLangName(file)
                langs[langName] = name
                sgnal[name] = langName
        if "English (US)" not in langs.keys():
            langs[u"English (US)"] = "en_US"
            sgnal["en_US"] = u"English (US)"
        self.langs = langs
        self.sgnal = sgnal
        logging.debug("Detected languages: %s"%self.langs)
        return langs

    def changeLanguage(self):
        langName = self.languageButton.selectedChoice
        if langName not in self.langs:
            lng = "en_US"
        else:
            lng = self.langs[langName]
        config.settings.langCode.set(lng)

    def portableButtonTooltip(self):
        return (
        "Click to make your MCEdit install self-contained by moving the settings and schematics into the program folder",
        "Click to make your MCEdit install persistent by moving the settings and schematics into your Documents folder")[
            directories.portable]

    @property
    def portableLabelText(self):
        return (_("Install Mode: Portable"), _("Install Mode: Fixed"))[1 - directories.portable]

    def togglePortable(self):
        if sys.platform == "darwin":
            return False
        textChoices = [
            _("This will make your MCEdit \"portable\" by moving your settings and schematics into the same folder as {0}. Continue?").format(
                (sys.platform == "darwin" and _("the MCEdit application") or _("MCEditData"))),
            _("This will move your settings and schematics to your Documents folder. Continue?"),
        ]
        if sys.platform == "darwin":
            textChoices[
                1] = _("This will move your schematics to your Documents folder and your settings to your Preferences folder. Continue?")

        alertText = textChoices[directories.portable]
        if albow.ask(alertText) == "OK":
            try:
                [directories.goPortable, directories.goFixed][directories.portable]()
            except Exception, e:
                traceback.print_exc()
                albow.alert(_(u"Error while moving files: {0}").format(repr(e)))

        self.goPortableButton.tooltipText = self.portableButtonTooltip()
        return True

    def dismiss(self, *args, **kwargs):
        """Used to change the language."""
        lng = config.settings.langCode.get()
        try:
            o, n, sc = albow.translate.setLang(lng)
        except:
            o, n, sc = albow.translate.setLang(self.langs[lng])
        if not sc and n != "en_US":
            albow.alert(_("{} is not a valid language").format("%s [%s]"%(self.sgnal[n], n)))
            if o == n:
                o = "en_US"
            config.settings.langCode.set(o)
            albow.translate.setLang(o)
        elif o != n:
            editor = self.mcedit.editor
            if editor and editor.unsavedEdits:
                result = albow.ask("You must restart MCEdit to see language changes", ["Save and Restart", "Restart", "Later"])
            else:
                result = albow.ask("You must restart MCEdit to see language changes", ["Restart", "Later"])
            if result == "Save and Restart":
                editor.saveFile()
                self.mcedit.restart()
            elif result == "Restart":
                self.mcedit.restart()
            elif result == "Later":
                pass
        Dialog.dismiss(self, *args, **kwargs)

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

        self.optionsPanel = OptionsPanel(self)
        if not albow.translate.buildTemplate:
            self.optionsPanel.getLanguageChoices()
            lng = config.settings.langCode.get()
            if lng not in self.optionsPanel.sgnal:
                lng = "en_US"
                config.settings.langCode.set(lng)
            albow.translate.setLang(lng)
        self.optionsPanel.initComponents()
        self.graphicsPanel = graphicsPanel(self)

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

        self.fileOpener = FileOpener(self)
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
        self.fileOpener = FileOpener(self)
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

        new_version = release.check_for_new_version()
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
            wParent = win.query_tree().parent.query_tree().parent
            geom = wParent.get_geometry()
            config.settings.windowX.set(geom.x)
            config.settings.windowY.set(geom.y)

    def restart(self):
        self.saveWindowPosition()
        config.save()
        self.editor.renderer.discardAllChunks()
        self.editor.deleteAllCopiedSchematics()
        python = sys.executable
#        p = 0
#        if sys.argv[0].endswith('.exe'):
#            p = 1
#        os.execl(python, python, * sys.argv[p:])
        if sys.argv[0].endswith('.exe'):
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


class GLDisplayContext(object):
    def __init__(self):
        self.reset()

    def getWindowSize(self):
        w, h = (config.settings.windowWidth.get(), config.settings.windowHeight.get())
        return max(20, w), max(20, h)

    def displayMode(self):
        return pygame.OPENGL | pygame.RESIZABLE | pygame.DOUBLEBUF

    def reset(self):
        pygame.key.set_repeat(500, 100)

        try:
            display.gl_set_attribute(pygame.GL_SWAP_CONTROL, config.settings.vsync.get())
        except Exception, e:
            logging.warning('Unable to set vertical sync: {0!r}'.format(e))

        display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)

        d = display.set_mode(self.getWindowSize(), self.displayMode())
        try:
            pygame.scrap.init()
        except:
            logging.warning('PyGame clipboard integration disabled.')

        display.set_caption('MCEdit ~ ' + release.get_version(), 'MCEdit')
        if sys.platform == 'win32' and config.settings.setWindowPlacement.get():
            config.settings.setWindowPlacement.set(False)
            config.save()
            X, Y = config.settings.windowX.get(), config.settings.windowY.get()

            if X:
                w, h = self.getWindowSize()
                hwndOwner = display.get_wm_info()['window']

                flags, showCmd, ptMin, ptMax, rect = mcplatform.win32gui.GetWindowPlacement(hwndOwner)
                realW = rect[2] - rect[0]
                realH = rect[3] - rect[1]

                showCmd = config.settings.windowShowCmd.get()
                rect = (X, Y, X + realW, Y + realH)

                mcplatform.win32gui.SetWindowPlacement(hwndOwner, (0, showCmd, ptMin, ptMax, rect))

            config.settings.setWindowPlacement.set(True)
            config.save()
        elif sys.platform == 'linux2' and mcplatform.hasXlibDisplay:
            dis = mcplatform.Xlib.display.Display()
            dRoot = dis.screen().root
            win = dRoot.get_full_property(dis.intern_atom('_NET_ACTIVE_WINDOW'), mcplatform.Xlib.X.AnyPropertyType).value[0]
            win = dis.create_resource_object('window', win)
            win.configure(x=config.settings.windowX.get(), y=config.settings.windowY.get())
            dis.sync()

        try:
            iconpath = os.path.join(directories.getDataDir(), 'favicon.png')
            iconfile = file(iconpath, 'rb')
            icon = pygame.image.load(iconfile, 'favicon.png')
            display.set_icon(icon)
        except Exception, e:
            logging.warning('Unable to set icon: {0!r}'.format(e))

        self.display = d

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glAlphaFunc(GL.GL_NOTEQUAL, 0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # textures are 256x256, so with this we can specify pixel coordinates
        GL.glMatrixMode(GL.GL_TEXTURE)
        GL.glScale(1 / 256., 1 / 256., 1 / 256.)

        self.loadTextures()

    def getTerrainTexture(self, level):
        return self.terrainTextures.get(level.materials.name, self.terrainTextures["Alpha"])

    def loadTextures(self):
        self.terrainTextures = {}

        def makeTerrainTexture(mats):
            w, h = 1, 1
            teximage = numpy.zeros((w, h, 4), dtype='uint8')
            teximage[:] = 127, 127, 127, 255

            GL.glTexImage2D(
                GL.GL_TEXTURE_2D,
                0,
                GL.GL_RGBA8,
                w,
                h,
                0,
                GL.GL_RGBA,
                GL.GL_UNSIGNED_BYTE,
                teximage
            )

        textures = (
            (pymclevel.classicMaterials, 'terrain-classic.png'),
            (pymclevel.indevMaterials, 'terrain-classic.png'),
            (pymclevel.alphaMaterials, resource_packs.packs.get_selected_resource_pack().terrain_path()),
            (pymclevel.pocketMaterials, 'terrain-pocket.png')
        )

        for mats, matFile in textures:
            try:
                if mats.name == 'Alpha':
                    tex = mceutils.loadAlphaTerrainTexture()
                else:
                    tex = mceutils.loadPNGTexture(matFile)
                self.terrainTextures[mats.name] = tex
            except Exception, e:
                logging.warning(
                    'Unable to load terrain from {0}, using flat colors.'
                    'Error was: {1!r}'.format(matFile, e)
                )
                self.terrainTextures[mats.name] = glutils.Texture(
                    functools.partial(makeTerrainTexture, mats)
                )
            mats.terrainTexture = self.terrainTextures[mats.name]

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
