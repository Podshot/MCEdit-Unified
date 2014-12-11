import os
import logging

import leveleditor
import pymclevel
import albow
import mceutils
import mcplatform
from config import config
from albow.translate import _


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
        # helpColumn.is_gl_container = True
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
        # self.mcedit.editor.mainViewport.setPerspective();
        self.mcedit.editor.drawStars()

    def idleevent(self, evt):
        self.mcedit.editor.doWorkUnit(onMenu=True)
        # self.invalidate()

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
