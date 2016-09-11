#-# This is not an albow component.
#-# It should be moved back to MCEdit root folder, since it does not defines GUI base widgets.
import os
import logging

import panels
import pymclevel
import albow
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

    #-# Translation live update
        self.buildWidgets()

    def buildWidgets(self):
        for w in self.subwidgets:
            w.set_parent(None)

        helpColumn = []

        self.root.movementLabel = label = albow.Label(_("{0}/{1}/{2}/{3}/{4}/{5} to move").format(
            _(config.keys.forward.get()),
            _(config.keys.left.get()),
            _(config.keys.back.get()),
            _(config.keys.right.get()),
            _(config.keys.up.get()),
            _(config.keys.down.get()),
        ), doNotTranslate=True)
        label.anchor = 'whrt'
        label.align = 'r'
        helpColumn.append(label)

        def addHelp(text, dnt=False):
            label = albow.Label(text, doNotTranslate=dnt)
            label.anchor = 'whrt'
            label.align = "r"
            helpColumn.append(label)
            return label

        self.root.slowDownLabel = addHelp(_("{0} to slow down").format(_(config.keys.brake.get())), dnt=True)
        self.camCont = addHelp("Right-click to toggle camera control")
        self.toolDist = addHelp("Mousewheel to control tool distance")
        self.root.detailsLabel = addHelp(_("Hold {0} for details").format(_(config.keys.showBlockInfo.get())), dnt=True)

        self.helpColumn = helpColumn = albow.Column(helpColumn, align="r")
        helpColumn.topright = self.topright
        helpColumn.anchor = "whrt"
        # helpColumn.is_gl_container = True
        self.add(helpColumn)

        keysColumn = [albow.Label("")]
        buttonsColumn = [panels.ControlPanel.getHeader()]

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

        self.root.commandRow = commandRow = albow.HotkeyColumn(hotkeys, keysColumn, buttonsColumn, translateButtons=range(3))
        commandRow.anchor = 'lrh'

        sideColumn1 = self.mcedit.makeSideColumn1()
        sideColumn1.anchor = 'wh'
        spaceLabel = albow.Label("")
        spaceLabel.anchor = 'wh'
        sideColumn2 = self.mcedit.makeSideColumn2()
        sideColumn2.anchor = 'wh'

        contentRow = albow.Row((commandRow, albow.Column((sideColumn1, spaceLabel, sideColumn2))))
        contentRow.center = self.center
        contentRow.anchor = "rh"
        self.contentRow = contentRow
        self.add(contentRow)
        self.invalidate()
#        self.shrink_wrap()

    def set_update_ui(self, v):
        albow.Widget.set_update_ui(self, v)
        if v:
            self.buildWidgets()
    #-#

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

        self.root.fix_sticky_ctrl()

    def promptOpenAndLoad(self):
#!# Bad! But used to test the file chooser.
#        try:
            filename = mcplatform.askOpenFile(schematics=True)
            if filename:
                self.mcedit.loadFile(filename)
#        except Exception, e:
#            logging.error('Error during proptOpenAndLoad: {0!r}'.format(e))

    def createNewWorld(self):
        self.parent.createNewWorld()

    def createLoadButtonHandler(self, filename):
        return lambda: self.mcedit.loadFile(filename)
