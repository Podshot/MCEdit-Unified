# !/usr/bin/env python2.7
# -*- coding: utf8 -*-

#-# Modified by D.C.-G. for translation purpose

"""
mcedit.py

Startup, main menu, keyboard configuration, automatic updating.
"""
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
# import locale
# albow.translate.setLang(locale.getdefaultlocale()[0])
# del locale

albow.translate.buildTranslation(albow.translate.refreshLang())

from albow.translate import tr, langPath, verifyLangCode
from albow.dialogs import Dialog
from albow.openglwidgets import GLViewport
from albow.root import RootWidget
import config
import directories
import functools
from glbackground import Panel
import glutils
import leveleditor
from leveleditor import ControlSettings, Settings
import mceutils
import mcplatform
from mcplatform import platform_open
import numpy

import os
import os.path
import pygame
from pygame import display, key, rect
import pymclevel
import release
import shutil
import sys
import traceback

ESCAPE = '\033'


class FileOpener(albow.Widget):
    is_gl_container = True

    def __init__(self, mcedit, *args, **kwargs):
        kwargs['rect'] = mcedit.rect
        albow.Widget.__init__(self, *args, **kwargs)
        self.anchor = 'tlbr'
        self.mcedit = mcedit

        helpColumn = []

        label = albow.Label("{0} {1} {2} {3} {4} {5}".format(
            config.config.get('Keys', 'Forward'),
            config.config.get('Keys', 'Left'),
            config.config.get('Keys', 'Back'),
            config.config.get('Keys', 'Right'),
            config.config.get('Keys', 'Up'),
            config.config.get('Keys', 'Down'),
        ).upper() + tr(" to move"))
        label.anchor = 'whrt'
        label.align = 'r'
        helpColumn.append(label)

        def addHelp(text):
            label = albow.Label(text)
            label.anchor = 'whrt'
            label.align = "r"
            helpColumn.append(label)

        addHelp("{0}".format(config.config.get('Keys', 'Brake').upper()) + tr(" to slow down"))
        addHelp("Right-click to toggle camera control")
        addHelp("Mousewheel to control tool distance")
        addHelp("Hold SHIFT to move along a major axis")
        addHelp("Hold ALT for details")

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

        hotkeys = ([(config.config.get('Keys', 'New World'), 'Create New World', self.createNewWorld),
                    (config.config.get('Keys', 'Quick Load'), 'Quick Load', self.mcedit.editor.askLoadWorld),
                    (config.config.get('Keys', 'Open'), 'Open...', self.promptOpenAndLoad)] + [
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
        self.mcedit.editor.doWorkUnit()
        #self.invalidate()

    def key_down(self, evt):
        keyname = keys.getKey(evt)
        if keyname == 'Alt-F4':
            raise SystemExit
        if keyname in ('F1', 'F2', 'F3', 'F4', 'F5'):
            self.mcedit.loadRecentWorldNumber(int(keyname[1]))
        if keyname == config.config.get('Keys', 'Quick Load'):
            self.mcedit.editor.askLoadWorld()
        if keyname == config.config.get('Keys', 'New World'):
            self.createNewWorld()
        if keyname == config.config.get('Keys', 'Open'):
            self.promptOpenAndLoad()
        if keyname == config.config.get('Keys', 'Quit'):
            self.mcedit.confirm_quit()

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
                                                ref=Settings.fov.propertyRef(), width=100, min=25, max=120)

        targetFPSRow = mceutils.IntInputRow("Target FPS: ",
                                            ref=Settings.targetFPS.propertyRef(), width=100, min=1, max=60)

        bufferLimitRow = mceutils.IntInputRow("Vertex Buffer Limit (MB): ",
                                              ref=Settings.vertexBufferLimit.propertyRef(), width=100, min=0)

        fastLeavesRow = mceutils.CheckBoxLabel("Fast Leaves",
                                               ref=Settings.fastLeaves.propertyRef(),
                                               tooltipText="Leaves are solid, like Minecraft's 'Fast' graphics")

        roughGraphicsRow = mceutils.CheckBoxLabel("Rough Graphics",
                                                  ref=Settings.roughGraphics.propertyRef(),
                                                  tooltipText="All blocks are drawn the same way (overrides 'Fast Leaves')")

        enableMouseLagRow = mceutils.CheckBoxLabel("Enable Mouse Lag",
                                                   ref=Settings.enableMouseLag.propertyRef(),
                                                   tooltipText="Enable choppy mouse movement for faster loading.")

        settingsColumn = albow.Column((fastLeavesRow,
                                       roughGraphicsRow,
                                       enableMouseLagRow,
                                       #                                  texturePackRow,
                                       fieldOfViewRow,
                                       targetFPSRow,
                                       bufferLimitRow,
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

    texturePack = Settings.skin.configProperty(_reloadTextures)


class OptionsPanel(Dialog):
    anchor = 'wh'

    def __init__(self, mcedit):
        albow.translate.refreshLang(suppressAlert=True)

        Dialog.__init__(self)

        self.mcedit = mcedit

        autoBrakeRow = mceutils.CheckBoxLabel("Autobrake",
                                              ref=ControlSettings.autobrake.propertyRef(),
                                              tooltipText="Apply brake when not pressing movement keys")

        swapAxesRow = mceutils.CheckBoxLabel("Swap Axes Looking Down",
                                             ref=ControlSettings.swapAxes.propertyRef(),
                                             tooltipText="Change the direction of the Forward and Backward keys when looking down")

        cameraAccelRow = mceutils.FloatInputRow("Camera Acceleration: ",
                                                ref=ControlSettings.cameraAccel.propertyRef(), width=100, min=5.0)

        cameraDragRow = mceutils.FloatInputRow("Camera Drag: ",
                                               ref=ControlSettings.cameraDrag.propertyRef(), width=100, min=1.0)

        cameraMaxSpeedRow = mceutils.FloatInputRow("Camera Max Speed: ",
                                                   ref=ControlSettings.cameraMaxSpeed.propertyRef(), width=100, min=1.0)

        cameraBrakeSpeedRow = mceutils.FloatInputRow("Camera Braking Speed: ",
                                                     ref=ControlSettings.cameraBrakingSpeed.propertyRef(), width=100,
                                                     min=1.0)

        mouseSpeedRow = mceutils.FloatInputRow("Mouse Speed: ",
                                               ref=ControlSettings.mouseSpeed.propertyRef(), width=100, min=0.1,
                                               max=20.0)

        undoLimitRow = mceutils.IntInputRow("Undo Limit: ",
                                            ref=Settings.undoLimit.propertyRef(), width=100, min=0)

        invertRow = mceutils.CheckBoxLabel("Invert Mouse",
                                           ref=ControlSettings.invertMousePitch.propertyRef(),
                                           tooltipText="Reverse the up and down motion of the mouse.")

        spaceHeightRow = mceutils.IntInputRow("Low Detail Height",
                                              ref=Settings.spaceHeight.propertyRef(),
                                              tooltipText="When you are this far above the top of the world, move fast and use low-detail mode.")

        blockBufferRow = mceutils.IntInputRow("Block Buffer (MB):",
                                              ref=albow.AttrRef(self, 'blockBuffer'), min=1,
                                              tooltipText="Amount of memory used for temporary storage.  When more than this is needed, the disk is used instead.")

        setWindowPlacementRow = mceutils.CheckBoxLabel("Set Window Placement",
                                                       ref=Settings.setWindowPlacement.propertyRef(),
                                                       tooltipText="Try to save and restore the window position.")

        rotateBlockBrushRow = mceutils.CheckBoxLabel("Rotate block with brush",
                                                        ref=Settings.rotateBlockBrush.propertyRef(),
                                                        tooltipText="When rotating your brush, also rotate the orientation of the block your brushing with")

        windowSizeRow = mceutils.CheckBoxLabel("Window Resize Alert",
                                               ref=Settings.shouldResizeAlert.propertyRef(),
                                               tooltipText="Reminds you that the cursor won't work correctly after resizing the window.")

        visibilityCheckRow = mceutils.CheckBoxLabel("Visibility Check",
                                                    ref=Settings.visibilityCheck.propertyRef(),
                                                    tooltipText="Do a visibility check on chunks while loading. May cause a crash.")

        longDistanceRow = mceutils.CheckBoxLabel("Long-Distance Mode",
                                                 ref=Settings.longDistanceMode.propertyRef(),
                                                 tooltipText="Always target the farthest block under the cursor, even in mouselook mode.")

        flyModeRow = mceutils.CheckBoxLabel("Fly Mode",
                                            ref=Settings.flyMode.propertyRef(),
                                            tooltipText="Moving forward and Backward will not change your altitude in Fly Mode.")

        self.languageButton = mceutils.ChoiceButton(self.getLanguageChoices(Settings.langCode.get()), choose=self.changeLanguage)
        self.languageButton.selectedChoice = Settings.langCode.get()

        langButtonRow = albow.Row((albow.Label("Language", tooltipText="Choose your language."), self.languageButton))

        staticCommandsNudgeRow = mceutils.CheckBoxLabel("Static Coords While Nudging",
                                            ref=Settings.staticCommandsNudge.propertyRef(),
                                            tooltipText="Change static coordinates in command blocks while nudging.")

        moveSpawnerPosNudgeRow = mceutils.CheckBoxLabel("Change Spawners While Nudging",
                                            ref=Settings.moveSpawnerPosNudge.propertyRef(),
                                            tooltipText="Change the position of the mobs in spawners while nudging.")

        self.goPortableButton = goPortableButton = albow.Button("Change", action=self.togglePortable)

        goPortableButton.tooltipText = self.portableButtonTooltip()
        goPortableRow = albow.Row(
            (albow.ValueDisplay(ref=albow.AttrRef(self, 'portableLabelText'), width=250, align='r'), goPortableButton))

# Disabled Crash Reporting Option
#       reportRow = mceutils.CheckBoxLabel("Report Errors",
#                                          ref=Settings.reportCrashes.propertyRef(),
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
        )

        options = (
                    longDistanceRow,
                    flyModeRow,
                    autoBrakeRow,
                    swapAxesRow,
                    invertRow,
                    visibilityCheckRow,
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
        return Settings.blockBuffer.get() / 1048576

    @blockBuffer.setter
    def blockBuffer(self, val):
        Settings.blockBuffer.set(int(val * 1048576))

    def getLanguageChoices(self, current):
        files = os.listdir(langPath)
        langs = [l[:-5] for l in files if l.endswith(".json") and l not in ["language template.json"]]
        langs = [l for l in langs if verifyLangCode(l)]
        if "en_US" not in langs:
            langs = ["en_US"] + langs
        return langs

    def changeLanguage(self):
        Settings.langCode.set(self.languageButton.selectedChoice)

    def portableButtonTooltip(self):
        return (
        tr("Click to make your MCEdit install self-contained by moving the settings and schematics into the program folder"),
        tr("Click to make your MCEdit install persistent by moving the settings and schematics into your Documents folder"))[
            directories.portable]

    @property
    def portableLabelText(self):
        return (tr("Install Mode: Portable"), tr("Install Mode: Fixed"))[1 - directories.portable]

    def togglePortable(self):
    	if sys.platform == "darwin":
    		return False
        textChoices = [
            tr("This will make your MCEdit \"portable\" by moving your settings and schematics into the same folder as {0}. Continue?").format(
                (sys.platform == "darwin" and tr("the MCEdit application") or tr("MCEditData"))),
            tr("This will move your settings and schematics to your Documents folder. Continue?"),
        ]
        if sys.platform == "darwin":
            textChoices[
                1] = tr("This will move your schematics to your Documents folder and your settings to your Preferences folder. Continue?")

        alertText = textChoices[directories.portable]
        if albow.ask(alertText) == "OK":
            try:
                [directories.goPortable, directories.goFixed][directories.portable]()
            except Exception, e:
                traceback.print_exc()
                albow.alert(tr(u"Error while moving files: {0}").format(repr(e)))

        self.goPortableButton.tooltipText = self.portableButtonTooltip()
       	return True

    def dismiss(self, *args, **kwargs):
        """Used to change the language."""
        if albow.translate.refreshLang(self.mcedit, build=False) != "":
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
        self.keyConfigPanel.present()

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
                     "Open Data Folder",
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

        #surf = pygame.display.get_surface()
        #assert isinstance(surf, pygame.Surface)
        #dw, dh = surf.get_size()

        if w >= 1000 and h >= 700:
            Settings.windowWidth.set(w)
            Settings.windowHeight.set(h)
            config.saveConfig()
        elif w !=0 and h !=0:
            Settings.windowWidth.set(1000)
            Settings.windowHeight.set(700)
            config.saveConfig()
        if dw > 20 or dh > 20:
            if not hasattr(self, 'resizeAlert'):
                self.resizeAlert = self.shouldResizeAlert
            if self.resizeAlert:
                albow.alert(
                    "Window size increased. You may have problems using the cursor until MCEdit is restarted.")
                self.resizeAlert = False

    shouldResizeAlert = Settings.shouldResizeAlert.configProperty()

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
        if self.editor.unsavedEdits:
            result = albow.ask(tr("There are {0} unsaved changes.").format(self.editor.unsavedEdits),
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

    closeMinecraftWarning = Settings.closeMinecraftWarning.configProperty()

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
                tr('Version {} is available').format(new_version["tag_name"]),
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
                albow.alert(tr(' {} should now be downloading via your browser. You will still need to extract the downloaded file to use the updated version.').format(new_version["asset"]["name"]))

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
#                       albow.alert(tr("Failed to install update %s") % update_version)
#                   else:
#                       albow.alert(tr("Version %s installed. Restart MCEdit to begin using it.") % update_version)
#                       raise SystemExit()

        if mcedit.closeMinecraftWarning:
            answer = albow.ask(
                "Warning: Only open a world in one program at a time. If you open a world at the same time in MCEdit and in Minecraft, you will lose your work and possibly damage your save file.\n\n If you are using Minecraft 1.3 or earlier, you need to close Minecraft completely before you use MCEdit.",
                ["Don't remind me again.", "OK"], default=1, cancel=1)
            if answer == "Don't remind me again.":
                mcedit.closeMinecraftWarning = False

# Disabled Crash Reporting Option
#       if not Settings.reportCrashesAsked.get():
#           answer = albow.ask(
#               "When an error occurs, MCEdit can report the details of the error to its developers. "
#               "The error report will include your operating system version, MCEdit version, "
#               "OpenGL version, plus the make and model of your CPU and graphics processor. No personal "
#               "information will be collected.\n\n"
#               "Error reporting can be enabled or disabled in the Options dialog.\n\n"
#               "Enable error reporting?",
#               ["Yes", "No"],
#               default=0)
#           Settings.reportCrashes.set(answer == "Yes")
#           Settings.reportCrashesAsked.set(True)
        Settings.reportCrashes.set(False)
        Settings.reportCrashesAsked.set(True)

        config.saveConfig()
        if "-causeError" in sys.argv:
            raise ValueError, "Error requested via -causeError"

        while True:
            try:
                rootwidget.run()
            except SystemExit:
                if sys.platform == "win32" and Settings.setWindowPlacement.get():
                    (flags, showCmd, ptMin, ptMax, rect) = mcplatform.win32gui.GetWindowPlacement(
                        display.get_wm_info()['window'])
                    X, Y, r, b = rect
                    #w = r-X
                    #h = b-Y
                    if (showCmd == mcplatform.win32con.SW_MINIMIZE or
                                showCmd == mcplatform.win32con.SW_SHOWMINIMIZED):
                        showCmd = mcplatform.win32con.SW_SHOWNORMAL

                    Settings.windowX.set(X)
                    Settings.windowY.set(Y)
                    Settings.windowShowCmd.set(showCmd)

                config.saveConfig()
                mcedit.editor.renderer.discardAllChunks()
                mcedit.editor.deleteAllCopiedSchematics()
                raise
            except MemoryError:
                traceback.print_exc()
                mcedit.editor.handleMemoryError()


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
#       client.disabled = not config.config.getboolean("Settings", "report crashes new")
#       client.disabled = True
#
#       def _reportingChanged(val):
#           client.disabled = not val
#
#       Settings.reportCrashes.addObserver(client, '_enabled', _reportingChanged)
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
        w, h = (Settings.windowWidth.get(), Settings.windowHeight.get())
        return max(20, w), max(20, h)

    def displayMode(self):
        return pygame.OPENGL | pygame.RESIZABLE | pygame.DOUBLEBUF

    def reset(self):
        pygame.key.set_repeat(500, 100)

        try:
            display.gl_set_attribute(pygame.GL_SWAP_CONTROL, Settings.vsync.get())
        except Exception, e:
            logging.warning('Unable to set vertical sync: {0!r}'.format(e))

        display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)

        d = display.set_mode(self.getWindowSize(), self.displayMode())
        try:
            pygame.scrap.init()
        except:
            logging.warning('PyGame clipboard integration disabled.')

        display.set_caption('MCEdit ~ ' + release.get_version(), 'MCEdit')
        if sys.platform == 'win32' and Settings.setWindowPlacement.get():
            Settings.setWindowPlacement.set(False)
            config.saveConfig()
            X, Y = Settings.windowX.get(), Settings.windowY.get()

            if X:
                w, h = self.getWindowSize()
                hwndOwner = display.get_wm_info()['window']

                flags, showCmd, ptMin, ptMax, rect = mcplatform.win32gui.GetWindowPlacement(hwndOwner)
                realW = rect[2] - rect[0]
                realH = rect[3] - rect[1]

                showCmd = Settings.windowShowCmd.get()
                rect = (X, Y, X + realW, Y + realH)

                mcplatform.win32gui.SetWindowPlacement(hwndOwner, (0, showCmd, ptMin, ptMax, rect))

            Settings.setWindowPlacement.set(True)
            config.saveConfig()

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
            (pymclevel.alphaMaterials, 'terrain.png'),
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
    import json
    profile = getMinecraftProfileJSON()[getSelectedProfile()]
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
