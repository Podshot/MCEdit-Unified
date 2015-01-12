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
import sys
from compass import CompassOverlay
from editortools.thumbview import ThumbView
from pymclevel.infiniteworld import SessionLockLost
from raycaster import TooFarException
import raycaster
import keys
import pygame
from albow.fields import FloatField
from mceutils import ChoiceButton, TextInputRow
from editortools.blockview import BlockButton

"""
leveleditor.py

Viewport objects for Camera and Chunk views, which respond to some keyboard and
mouse input. LevelEditor object responds to some other keyboard and mouse
input, plus handles the undo stack and implements tile entity editors for
chests, signs, and more. Toolbar object which holds instances of EditorTool
imported from editortools/

"""

import gc
import os
import math
import csv
import copy
import time
import numpy
from config import config
from config import DEF_ENC
import frustum
import logging
import glutils
import release
import mceutils
import platform
import functools
import editortools
import itertools
import mcplatform
import pymclevel
import renderer
import directories
import panels
import viewports

from math import isnan
from os.path import dirname, isdir
from datetime import datetime, timedelta
from collections import defaultdict, deque

from OpenGL import GL
from OpenGL import GLU

from albow import alert, ask, AttrRef, Button, Column, get_font, Grid, input_text, IntField, Menu, root, Row, \
    TableColumn, TableView, TextField, TimeField, Widget, CheckBox
from albow.controls import Label, SmallValueDisplay, ValueDisplay
from albow.dialogs import Dialog, QuickDialog, wrapped_label
from albow.openglwidgets import GLOrtho, GLViewport
from albow.translate import _
from pygame import display, event, key, mouse, MOUSEMOTION

from depths import DepthOffset
from editortools.operation import Operation
from editortools.chunk import GeneratorPanel
from glbackground import GLBackground, Panel
from glutils import gl, Texture
from mcplatform import askSaveFile, platform_open
from pymclevel.minecraft_server import alphanum_key  # ?????
from renderer import MCRenderer
from pymclevel.entity import Entity

try:
    import resource  # @UnresolvedImport
    resource.setrlimit(resource.RLIMIT_NOFILE, (500, -1))
except:
    pass

# Label = GLLabel


arch = platform.architecture()[0]


def DebugDisplay(obj, *attrs):
    col = []
    for attr in attrs:
        def _get(attr):
            return lambda: str(getattr(obj, attr))

        col.append(Row((Label(attr + " = "), ValueDisplay(width=600, get_value=_get(attr)))))

    col = Column(col, align="l")
    b = GLBackground()
    b.add(col)
    b.shrink_wrap()
    return b


# if self.defaultScale >= 0.5:
#            return super(ChunkViewport, self).drawCeiling()


class LevelEditor(GLViewport):
    anchor = "tlbr"
    __maxCopies = 32

    def __init__(self, mcedit):
        self.mcedit = mcedit
        rect = mcedit.rect
        GLViewport.__init__(self, rect)

        self.currentCopyPage = 0

        self.frames = 0
        self.frameStartTime = datetime.now()
        self.oldFrameStartTime = self.frameStartTime

        self.dragInProgress = False

        self.debug = 0
        self.debugString = ""

        self.testBoardKey = 0

        self.perfSamples = 5
        self.frameSamples = [timedelta(0, 0, 0)] * 5

        self.unsavedEdits = 0
        self.undoStack = []
        self.redoStack = []
        self.copyStack = []

        self.level = None

        self.cameraInputs = [0., 0., 0.]
        self.cameraPanKeys = [0., 0.]
        self.movements = [
            config.keys.left.get(),
            config.keys.right.get(),
            config.keys.forward.get(),
            config.keys.back.get(),
            config.keys.up.get(),
            config.keys.down.get()
        ]
        self.cameraPan = [
            config.keys.panLeft.get(),
            config.keys.panRight.get(),
            config.keys.panUp.get(),
            config.keys.panDown.get()
        ]
        self.different_keys = {
            "mouse1": "Mouse1",
            "mouse2": "Mouse2",
            "mouse3": "Button 3",
            "mouse4": "Scroll Up",
            "mouse5": "Scroll Down",
            "mouse6": "Button 4",
            "mouse7": "Button 5"
        }
        self.rightClickNudge = False
        self.root = self.get_root()
        self.cameraToolDistance = self.defaultCameraToolDistance

        self.createRenderers()

        self.sixteenBlockTex = self.genSixteenBlockTexture()

        # self.Font = Font("Verdana, Arial", 18)

        self.generateStars()

        self.optionsBar = Widget()

        mcEditButton = Button("MCEdit", action=self.showControls)
        viewDistanceDown = Button("<", action=self.decreaseViewDistance)
        viewDistanceUp = Button(">", action=self.increaseViewDistance)
        viewDistanceReadout = ValueDisplay(width=40, ref=AttrRef(self.renderer, "viewDistance"))

        chunksReadout = SmallValueDisplay(width=140,
                                          get_value=lambda: _("Chunks: %d") % len(self.renderer.chunkRenderers),
                                          tooltipText="Number of chunks loaded into the renderer.")
        fpsReadout = SmallValueDisplay(width=80,
                                       get_value=lambda: _("fps: %0.1f") % self.averageFPS,
                                       tooltipText="Frames per second.")
        cpsReadout = SmallValueDisplay(width=100,
                                       get_value=lambda: _("cps: %0.1f") % self.averageCPS,
                                       tooltipText="Chunks per second.")
        mbReadout = SmallValueDisplay(width=60,
                                      get_value=lambda: _("MBv: %0.1f") % (self.renderer.bufferUsage / 1000000.),
                                      tooltipText="Memory used for vertexes")


        def showViewOptions():
            col = []
            col.append(mceutils.CheckBoxLabel("Entities", fg_color=(0xff, 0x22, 0x22),
                                              ref=config.settings.drawEntities))
            col.append(
                mceutils.CheckBoxLabel("Items", fg_color=(0x22, 0xff, 0x22), ref=config.settings.drawItems))
            col.append(mceutils.CheckBoxLabel("TileEntities", fg_color=(0xff, 0xff, 0x22),
                                              ref=config.settings.drawTileEntities))
            col.append(mceutils.CheckBoxLabel("TileTicks", ref=config.settings.drawTileTicks))
            col.append(mceutils.CheckBoxLabel("Unpopulated Chunks", fg_color=renderer.TerrainPopulatedRenderer.color,
                                              ref=config.settings.drawUnpopulatedChunks))
            col.append(mceutils.CheckBoxLabel("Chunks Borders", fg_color=renderer.ChunkBorderRenderer.color,
                                              ref=config.settings.drawChunkBorders))

            col.append(mceutils.CheckBoxLabel("Sky", ref=config.settings.drawSky))
            col.append(mceutils.CheckBoxLabel("Fog", ref=config.settings.drawFog))
            col.append(mceutils.CheckBoxLabel("Ceiling",
                                              ref=config.settings.showCeiling))

            col.append(mceutils.CheckBoxLabel("Chunk Redraw", fg_color=(0xff, 0x99, 0x99),
                                              ref=config.settings.showChunkRedraw))

            col.append(mceutils.CheckBoxLabel("Hidden Ores",
                                              ref=config.settings.showHiddenOres,
                                              tooltipText="Check to show/hide specific ores using the settings below."))

            for ore in config.settings.hiddableOres.get():
                col.append(mceutils.CheckBoxLabel(self.level.materials[ore].name.replace(" Ore", ""),
                                                  ref=config.settings["showOre{}".format(ore)]))

            col = Column(col, align="r")

            d = QuickDialog()
            d.add(col)
            d.shrink_wrap()
            d.topleft = viewButton.bottomleft
            d.present(centered=False)

        viewButton = Button("Show...", action=showViewOptions)

        mbReadoutRow = Row((mbReadout, Label("")))
        readoutGrid = Grid(((chunksReadout, fpsReadout), (mbReadoutRow, cpsReadout), ), 0, 0)

        self.viewportButton = Button("Camera View", action=self.swapViewports,
                                     tooltipText="Shortcut: {0}".format(config.keys.toggleView.get()))

        self.recordUndoButton = mceutils.CheckBoxLabel("Record Undo", ref=AttrRef(self, 'recordUndo'))

        row = (mcEditButton, viewDistanceDown, Label("View Distance:"), viewDistanceReadout, viewDistanceUp,
               readoutGrid, viewButton, self.viewportButton, self.recordUndoButton)

        # row += (Button("CR Info", action=self.showChunkRendererInfo), )
        row = Row(row)
        self.add(row)
        self.statusLabel = ValueDisplay(width=self.width, ref=AttrRef(self, "statusText"))

        self.mainViewport = viewports.CameraViewport(self)
        self.chunkViewport = viewports.ChunkViewport(self)

        self.mainViewport.height -= row.height

        self.mainViewport.height -= self.statusLabel.height
        self.statusLabel.bottom = self.bottom
        self.statusLabel.anchor = "blrh"

        self.add(self.statusLabel)

        self.viewportContainer = Widget(is_gl_container=True, anchor="tlbr")
        self.viewportContainer.top = row.bottom
        self.viewportContainer.size = self.mainViewport.size
        self.add(self.viewportContainer)

        config.settings.viewMode.addObserver(self)
        config.settings.undoLimit.addObserver(self)

        self.reloadToolbar()

        self.currentTool = None
        self.toolbar.selectTool(0)

        self.controlPanel = panels.ControlPanel(self)
        self.controlPanel.topleft = mcEditButton.bottomleft

    def __del__(self):
        self.deleteAllCopiedSchematics()

    _viewMode = None

    @property
    def viewMode(self):
        return self._viewMode

    @viewMode.setter
    def viewMode(self, val):
        if val == self._viewMode:
            return
        ports = {"Chunk": self.chunkViewport, "Camera": self.mainViewport}
        for p in ports.values():
            p.set_parent(None)
        port = ports.get(val, self.mainViewport)
        self.mainViewport.mouseLookOff()
        self._viewMode = val

        if val == "Camera":
            x, y, z = self.chunkViewport.cameraPosition
            try:
                h = self.level.heightMapAt(int(x), int(z))
            except:
                h = 0
            y = max(self.mainViewport.cameraPosition[1], h + 2)
            self.mainViewport.cameraPosition = x, y, z
            # self.mainViewport.yaw = 180.0
            # self.mainViewport.pitch = 90.0
            self.mainViewport.cameraVector = self.mainViewport._cameraVector()
            self.renderer.overheadMode = False
            self.viewportButton.text = "Chunk View"
        else:
            x, y, z = self.mainViewport.cameraPosition
            self.chunkViewport.cameraPosition = x, y, z
            self.renderer.overheadMode = True
            self.viewportButton.text = "Camera View"

        self.viewportContainer.add(port)
        self.currentViewport = port
        self.chunkViewport.size = self.mainViewport.size = self.viewportContainer.size
        self.renderer.loadNearbyChunks()

    def swapViewports(self):
        if config.settings.viewMode.get() == "Chunk":
            config.settings.viewMode.set("Camera")
        else:
            config.settings.viewMode.set("Chunk")

    def addCopiedSchematic(self, sch):
        self.copyStack.insert(0, sch)
        if len(self.copyStack) > self.maxCopies:
            self.deleteCopiedSchematic(self.copyStack[-1])
        self.updateCopyPanel()

    def _deleteSchematic(self, sch):
        if hasattr(sch, 'close'):
            sch.close()
        if sch.filename and os.path.exists(sch.filename):
            os.remove(sch.filename)

    def deleteCopiedSchematic(self, sch):
        self._deleteSchematic(sch)
        self.copyStack = [s for s in self.copyStack if s is not sch]
        self.updateCopyPanel()

    def deleteAllCopiedSchematics(self):
        for s in self.copyStack:
            self._deleteSchematic(s)

    copyPanel = None

    def updateCopyPanel(self):
        if self.copyPanel:
            self.copyPanel.set_parent(None)
        if 0 == len(self.copyStack):
            return

        self.copyPanel = self.createCopyPanel()
        self.copyPanel.right = self.mainViewport.right
        self.copyPanel.top = self.subwidgets[0].bottom + 2
        self.add(self.copyPanel)

    thumbCache = None
    fboCache = None

    def __getMaxCopies(self):
        return config.settings.maxCopies.get() or self.__maxCopies

    def __setMaxCopies(self, *args, **kwargs):
        return

    def __delMaxCopies(self):
        return

    maxCopies = property(__getMaxCopies, __setMaxCopies, __delMaxCopies, "Copy stack size.")

    def createCopyPanel(self):
        panel = GLBackground()
        panel.bg_color = (0.0, 0.0, 0.0, 0.5)
        panel.pages = []
        if len(self.copyStack) > self.maxCopies:
            for sch in self.copyStack[self.maxCopies:]:
                self.deleteCopiedSchematic(sch)

        prevButton = Button("Previous Page")

        self.thumbCache = thumbCache = self.thumbCache or {}
        self.fboCache = self.fboCache or {}
        for k in self.thumbCache.keys():
            if k not in self.copyStack:
                del self.thumbCache[k]

        inner_height = 0
        itemNo = Label("#%s"%("W" * len("%s"%self.maxCopies)), doNotTranslate=True)
        fixedwidth = 0 + itemNo.width
        del itemNo

        def createOneCopyPanel(sch, i):
            p = GLBackground()
            p.bg_color = (0.0, 0.0, 0.0, 0.4)
            itemNo = Label("#%s%s"%(" " * (len("%s"%self.maxCopies) - len("%s"%(i + 1))), (i + 1)), doNotTranslate=True)
            thumb = thumbCache.get(sch)
            if thumb is None:
                thumb = ThumbView(sch)
                thumb.mouse_down = lambda e: self.pasteSchematic(sch)
                thumb.tooltipText = "Click to import this item."
                thumbCache[sch] = thumb
            self.addWorker(thumb.renderer)
            deleteButton = Button("Delete", action=lambda: (self.deleteCopiedSchematic(sch)))
            saveButton = Button("Save", action=lambda: (self.exportSchematic(sch)))
            sizeLabel = Label("{0} x {1} x {2}".format(sch.Length, sch.Width, sch.Height))

            r = Row((itemNo, thumb, Column((sizeLabel, Row((deleteButton, saveButton))), spacing=5)))
            p.add(r)
            itemNo.width = 0 + fixedwidth
            p.shrink_wrap()
            return p

        page = []
        for i in range(len(self.copyStack)):
            sch = self.copyStack[i]
            p = createOneCopyPanel(sch, i)
            if self.netherPanel is None:
                bottom = pygame.display.get_surface().get_height() - 60
            else:
                bottom = self.netherPanel.top - 2
            if inner_height + p.height + 2 <= bottom - (self.subwidgets[0].bottom + 2) - prevButton.height - (panel.margin * 2):
                inner_height += p.height + 2
                page.append(p)
            else:
                inner_height = p.height
                panel.pages.append(Column(page, spacing=2, align="l"))
                panel.pages[-1].shrink_wrap()
                page = [p]
        if page != []:
            panel.pages.append(Column(page, spacing=2, align="l"))
            panel.pages[-1].shrink_wrap()

        prevButton.shrink_wrap()
        self.currentCopyPage = min(self.currentCopyPage, len(panel.pages) - 1)
        col = Column([panel.pages[self.currentCopyPage]], spacing=2, align="l")
        col.shrink_wrap()

        def changeCopyPage(this, delta):
            if delta > 0:
                m = min
                a = self.currentCopyPage + delta, len(this.pages) -1
            elif delta < 0:
                m = max
                a = self.currentCopyPage - 1, 0
            else:
                return
            self.currentCopyPage = m(*a)
            for i in range(len(this.pages)):
                page = this.pages[i]
                if i == self.currentCopyPage:
                    page.visible = True
                    this.subwidgets[0].subwidgets[1].subwidgets[0] = page
                    page.parent = this.subwidgets[0].subwidgets[1]
                else:
                    page.visible = False
            page = this.pages[self.currentCopyPage]
            pb = this.subwidgets[0].subwidgets[0].subwidgets[0]
            nb = this.subwidgets[0].subwidgets[0].subwidgets[1]
            if self.currentCopyPage == 0:
                pb.enabled = False
                nb.enabled = True
            elif 0 < self.currentCopyPage < len(this.pages) -1:
                pb.enabled = True
                nb.enabled = True
            elif self.currentCopyPage == len(this.pages) -1:
                pb.enabled = True
                nb.enabled = False
            this.subwidgets[0].subwidgets[1].shrink_wrap()
            this.subwidgets[0].shrink_wrap()
            this.shrink_wrap()
            this.width = 0 + this.orgwidth

        nextButton = Button("Next Page", action=lambda: changeCopyPage(panel, 1), width=prevButton.width, height=prevButton.height)
        prevButton.action=lambda: changeCopyPage(panel, -1)
        if len(panel.pages) < 2:
            prevButton.enabled = False
            nextButton.enabled = False
        elif self.currentCopyPage == 0:
            prevButton.enabled = False
            nextButton.enabled = True
        elif 0 < self.currentCopyPage < len(panel.pages) -1:
            prevButton.enabled = True
            nextButton.enabled = True
        elif self.currentCopyPage == len(panel.pages) -1:
            prevButton.enabled = True
            nextButton.enabled = False
        btns = Row((prevButton, nextButton), spacing=2, align='c')
        btns.shrink_wrap()
        mainCol = Column((btns, col), spacing=2, align='c')
        mainCol.shrink_wrap()
        panel.add(mainCol)

        panel.shrink_wrap()
        panel.anchor = "whrt"
        panel.orgwidth = 0 + panel.width
        return panel

    @mceutils.alertException
    def showAnalysis(self, schematic):
        self.analyzeBox(schematic, schematic.bounds)

    def analyzeBox(self, level, box):
        entityCounts = defaultdict(int)
        tileEntityCounts = defaultdict(int)
        types = numpy.zeros(65536, dtype='uint32')

        def _analyzeBox():
            i = 0
            for (chunk, slices, point) in level.getChunkSlices(box):
                i += 1
                yield i, box.chunkCount
                blocks = numpy.array(chunk.Blocks[slices], dtype='uint16')
                blocks |= (numpy.array(chunk.Data[slices], dtype='uint16') << 12)
                b = numpy.bincount(blocks.ravel())
                types[:b.shape[0]] += b

                for ent in chunk.getEntitiesInBox(box):
                    entID = Entity.getId(ent["id"].value)
                    if ent["id"].value == "Item":
                        v = pymclevel.items.items.findItem(ent["Item"]["id"].value,
                                                           ent["Item"]["Damage"].value).name
                    else:
                        v = ent["id"].value
                    entityCounts[(entID, v)] += 1
                for ent in chunk.getTileEntitiesInBox(box):
                    tileEntityCounts[ent["id"].value] += 1

        with mceutils.setWindowCaption("ANALYZING - "):
            mceutils.showProgress(_("Analyzing {0} blocks...").format(box.volume), _analyzeBox(), cancel=True)

        entitySum = numpy.sum(entityCounts.values())
        tileEntitySum = numpy.sum(tileEntityCounts.values())
        presentTypes = types.nonzero()

        blockCounts = sorted([(level.materials[t & 0xfff, t >> 12], types[t]) for t in presentTypes[0]])

        blockRows = [("", "", ""), (box.volume, "<Blocks>", "")]
        rows = list(blockRows)
        rows.extend([[count ,block.name, ("({0}:{1})".format(block.ID, block.blockData))] for block, count in blockCounts])
        #rows.sort(key=lambda x: alphanum_key(x[2]), reverse=True)

        def extendEntities():
            if entitySum:
                rows.extend([("", "", ""), (entitySum, "<Entities>", "")])
                rows.extend([(count, id[1], id[0]) for (id, count) in sorted(entityCounts.iteritems())])
            if tileEntitySum:
                rows.extend([("", "", ""), (tileEntitySum, "<TileEntities>", "")])
                rows.extend([(count, id, "") for (id, count) in sorted(tileEntityCounts.iteritems())])

        extendEntities()

        columns = [
            TableColumn("Count", 100),
            TableColumn("Name", 400),
            TableColumn("ID", 120),
        ]
        table = TableView(columns=columns)
        table.sortColumn = columns[2]
        table.reverseSort = True

        def sortColumn(col):
            if table.sortColumn == col:
                table.reverseSort = not table.reverseSort
            else:
                table.reverseSort = (col.title == "Count")
            colnum = columns.index(col)

            def sortKey(x):
                val = x[colnum]
                if isinstance(val, basestring):
                    alphanum_key(val)
                return val

            blockRows.sort(key=sortKey,
                           reverse=table.reverseSort)
            table.sortColumn = col
            rows[:] = blockRows
            extendEntities()

        table.num_rows = lambda: len(rows)
        table.row_data = lambda i: rows[i]
        table.row_is_selected = lambda x: False
        table.click_column_header = sortColumn

        tableBacking = Widget()
        tableBacking.add(table)
        tableBacking.shrink_wrap()

        def saveToFile():
            dt = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            filename = askSaveFile(directories.docsFolder,
                                   title='Save analysis...',
                                   defaultName=self.level.displayName + "_analysis_" + dt + ".txt",
                                   filetype='Comma Separated Values\0*.txt\0\0',
                                   suffix="txt",
            )

            if filename:
                try:
                    csvfile = csv.writer(open(filename, "wb"))
                except Exception, e:
                    alert(str(e))
                else:
                    csvfile.writerows(rows)

        saveButton = Button("Save to file...", action=saveToFile)
        col = Column((Label("Analysis"), tableBacking, saveButton))
        Dialog(client=col, responses=["OK"]).present()

    def exportSchematic(self, schematic):
        filename = mcplatform.askSaveSchematic(
            directories.schematicsDir, self.level.displayName, "schematic")

        if filename:
            schematic.saveToFile(filename)

    def getLastCopiedSchematic(self):
        if len(self.copyStack) == 0:
            return None
        return self.copyStack[0]

    toolbar = None

    def YesNoWidget(self, msg):
        self.user_yon_response = None
        self.yon = Widget()
        self.yon.bg_color = (0.0, 0.0, 0.6)
        label = Label(msg)
        ybutton = Button("Yes", action=self.yes)
        nbutton = Button("No", action=self.no)
        col = Column((label, ybutton, nbutton))
        self.yon.add(col)
        self.yon.shrink_wrap()
        self.yon.present()
        waiter = None
        while waiter is None:
            if self.user_yon_response is not None:
                waiter = True
                return self.user_yon_response

    def yes(self):
        self.yon.dismiss()
        self.user_yon_response = True

    def no(self):
        self.yon.dismiss()
        self.user_yon_response = False

    def addExternalWidget(self, provided_fields):

        def addNumField(wid, name, val, minimum=None, maximum=None, increment=0.1):
            if isinstance(val, float):
                ftype = FloatField
                if isinstance(increment, int):
                    increment = float(increment)
            else:
                ftype = IntField
                if increment == 0.1:
                    increment = 1
                if isinstance(increment, float):
                    increment = int(round(increment))

            if minimum == maximum:
                minimum = None
                maximum = None

            field = ftype(value=val, width=100, min=minimum, max=maximum)
            field._increment = increment
            wid.inputDict[name] = AttrRef(field, 'value')
            return Row([Label(name), field])

        widget = Widget()
        rows = []
        cols = []
        max_height = self.mainViewport.height
        widget.inputDict = {}
        for inputName, inputType in provided_fields:
            if isinstance(inputType, tuple):
                if isinstance(inputType[0], (int, long, float)):
                    if len(inputType) == 2:
                        min, max = inputType
                        val = min
                        increment = 0.1
                    elif len(inputType) == 3:
                        val, min, max = inputType
                        increment = 0.1
                    elif len(inputType) == 4:
                        val, min, max, increment = inputType
                    rows.append(addNumField(widget, inputName, val, min, max, increment))

                if isinstance(inputType[0], (str, unicode)):
                    isChoiceButton = False

                    if inputType[0] == "string":
                        keywords = []
                        width = None
                        value = None
                        for keyword in inputType:
                            if isinstance(keyword, (str, unicode)) and keyword != "string":
                                keywords.append(keyword)
                        for word in keywords:
                            splitWord = word.split('=')
                            if len(splitWord) > 1:
                                v = None
                                key = None

                                try:
                                    v = int(splitWord[1])
                                except:
                                    pass

                                key = splitWord[0]
                                if v is not None:
                                    if key == "lines":
                                        lin = v
                                    elif key == "width":
                                        width = v
                                else:
                                    if key == "value":
                                        value = splitWord[1]
                        if val is None:
                            value = ""
                        if width is None:
                            width = 200

                        field = TextField(value=value,width=width)
                        widget.inputDict[inputName] = AttrRef(field, 'value')
                        row = Row((Label(inputName), field))
                        rows.append(row)
                    else:
                        isChoiceButton = True

                    if isChoiceButton:
                        choiceButton = ChoiceButton(map(str, inputType))
                        widget.inputDict[inputName] = AttrRef(choiceButton, 'selectedChoice')
                        rows.append(Row((Label(inputName), choiceButton)))
            elif isinstance(inputType, bool):
                chkbox = CheckBox(value=inputType)
                widget.inputDict[inputName] = AttrRef(chkbox, 'value')
                row = Row((Label(inputName),chkbox))
                rows.append(row)

            elif isinstance(inputType, (int, float)):
                rows.append(addNumField(widget, inputName, inputType))

            elif inputType == "blocktype" or isinstance(inputType, pymclevel.materials.Block):
                blockButton = BlockButton(self.level.materials)
                if isinstance(inputType, pymclevel.materials.Block):
                    blockButton.blockInfo = inputType
                row = Column((Label(inputName), blockButton))
                widget.inputDict[inputName] = AttrRef(blockButton, 'blockInfo')

                rows.append(row)
            elif inputType == "label":
                rows.append(wrapped_label(inputName, 50))

            elif inputType == "string":
                input = None
                if input != None:
                    size = input
                else:
                    size = 200
                field = TextField(value="")
                row = TextInputRow(inputName, ref=AttrRef(field, 'value'), width=size)
                widget.inputDict[inputName] = AttrRef(field, 'value')
                rows.append(row)
            else:
                raise ValueError(("Unknown option type", inputType))
        height = sum(r.height for r in rows)

        if height > max_height:
            h = 0
            for i, r in enumerate(rows):
                h += r.height
                if h > height / 2:
                    break
            cols.append(Column(rows[:i]))
            rows = rows[i:]
        if len(rows):
            cols.append(Column(rows))

        if len(cols):
            widget.add(Row(cols))

        widget.shrink_wrap()
        result = Dialog(widget, ["Ok", "Cancel"]).present()
        if result == "Ok":
            return dict((k, v.get()) for k, v in widget.inputDict.iteritems())
        else:
            return "user canceled"


    def Notify(self, msg):
        ask(msg, ["Close"], cancel=0)

    def reloadToolbar(self):
        self.toolbar = EditorToolbar(self, tools=[editortools.SelectionTool(self),
                                                  editortools.BrushTool(self),
                                                  editortools.CloneTool(self),
                                                  editortools.FillTool(self),
                                                  editortools.FilterTool(self),
                                                  editortools.ConstructionTool(self),
                                                  editortools.PlayerPositionTool(self),
                                                  editortools.PlayerSpawnPositionTool(self),
                                                  editortools.ChunkTool(self),
                                                  editortools.NBTExplorerTool(self),
        ])

        self.toolbar.anchor = 'bwh'
        self.add(self.toolbar)
        self.toolbar.bottom = self.viewportContainer.bottom  # bottoms are touching
        self.toolbar.centerx = self.centerx

    is_gl_container = True

    maxDebug = 1
    allBlend = False
    onscreen = True
    mouseEntered = True
    defaultCameraToolDistance = 10
    mouseSensitivity = 5.0

    longDistanceMode = config.settings.longDistanceMode.property()

    def genSixteenBlockTexture(self):
        has12 = GL.glGetString(GL.GL_VERSION) >= "1.2"
        if has12:
            maxLevel = 2
            mode = GL.GL_LINEAR_MIPMAP_NEAREST
        else:
            maxLevel = 1
            mode = GL.GL_LINEAR

        def makeSixteenBlockTex():
            darkColor = (0x30, 0x30, 0x30, 0xff)
            lightColor = (0x80, 0x80, 0x80, 0xff)
            w, h, = 256, 256

            teximage = numpy.zeros((w, h, 4), dtype='uint8')
            teximage[:] = 0xff
            teximage[:, ::16] = lightColor
            teximage[::16, :] = lightColor
            teximage[:2] = darkColor
            teximage[-1:] = darkColor
            teximage[:, -1:] = darkColor
            teximage[:, :2] = darkColor
            # GL.glTexParameter(GL.GL_TEXTURE_2D,
            #                  GL.GL_TEXTURE_MIN_FILTER,
            #                  GL.GL_NEAREST_MIPMAP_NEAREST),
            GL.glTexParameter(GL.GL_TEXTURE_2D,
                              GL.GL_TEXTURE_MAX_LEVEL,
                              maxLevel - 1)

            for lev in range(maxLevel):
                step = 1 << lev
                if lev:
                    teximage[::16] = 0xff
                    teximage[:, ::16] = 0xff
                    teximage[:2] = darkColor
                    teximage[-1:] = darkColor
                    teximage[:, -1:] = darkColor
                    teximage[:, :2] = darkColor

                GL.glTexImage2D(GL.GL_TEXTURE_2D, lev, GL.GL_RGBA8,
                                w / step, h / step, 0,
                                GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
                                teximage[::step, ::step].ravel())

        return Texture(makeSixteenBlockTex, mode)

    def showProgress(self, *a, **kw):
        return mceutils.showProgress(*a, **kw)

    def drawConstructionCube(self, box, color, texture=None):
        if texture is None:
            texture = self.sixteenBlockTex
        # textured cube faces

        GL.glEnable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(False)

        # edges within terrain
        GL.glDepthFunc(GL.GL_GREATER)
        try:
            GL.glColor(color[0], color[1], color[2], max(color[3], 0.35))
        except IndexError:
            raise
        GL.glLineWidth(1.0)
        mceutils.drawCube(box, cubeType=GL.GL_LINE_STRIP)

        # edges on or outside terrain
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glColor(color[0], color[1], color[2], max(color[3] * 2, 0.75))
        GL.glLineWidth(2.0)
        mceutils.drawCube(box, cubeType=GL.GL_LINE_STRIP)

        GL.glDepthFunc(GL.GL_LESS)
        GL.glColor(color[0], color[1], color[2], color[3])
        GL.glDepthFunc(GL.GL_LEQUAL)
        mceutils.drawCube(box, texture=texture, selectionBox=True)
        GL.glDepthMask(True)

        GL.glDisable(GL.GL_BLEND)
        GL.glDisable(GL.GL_DEPTH_TEST)

    def loadFile(self, filename):
        """
        Called when the user picks a level using Load World or Open File.
        """
        if self.level and self.unsavedEdits > 0:
            resp = ask("Save unsaved edits before loading?", ["Cancel", "Don't Save", "Save"], default=2, cancel=0)
            if resp == "Cancel":
                return
            if resp == "Save":
                self.saveFile()

        self.freezeStatus(_("Loading ") + filename)
        if self.level:
            self.level.close()

        try:
            level = pymclevel.fromFile(filename)
        except Exception, e:
            logging.exception(
                'Wasn\'t able to open a file {file => %s}' % filename
            )
            alert(_(u"I don't know how to open {0}:\n\n{1!r}").format(filename, e))
            self.closeEditor()
            return

        assert level

        self.mcedit.addRecentWorld(filename)

        try:
            self.currentViewport.cameraPosition = level.getPlayerPosition()

            y, p = level.getPlayerOrientation()
            if p == -90.0:
                p += 0.000000001
            if p == 90.0:
                p -= 0.000000001
            self.mainViewport.yaw, self.mainViewport.pitch = y, p

            pdim = level.getPlayerDimension()
            if pdim and pdim in level.dimensions:
                level = level.dimensions[pdim]

        except (KeyError, pymclevel.PlayerNotFound):  # TagNotFound
            # player tag not found, maybe
            try:
                self.currentViewport.cameraPosition = level.playerSpawnPosition()
            except KeyError:  # TagNotFound
                self.currentViewport.cameraPosition = numpy.array((0, level.Height * 0.75, 0))
                self.mainViewport.yaw = -45.
                self.mainViewport.pitch = 0.0

        self.removeNetherPanel()

        self.loadLevel(level)

        self.renderer.position = self.currentViewport.cameraPosition
        self.renderer.loadNearbyChunks()

    def loadLevel(self, level):
        """
        Called to load a level, world, or dimension into the editor and display it in the viewport.
        """
        self.level = level

        self.toolbar.removeToolPanels()
        self.selectedChunks = set()

        self.mainViewport.stopMoving()

        self.renderer.level = level
        self.addWorker(self.renderer)

        self.undoStack = []
        self.afterSaveUndoStack = []
        self.redoStack = []
        self.recordUndo = True
        self.clearUnsavedEdits()

        self.initWindowCaption()
        self.selectionTool.selectNone()

        [t.levelChanged() for t in self.toolbar.tools]
        if "select" not in str(self.currentTool):
            self.toolbar.selectTool(0)

        if isinstance(self.level, pymclevel.MCInfdevOldLevel):
            if self.level.parentWorld:
                dimensions = self.level.parentWorld.dimensions
            else:
                dimensions = self.level.dimensions

            dimensionsMenu = [("Overworld", "0")]
            dimensionsMenu += [
                (pymclevel.MCAlphaDimension.dimensionNames.get(dimNo, "Dimension {0}".format(dimNo)), str(dimNo)) for
                dimNo in dimensions]
            for dim, name in pymclevel.MCAlphaDimension.dimensionNames.iteritems():
                if dim not in dimensions:
                    dimensionsMenu.append((name, str(dim)))

            menu = Menu("", dimensionsMenu)

            def presentMenu():
                x, y = self.netherPanel.topleft
                dimIdx = menu.present(self, (x, y - menu.height))
                if dimIdx == -1:
                    return
                dimNo = int(dimensionsMenu[dimIdx][1])
                self.gotoDimension(dimNo)

            self.netherPanel = Panel()
            self.netherButton = Button("Goto Dimension", action=presentMenu)
            self.netherPanel.add(self.netherButton)
            self.netherPanel.shrink_wrap()
            self.netherPanel.bottomright = self.viewportContainer.bottomright
            self.netherPanel.anchor = "brwh"
            self.add(self.netherPanel)

        if len(list(self.level.allChunks)) == 0:
            resp = ask(
                "It looks like this level is completely empty!  You'll have to create some chunks before you can get started.",
                responses=["Create Chunks", "Cancel"])
            if resp == "Create Chunks":
                x, y, z = self.mainViewport.cameraPosition
                box = pymclevel.BoundingBox((x - 128, 0, z - 128), (256, self.level.Height, 256))
                self.selectionTool.setSelection(box)
                self.toolbar.selectTool(8)
                self.toolbar.tools[8].createChunks()
                self.mainViewport.cameraPosition = (x, self.level.Height, z)

    def removeNetherPanel(self):
        if self.netherPanel:
            self.remove(self.netherPanel)
            self.netherPanel = None

    @mceutils.alertException
    def gotoEarth(self):
        assert self.level.parentWorld
        self.removeNetherPanel()
        self.loadLevel(self.level.parentWorld)

        x, y, z = self.mainViewport.cameraPosition
        self.mainViewport.cameraPosition = [x * 8, y, z * 8]

    @mceutils.alertException
    def gotoNether(self):
        self.removeNetherPanel()
        x, y, z = self.mainViewport.cameraPosition
        self.mainViewport.cameraPosition = [x / 8, y, z / 8]
        self.loadLevel(self.level.getDimension(-1))

    def gotoDimension(self, dimNo):
        if dimNo == self.level.dimNo:
            return
        elif dimNo == -1 and self.level.dimNo == 0:
            self.gotoNether()
        elif dimNo == 0 and self.level.dimNo == -1:
            self.gotoEarth()
        else:
            self.removeNetherPanel()
            if dimNo:
                if dimNo == 1:
                    self.mainViewport.cameraPosition = (0, 96, 0)
                self.loadLevel(self.level.getDimension(dimNo))

            else:
                self.loadLevel(self.level.parentWorld)

    netherPanel = None

    def initWindowCaption(self):
        filename = self.level.filename
        s = os.path.split(filename)
        title = os.path.split(s[0])[1] + os.sep + s[1] + _(u" - MCEdit ~ ") + release.get_version()
        if DEF_ENC != "UTF-8":
            title = title.encode('utf-8')
        display.set_caption(title)

    @mceutils.alertException
    def reload(self):
        filename = self.level.filename
        # self.discardAllChunks()
        self.loadFile(filename)

    @mceutils.alertException
    def saveFile(self):
        with mceutils.setWindowCaption("SAVING - "):
            if isinstance(self.level, pymclevel.ChunkedLevelMixin):  # xxx relight indev levels?
                level = self.level
                if level.parentWorld:
                    level = level.parentWorld

                if hasattr(level, 'checkSessionLock'):
                    try:
                        level.checkSessionLock()
                    except SessionLockLost, e:
                        alert(e.message + _("\n\nYour changes cannot be saved."))
                        return

                for level in itertools.chain(level.dimensions.itervalues(), [level]):

                    if "Canceled" == mceutils.showProgress("Lighting chunks", level.generateLightsIter(), cancel=True):
                        return

                    if self.level == level:
                        if isinstance(level, pymclevel.MCInfdevOldLevel):
                            needsRefresh = [c.chunkPosition for c in level._loadedChunkData.itervalues() if c.dirty]
                            needsRefresh.extend(level.unsavedWorkFolder.listChunks())
                        else:
                            needsRefresh = [c for c in level.allChunks if level.getChunk(*c).dirty]
                        #xxx change MCInfdevOldLevel to monitor changes since last call
                        self.invalidateChunks(needsRefresh)

            self.freezeStatus("Saving...")
            chunks = self.level.chunkCount
            count = [0]
            def copyChunks():
                for i in self.level.saveInPlaceGen():
                    count[0] += 1
                    yield count[0],chunks

            if "Canceled" == mceutils.showProgress("Copying chunks", copyChunks(), cancel=True):
                return

        self.recordUndo = True
        self.clearUnsavedEdits(True)

    def addUnsavedEdit(self):
        if self.unsavedEdits:
            self.remove(self.saveInfoBackground)

        self.unsavedEdits += 1

        self.saveInfoBackground = GLBackground()
        self.saveInfoBackground.bg_color = (0.0, 0.0, 0.0, 0.6)

        self.saveInfoLabel = Label(self.saveInfoLabelText)
        self.saveInfoLabel.anchor = "blwh"

        self.saveInfoBackground.add(self.saveInfoLabel)
        self.saveInfoBackground.shrink_wrap()

        self.saveInfoBackground.left = 50
        self.saveInfoBackground.bottom = self.toolbar.toolbarRectInWindowCoords()[1]

        self.add(self.saveInfoBackground)
        self.saveInfoBackground = self.saveInfoBackground

    def removeUnsavedEdit(self):
        self.unsavedEdits -= 1
        self.remove(self.saveInfoBackground)
        if self.unsavedEdits:
            self.saveInfoBackground = GLBackground()
            self.saveInfoBackground.bg_color = (0.0, 0.0, 0.0, 0.6)

            self.saveInfoLabel = Label(self.saveInfoLabelText)
            self.saveInfoLabel.anchor = "blwh"

            self.saveInfoBackground.add(self.saveInfoLabel)
            self.saveInfoBackground.shrink_wrap()

            self.saveInfoBackground.left = 50
            self.saveInfoBackground.bottom = self.toolbar.toolbarRectInWindowCoords()[1]

            self.add(self.saveInfoBackground)
            self.saveInfoBackground = self.saveInfoBackground

    def clearUnsavedEdits(self, saving=False):
        if self.unsavedEdits:
            self.unsavedEdits = 0
            self.remove(self.saveInfoBackground)
            if saving:
                for operation in self.undoStack:
                    self.afterSaveUndoStack.append(operation)
                self.undoStack = []

    @property
    def saveInfoLabelText(self):
        if self.unsavedEdits == 0:
            return ""
        return _("{0} unsaved edits.  {1} to save.  {2}").format(self.unsavedEdits,
                                                                   config.keys.save.get(),
                                                                   "" if self.recordUndo else "(UNDO DISABLED)")

    @property
    def viewDistanceLabelText(self):
        return _("View Distance ({0})").format(self.renderer.viewDistance)

    def createRenderers(self):
        self.renderer = MCRenderer()

        self.workers = deque()

        if self.level:
            self.renderer.level = self.level
            self.addWorker(self.renderer)

        self.renderer.viewDistance = int(config.settings.viewDistance.get())

    def addWorker(self, chunkWorker):
        if chunkWorker not in self.workers:
            self.workers.appendleft(chunkWorker)

    def removeWorker(self, chunkWorker):
        if chunkWorker in self.workers:
            self.workers.remove(chunkWorker)

    def getFrameDuration(self):
        frameDuration = timedelta(0, 1, 0) / self.renderer.targetFPS
        return frameDuration

    lastRendererDraw = datetime.now()

    def idleevent(self, e):
        if any(self.cameraInputs) or any(self.cameraPanKeys):
            self.postMouseMoved()

        if (self.renderer.needsImmediateRedraw or
                (self.renderer.needsRedraw and datetime.now() - self.lastRendererDraw > timedelta(0, 1, 0) / 3)):
            self.invalidate()
            self.lastRendererDraw = datetime.now()
        if self.renderer.needsImmediateRedraw:
            self.invalidate()

        if self.root.bonus_draw_time < 1:
            frameDuration = self.getFrameDuration()

            while frameDuration > (datetime.now() - self.frameStartTime):
                self.doWorkUnit()
            else:
                return

        self.doWorkUnit()

    def activeevent(self, evt):
        self.mainViewport.activeevent(evt)

        if evt.state & 0x4:  # minimized
            if evt.gain == 0:
                logging.debug("Offscreen")
                self.onscreen = False

                self.mouseLookOff()

            else:
                logging.debug("Onscreen")
                self.onscreen = True
                self.invalidate()

        if evt.state & 0x1:  # mouse enter/leave
            if evt.gain == 0:
                logging.debug("Mouse left")
                self.mouseEntered = False
                self.mouseLookOff()

            else:
                logging.debug("Mouse entered")
                self.mouseEntered = True

    def swapDebugLevels(self):
        self.debug += 1
        if self.debug > self.maxDebug:
            self.debug = 0

        if self.debug:
            self.showDebugPanel()
        else:
            self.hideDebugPanel()

    def showDebugPanel(self):
        dp = GLBackground()
        debugLabel = ValueDisplay(width=1100, ref=AttrRef(self, "debugString"))
        inspectLabel = ValueDisplay(width=1100, ref=AttrRef(self, "inspectionString"))
        dp.add(Column((debugLabel, inspectLabel)))
        dp.shrink_wrap()
        dp.bg_color = (0, 0, 0, 0.6)
        self.add(dp)
        dp.top = 40
        self.debugPanel = dp

    def hideDebugPanel(self):
        self.remove(self.debugPanel)

    @property
    def statusText(self):
        try:
            return self.currentTool.statusText
        except Exception, e:
            return repr(e)

    def toolMouseDown(self, evt, f):  # xxx f is a tuple
        if self.level:
            if None != f:
                (focusPoint, direction) = f
                if focusPoint is not None and direction is not None:
                    self.currentTool.mouseDown(evt, focusPoint, direction)

    def toolMouseUp(self, evt, f):  # xxx f is a tuple
        if self.level:
            if None != f:
                (focusPoint, direction) = f
                if focusPoint is not None and direction is not None:
                    self.currentTool.mouseUp(evt, focusPoint, direction)

    def mouse_up(self, evt):
        button = keys.remapMouseButton(evt.button)
        evt.dict['keyname'] = "mouse{}".format(button)
        self.key_up(evt)

    def mouse_drag(self, evt):
        # if 'button' not in evt.dict or evt.button != 1:
        #    return
        if self.level:
            f = self.blockFaceUnderCursor
            if None != f:
                (focusPoint, direction) = f
                self.currentTool.mouseDrag(evt, focusPoint, direction)

    def mouse_down(self, evt):
        button = keys.remapMouseButton(evt.button)

        evt.dict['keyname'] = "mouse{}".format(button)
        self.mcedit.focus_switch = self
        self.turn_off_focus()
        self.key_down(evt)

    '''
    def mouseDragOn(self):

        x,y = mouse.get_pos(0)
        if None != self.currentOperation:
            self.dragInProgress = True
            self.dragStartPoint = (x,y)
            self.currentOperation.dragStart(x,y)

    def mouseDragOff(self):
        if self.dragInProgress:
            self.dragInProgress = False
            '''

    def mouseLookOff(self):
        self.mouseWasCaptured = False
        self.mainViewport.mouseLookOff()

    def mouseLookOn(self):
        self.mainViewport.mouseLookOn()

    def turn_off_focus(self):
        self.focus_switch = None

    @property
    def blockFaceUnderCursor(self):
        return self.currentViewport.blockFaceUnderCursor

    #    @property
    #    def worldTooltipText(self):
    #        try:
    #            if self.blockFaceUnderCursor:
    #                pos = self.blockFaceUnderCursor[0]
    #                blockID = self.level.blockAt(*pos)
    #                blockData = self.level.blockDataAt(*pos)
    #
    #                return "{name} ({bid})\n{pos}".format(name=self.level.materials.names[blockID][blockData], bid=blockID,pos=pos)
    #
    #        except Exception, e:
    #            return None
    #

    def generateStars(self):
        starDistance = 999.0
        starCount = 2000

        r = starDistance

        randPoints = (numpy.random.random(size=starCount * 3)) * 2.0 * r
        randPoints.shape = (starCount, 3)

        nearbyPoints = (randPoints[:, 0] < r) & (randPoints[:, 1] < r) & (randPoints[:, 2] < r)
        randPoints[nearbyPoints] += r

        randPoints[:starCount / 2, 0] = -randPoints[:starCount / 2, 0]
        randPoints[::2, 1] = -randPoints[::2, 1]
        randPoints[::4, 2] = -randPoints[::4, 2]
        randPoints[1::4, 2] = -randPoints[1::4, 2]

        randsizes = numpy.random.random(size=starCount) * 6 + 0.8

        vertsPerStar = 4

        vertexBuffer = numpy.zeros((starCount, vertsPerStar, 3), dtype='float32')

        def normvector(x):
            return x / numpy.sqrt(numpy.sum(x * x, 1))[:, numpy.newaxis]

        viewVector = normvector(randPoints)

        rmod = numpy.random.random(size=starCount * 3) * 2.0 - 1.0
        rmod.shape = (starCount, 3)
        referenceVector = viewVector + rmod

        rightVector = normvector(numpy.cross(referenceVector, viewVector)) * randsizes[:,
                                                                             numpy.newaxis]  # vector perpendicular to viewing line
        upVector = normvector(numpy.cross(rightVector, viewVector)) * randsizes[:,
                                                                      numpy.newaxis]  # vector perpendicular previous vector and viewing line

        p = randPoints
        p1 = p + (- upVector - rightVector)
        p2 = p + (upVector - rightVector)
        p3 = p + (upVector + rightVector)
        p4 = p + (- upVector + rightVector)

        vertexBuffer[:, 0, :] = p1
        vertexBuffer[:, 1, :] = p2
        vertexBuffer[:, 2, :] = p3
        vertexBuffer[:, 3, :] = p4

        self.starVertices = vertexBuffer.ravel()

    starColor = None

    def drawStars(self):
        pos = self.mainViewport.cameraPosition
        self.mainViewport.cameraPosition = map(lambda x: x / 128.0, pos)
        self.mainViewport.setModelview()

        GL.glColor(.5, .5, .5, 1.)

        GL.glVertexPointer(3, GL.GL_FLOAT, 0, self.starVertices)
        GL.glDrawArrays(GL.GL_QUADS, 0, len(self.starVertices) / 3)

        self.mainViewport.cameraPosition = pos
        self.mainViewport.setModelview()

    fractionalReachAdjustment = True

    def postMouseMoved(self):
        evt = event.Event(MOUSEMOTION, rel=(0, 0), pos=mouse.get_pos(), buttons=mouse.get_pressed())
        event.post(evt)

    def resetReach(self):
        self.postMouseMoved()
        if self.currentTool.resetToolReach():
            return
        self.cameraToolDistance = self.defaultCameraToolDistance

    def increaseReach(self):
        self.postMouseMoved()
        if self.currentTool.increaseToolReach():
            return
        self.cameraToolDistance = self._incrementReach(self.cameraToolDistance)

    def decreaseReach(self):
        self.postMouseMoved()
        if self.currentTool.decreaseToolReach():
            return
        self.cameraToolDistance = self._decrementReach(self.cameraToolDistance)

    def _incrementReach(self, reach):
        reach += 1
        if reach > 30 and self.fractionalReachAdjustment:
            reach *= 1.05
        return reach

    def _decrementReach(self, reach):
        reach -= 1
        if reach > 30 and self.fractionalReachAdjustment:
            reach *= 0.95
        return reach

    def take_screenshot(self):
        try:
            os.mkdir(os.path.join(directories.parentDir, "screenshots"))
        except OSError:
            pass
        screenshot_name = os.path.join(directories.parentDir, "screenshots", time.strftime("%Y-%m-%d (%I-%M-%S-%p)")+".png")
        pygame.image.save(pygame.display.get_surface(), screenshot_name)
        self.diag = Dialog()
        lbl = Label("Screenshot taken and saved as '"+screenshot_name+"'")
        folderBtn = Button("Open Folder", action=self.open_screenshots_folder)
        btn = Button("Ok", action=self.screenshot_notify)
        buttonsRow = Row((btn,folderBtn))
        col = Column((lbl,buttonsRow))
        self.diag.add(col)
        self.diag.shrink_wrap()
        self.diag.present()

    def open_screenshots_folder(self):
        platform_open(os.path.join(directories.parentDir, "screenshots"))

    def screenshot_notify(self):
        self.diag.dismiss()

    def key_up(self, evt):
        self.currentTool.keyUp(evt)
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        try:
        	keyname = self.different_keys[keyname]
        except:
        	pass

        if keyname == config.keys.brake.get():
            self.mainViewport.brakeOff()

        if keyname == config.keys.fastNudge.get():
            self.rightClickNudge = False

        if keyname == 'F7':
            self.testBoardKey = 0

    def key_down(self, evt):
        if not pygame.key.get_focused():
            return

        self.currentTool.keyDown(evt)
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        try:
        	keyname = self.different_keys[keyname]
        except:
        	pass

        if keyname == "Alt-F4":
            self.quit()
            return

        if keyname == config.keys.longDistanceMode.get():
            self.longDistanceMode = not self.longDistanceMode
        if keyname == "Alt-1" or keyname == "Alt-2" or keyname == "Alt-3" or keyname == "Alt-4" or keyname == "Alt-5":
            name = "option" + keyname[len(keyname) - 1:]
            if hasattr(self.currentTool, name):
                getattr(self.currentTool, name)()

        if keyname == config.keys.fastNudge.get():
            self.rightClickNudge = True

        if "clone" in str(self.currentTool):
            blocksOnlyModifier = config.keys.blocksOnlyModifier.get()
            if keyname.startswith(blocksOnlyModifier):
                tempKeyname = keyname[len(blocksOnlyModifier)+1:]
                blocksOnly = True
            else:
                tempKeyname = keyname
                blocksOnly = False

            if tempKeyname == config.keys.flip.get():
                self.currentTool.flip(blocksOnly=blocksOnly)
            if tempKeyname == config.keys.rollClone.get():
                self.currentTool.roll(blocksOnly=blocksOnly)
            if tempKeyname == config.keys.rotateClone.get():
                self.currentTool.rotate(blocksOnly=blocksOnly)
            if tempKeyname == config.keys.mirror.get():
                self.currentTool.mirror(blocksOnly=blocksOnly)

        if "Brush" in str(self.currentTool):
            if keyname == config.keys.decreaseBrush.get():
                self.currentTool.decreaseBrushSize()
            if keyname == config.keys.increaseBrush.get():
                self.currentTool.increaseBrushSize()

            blocksOnlyModifier = config.keys.blocksOnlyModifier.get()
            if keyname.startswith(blocksOnlyModifier):
                tempKeyname = keyname[len(blocksOnlyModifier)+1:]
                blocksOnly = True
            else:
                tempKeyname = keyname
                blocksOnly = False

            if tempKeyname == config.keys.rotateBrush.get():
                self.currentTool.rotate(blocksOnly=blocksOnly)
            if tempKeyname == config.keys.rollBrush.get():
                self.currentTool.roll(blocksOnly=blocksOnly)

        if "fill" in str(self.currentTool) and keyname == config.keys.replaceShortcut.get():
            self.currentTool.toggleReplacing()

        if keyname == config.keys.quit.get():
            self.quit()
            return
        if keyname == config.keys.viewDistance.get():
            self.swapViewDistance()
        if keyname == config.keys.selectAll.get():
            self.selectAll()
        if keyname == config.keys.deselect.get():
            self.deselect()
        if keyname == config.keys.cut.get():
            self.cutSelection()
        if keyname == config.keys.copy.get():
            self.copySelection()
        if keyname == config.keys.paste.get():
            self.pasteSelection()
        if keyname == config.keys.takeAScreenshot.get():
            self.take_screenshot()

        if keyname == config.keys.reloadWorld.get():
            self.reload()

        if keyname == config.keys.open.get():
            self.askOpenFile()
        if keyname == config.keys.quickLoad.get():
            self.askLoadWorld()
        if keyname == config.keys.undo.get():
            self.undo()
        if keyname == config.keys.redo.get():
            self.redo()
        if keyname == config.keys.save.get():
            self.saveFile()
        if keyname == config.keys.newWorld.get():
            self.createNewLevel()
        if keyname == config.keys.closeWorld.get():
            self.closeEditor()
        if keyname == config.keys.worldInfo.get():
            self.showWorldInfo()
        if keyname == config.keys.gotoPanel.get():
            self.showGotoPanel()

        if keyname == config.keys.exportSelection.get():
            self.selectionTool.exportSelection()

        if keyname == 'Ctrl-Alt-F9':
            try:
                expr = input_text(">>> ", 600)
                expr = compile(expr, 'eval', 'single')
                alert("Result: {0!r}".format(eval(expr, globals(), locals())))
            except Exception, e:
                alert("Exception: {0!r}".format(e))

        if keyname == 'Ctrl-Alt-F10':
            alert("MCEdit, a Minecraft World Editor\n\nCopyright 2010 David Rio Vierra")

        if keyname == config.keys.toggleView.get():
            self.swapViewports()

        if keyname == config.keys.brake.get():
            self.mainViewport.brakeOn()

        if keyname == config.keys.resetReach.get():
            self.resetReach()
        if keyname == config.keys.increaseReach.get():
            self.increaseReach()
        if keyname == config.keys.decreaseReach.get():
            self.decreaseReach()
        if keyname == config.keys.swap.get():
            self.currentTool.swap()

        if keyname == 'Escape':
            if "select" not in str(self.currentTool):
                self.toolbar.selectTool(0)
            else:
                self.mouseLookOff()
                self.showControls()

        if keyname == config.keys.confirmConstruction.get():
            self.confirmConstruction()

        if keyname == config.keys.debugOverlay.get():
            self.swapDebugLevels()

        if keyname == config.keys.toggleRenderer.get():
            self.renderer.render = not self.renderer.render

        if keyname == config.keys.deleteBlocks.get():
            self.deleteSelectedBlocks()

        if keyname == config.keys.flyMode.get():
            config.settings.flyMode.set(not config.settings.flyMode.get())
            config.save()

        if keyname == '1' or keyname == '2' or keyname == '3' or keyname == '4' or keyname == '5' or keyname == '6' or keyname == '7' or keyname == '8' or keyname == '9':
            self.toolbar.selectTool(int(keyname) - 1)

        if keyname in ('F1', 'F2', 'F3', 'F4', 'F5'):
            self.mcedit.loadRecentWorldNumber(int(keyname[1]))

        if keyname == 'F7':
            self.testBoardKey = 1

        self.root.fix_sticky_ctrl()

    def showGotoPanel(self):

        gotoPanel = Widget()
        gotoPanel.X, gotoPanel.Y, gotoPanel.Z = map(int, self.mainViewport.cameraPosition)

        inputRow = (
            Label("X: "), IntField(ref=AttrRef(gotoPanel, "X")),
            Label("Y: "), IntField(ref=AttrRef(gotoPanel, "Y")),
            Label("Z: "), IntField(ref=AttrRef(gotoPanel, "Z")),
        )
        inputRow = Row(inputRow)
        column = (
            Label("Goto Position:"),
            Label("(click anywhere to teleport)"),
            inputRow,
            # Row( (Button("Cancel"), Button("Goto")), align="r" )
        )
        column = Column(column)
        gotoPanel.add(column)
        gotoPanel.shrink_wrap()
        d = Dialog(client=gotoPanel, responses=["Goto", "Cancel"])

        def click_outside(event):
            if event not in d:
                x, y, z = self.blockFaceUnderCursor[0]
                if y == 0:
                    y = 64
                y += 3
                gotoPanel.X, gotoPanel.Y, gotoPanel.Z = x, y, z
                if event.num_clicks == 2:
                    d.dismiss("Goto")

        d.mouse_down = click_outside
        d.top = self.viewportContainer.top + 10
        d.centerx = self.viewportContainer.centerx
        if d.present(centered=False) == "Goto":
            destPoint = [gotoPanel.X, gotoPanel.Y, gotoPanel.Z]
            if self.currentViewport is self.chunkViewport:
                self.swapViewports()
            self.mainViewport.cameraPosition = destPoint

    def closeEditor(self):
        if self.unsavedEdits:
            answer = ask("Save unsaved edits before closing?", ["Cancel", "Don't Save", "Save"], default=-1, cancel=0)
            self.root.fix_sticky_ctrl()
            if answer == "Save":
                self.saveFile()
            if answer == "Cancel":
                return
        self.clearUnsavedEdits()
        self.unsavedEdits = 0
        self.root.fix_sticky_ctrl()
        self.mainViewport.mouseLookOff()
        self.level = None
        self.renderer.stopWork()
        self.removeWorker(self.renderer)
        self.renderer.level = None
        self.mcedit.removeEditor()
        self.controlPanel.dismiss()
        display.set_caption("MCEdit ~ " + release.get_version())

    def repairRegions(self):
        worldFolder = self.level.worldFolder
        for filename in worldFolder.findRegionFiles():
            rf = worldFolder.tryLoadRegionFile(filename)
            if rf:
                rf.repair()

        alert("Repairs complete.  See the console window for details.")

    @mceutils.alertException
    def showWorldInfo(self):
        ticksPerDay = 24000
        ticksPerHour = ticksPerDay / 24
        ticksPerMinute = ticksPerDay / (24 * 60)

        def decomposeMCTime(time):
            day = time / ticksPerDay
            tick = time % ticksPerDay
            hour = tick / ticksPerHour
            tick %= ticksPerHour
            minute = tick / ticksPerMinute
            tick %= ticksPerMinute

            return day, hour, minute, tick

        def composeMCTime(d, h, m, t):
            time = d * ticksPerDay + h * ticksPerHour + m * ticksPerMinute + t
            return time

        worldInfoPanel = Dialog()
        items = []

        t = functools.partial(isinstance, self.level)
        if t(pymclevel.MCInfdevOldLevel):
            if self.level.version == pymclevel.MCInfdevOldLevel.VERSION_ANVIL:
                levelFormat = "Minecraft Infinite World (Anvil Format)"
            elif self.level.version == pymclevel.MCInfdevOldLevel.VERSION_MCR:
                levelFormat = "Minecraft Infinite World (Region Format)"
            else:
                levelFormat = "Minecraft Infinite World (Old Chunk Format)"
        elif t(pymclevel.MCIndevLevel):
            levelFormat = "Minecraft Indev (.mclevel format)"
        elif t(pymclevel.MCSchematic):
            levelFormat = "MCEdit Schematic"
        elif t(pymclevel.ZipSchematic):
            levelFormat = "MCEdit Schematic (Zipped Format)"
        elif t(pymclevel.MCJavaLevel):
            levelFormat = "Minecraft Classic or raw block array"
        else:
            levelFormat = "Unknown"
        formatLabel = Label(levelFormat)
        items.append(Row([Label("Format:"),formatLabel]))

        nameField = TextField(width=300, value=self.level.LevelName)
        def alt21():
            nameField.insertion_point = len(nameField.text)
            nameField.insert_char(u'\xa7')
        alt21button = Button(u"\xa7", action=alt21)
        label = Label("Name:")
        items.append(Row((label, nameField, alt21button)))

        if hasattr(self.level, 'Time'):
            time = self.level.Time
            # timezone adjust -
            # minecraft time shows 0:00 on day 0 at the first sunrise
            # I want that to be 6:00 on day 1, so I add 30 hours
            timezoneAdjust = ticksPerHour * 30
            time += timezoneAdjust

            d, h, m, tick = decomposeMCTime(time)

            dayInput = IntField(value=d, min=1)
            items.append(Row((Label("Day: "), dayInput)))

            timeInput = TimeField(value=(h, m))
            timeInputRow = Row((Label("Time of day:"), timeInput))
            items.append(timeInputRow)

        if hasattr(self.level, 'RandomSeed'):
            seedField = IntField(width=250, value=self.level.RandomSeed)
            seedLabel = Label("RandomSeed: ")
            items.append(Row((seedLabel, seedField)))

        if hasattr(self.level, 'GameType'):
            t = self.level.GameType
            types = ["Survival", "Creative"]

            def gametype(t):
                if t < len(types):
                    return types[t]
                return "Unknown"

            def action():
                if b.gametype < 2:
                    b.gametype = 1 - b.gametype
                    b.text = gametype(b.gametype)

            b = Button(gametype(t), action=action)
            b.gametype = t


            gametypeRow = Row((Label("Game Type: "), b))
            items.append(gametypeRow)
        if isinstance(self.level, pymclevel.MCInfdevOldLevel):

            chunkCount = self.level.chunkCount
            chunkCountLabel = Label(_("Number of chunks: {0}").format(chunkCount))

            items.append(chunkCountLabel)

        if hasattr(self.level, 'worldFolder'):
            if hasattr(self.level.worldFolder, 'regionFiles'):
                worldFolder = self.level.worldFolder
                regionCount = len(worldFolder.regionFiles)
                regionCountLabel = Label(_("Number of regions: {0}").format(regionCount))
                items.append(regionCountLabel)

            button = Button("Repair regions", action=self.repairRegions)
            items.append(button)

        def openFolder():
            filename = self.level.filename
            if not isdir(filename):
                filename = dirname(filename)
            mcplatform.platform_open(filename)

        revealButton = Button("Open Folder", action=openFolder)
        items.append(revealButton)

        # if all(hasattr(self.level, i) for i in ("Length", "Width", "Height")):
        size = self.level.size
        sizelabel = Label("{L}L x {W}W x {H}H".format(L=size[2], H=size[1], W=size[0]))
        items.append(sizelabel)

        if hasattr(self.level, "Entities"):
            label = Label(_("{0} Entities").format(len(self.level.Entities)))
            items.append(label)
        if hasattr(self.level, "TileEntities"):
            label = Label(_("{0} TileEntities").format(len(self.level.TileEntities)))
            items.append(label)

        col = Column(items)

        self.change = False

        def dismiss(*args, **kwargs):
            self.change = True
            worldInfoPanel.dismiss(self, *args, **kwargs)

        def cancel(*args, **kwargs):
            Changes = False
            if hasattr(self.level, 'Time'):
                h, m = timeInput.value
                time = composeMCTime(dayInput.value, h, m, tick)
                time -= timezoneAdjust
                if self.level.Time != time:
                    Changes = True
            if hasattr(self.level, 'RandomSeed'):
                if seedField.value != self.level.RandomSeed:
                    Changes = True
            if hasattr(self.level, 'LevelName'):
                if nameField.value != self.level.LevelName:
                    Changes = True
            if hasattr(self.level, 'GameType'):
                if b.gametype != self.level.GameType:
                    Changes = True

            if not Changes:
                worldInfoPanel.dismiss(self, *args, **kwargs)
                return

            result = ask("Do you want to keep your changes?", ["Yes", "No", "Cancel"])
            if result == "Cancel":
                return
            if result == "No":
                worldInfoPanel.dismiss(self, *args, **kwargs)
                return
            if result == "Yes":
                dismiss(*args, **kwargs)

        col = Column((col, Row((Button("OK", action=dismiss), Button("Cancel", action=cancel)))))

        worldInfoPanel.add(col)
        worldInfoPanel.shrink_wrap()

        def dispatchKey(name, evt):
            if name == "key_down":
                keyname = self.get_root().getKey(evt)
                if keyname == 'Escape':
                    cancel()

        worldInfoPanel.dispatch_key = dispatchKey

        worldInfoPanel.present()
        if not self.change:
            return

        if hasattr(self.level, 'Time'):
            h, m = timeInput.value
            time = composeMCTime(dayInput.value, h, m, tick)
            time -= timezoneAdjust
            if self.level.Time != time:
                self.level.Time = time
                # xxx TimeChangeOperation
                self.addUnsavedEdit()

        if hasattr(self.level, 'RandomSeed'):
            if seedField.value != self.level.RandomSeed:
                self.level.RandomSeed = seedField.value
                self.addUnsavedEdit()

        if hasattr(self.level, 'LevelName'):
            if nameField.value != self.level.LevelName:
                self.level.LevelName = nameField.value
                self.addUnsavedEdit()

        if hasattr(self.level, 'GameType'):
            if b.gametype != self.level.GameType:
                self.level.GameType = b.gametype
                self.addUnsavedEdit()

    def swapViewDistance(self):
        if self.renderer.viewDistance >= self.renderer.maxViewDistance:
            self.renderer.viewDistance = self.renderer.minViewDistance
        else:
            self.renderer.viewDistance += 2

        self.addWorker(self.renderer)
        config.settings.viewDistance.set(self.renderer.viewDistance)

    def increaseViewDistance(self):
        self.renderer.viewDistance = min(self.renderer.maxViewDistance, self.renderer.viewDistance + 2)
        self.addWorker(self.renderer)
        config.settings.viewDistance.set(self.renderer.viewDistance)

    def decreaseViewDistance(self):
        self.renderer.viewDistance = max(self.renderer.minViewDistance, self.renderer.viewDistance - 2)
        self.addWorker(self.renderer)
        config.settings.viewDistance.set(self.renderer.viewDistance)

    @mceutils.alertException
    def askLoadWorld(self):
        if not os.path.isdir(directories.minecraftSaveFileDir):
            alert(_(u"Could not find the Minecraft saves directory!\n\n({0} was not found or is not a directory)").format(
                directories.minecraftSaveFileDir))
            return

        worldPanel = Widget()

        potentialWorlds = os.listdir(directories.minecraftSaveFileDir)
        potentialWorlds = [os.path.join(directories.minecraftSaveFileDir, p) for p in potentialWorlds]
        worldFiles = [p for p in potentialWorlds if pymclevel.MCInfdevOldLevel.isLevel(p)]
        worlds = []
        for f in worldFiles:
            try:
                lev = pymclevel.MCInfdevOldLevel(f, readonly=True)
            except Exception:
                continue
            else:
                worlds.append(lev)
        if len(worlds) == 0:
            alert("No worlds found! You should probably play Minecraft to create your first world.")
            return

        def loadWorld():
            self.mcedit.loadFile(worldData[worldTable.selectedWorldIndex][3].filename)
            self.root.fix_sticky_ctrl()

        def click_row(i, evt):
            worldTable.selectedWorldIndex = i
            if evt.num_clicks == 2:
                loadWorld()
                d.dismiss("Cancel")

        def key_down(evt):
            keyname = self.root.getKey(evt)
            if keyname == "Escape":
                d.dismiss("Cancel")
            elif keyname == "Up" and worldTable.selectedWorldIndex > 0:
                worldTable.selectedWorldIndex -= 1
                worldTable.rows.scroll_to_item(worldTable.selectedWorldIndex)
            elif keyname == "Down" and worldTable.selectedWorldIndex < len(worlds)-1:
                worldTable.selectedWorldIndex += 1
                worldTable.rows.scroll_to_item(worldTable.selectedWorldIndex)
            elif keyname == "Return":
                loadWorld()
                d.dismiss("Cancel")

        def key_up(evt):
            pass

        worldTable = TableView(columns=[
            TableColumn("Last Played", 170, "l"),
            TableColumn("Level Name (filename)", 500, "l"),
            TableColumn("Dims", 100, "r"),

        ])

        def dateobj(lp):
            try:
                return datetime.utcfromtimestamp(lp / 1000.0)
            except:
                return datetime.utcfromtimestamp(0.0)

        def dateFormat(lp):
            try:
                return lp.strftime("%x %X").decode('utf-8')
            except:
                return u"{0} seconds since the epoch.".format(lp)

        def nameFormat(w):
            try:
                if w.LevelName == w.displayName.decode("utf-8"):
                    return w.LevelName
                return u"{0} ({1})".format(w.LevelName, w.displayName.decode("utf-8"))
            except:
                try:
                    return w.LevelName
                except:
                    try:
                        return w.displayName
                    except:
                        return "[UNABLE TO READ]"

        worldData = [[dateFormat(d), nameFormat(w), str(w.dimensions.keys())[1:-1], w, d]
                     for w, d in ((w, dateobj(w.LastPlayed)) for w in worlds)]
        worldData.sort(key=lambda (a, b, dim, w, d): d, reverse=True)
        # worlds = [w[2] for w in worldData]

        worldTable.selectedWorldIndex = 0
        worldTable.num_rows = lambda: len(worldData)
        worldTable.row_data = lambda i: worldData[i]
        worldTable.row_is_selected = lambda x: x == worldTable.selectedWorldIndex
        worldTable.click_row = click_row

        worldPanel.add(worldTable)
        worldPanel.shrink_wrap()

        d = Dialog(worldPanel, ["Load", "Cancel"])
        d.key_down = key_down
        d.key_up = key_up
        if d.present() == "Load":
            loadWorld()

    def askOpenFile(self):
        self.mouseLookOff()
        try:
            filename = mcplatform.askOpenFile()
            if filename:
                self.parent.loadFile(filename)
        except Exception:
            logging.exception('Error while asking user for filename')
            return

    def createNewLevel(self):
        self.mouseLookOff()

        newWorldPanel = Widget()
        newWorldPanel.w = newWorldPanel.h = 16
        newWorldPanel.x = newWorldPanel.z = newWorldPanel.f = 0
        newWorldPanel.y = 64
        newWorldPanel.seed = 0

        label = Label("Creating a new world.")
        generatorPanel = GeneratorPanel()

        xinput = mceutils.IntInputRow("X: ", ref=AttrRef(newWorldPanel, "x"))
        yinput = mceutils.IntInputRow("Y: ", ref=AttrRef(newWorldPanel, "y"))
        zinput = mceutils.IntInputRow("Z: ", ref=AttrRef(newWorldPanel, "z"))
        finput = mceutils.IntInputRow("f: ", ref=AttrRef(newWorldPanel, "f"), min=0, max=3)
        xyzrow = Row([xinput, yinput, zinput, finput])
        seedinput = mceutils.IntInputRow("Seed: ", width=250, ref=AttrRef(newWorldPanel, "seed"))

        winput = mceutils.IntInputRow("East-West Chunks: ", ref=AttrRef(newWorldPanel, "w"), min=0)
        hinput = mceutils.IntInputRow("North-South Chunks: ", ref=AttrRef(newWorldPanel, "h"), min=0)
        # grassinputrow = Row( (Label("Grass: ")
        # from editortools import BlockButton
        # blockInput = BlockButton(pymclevel.alphaMaterials, pymclevel.alphaMaterials.Grass)
        # blockInputRow = Row( (Label("Surface: "), blockInput) )

        types = ["Survival", "Creative"]

        def gametype(t):
            if t < len(types):
                return types[t]
            return "Unknown"

        def action():
            if gametypeButton.gametype < 2:
                gametypeButton.gametype = 1 - gametypeButton.gametype
                gametypeButton.text = gametype(gametypeButton.gametype)

        gametypeButton = Button(gametype(0), action=action)
        gametypeButton.gametype = 0
        gametypeRow = Row((Label("Game Type:"), gametypeButton))
        newWorldPanel.add(
            Column((label, Row([winput, hinput]), xyzrow, seedinput, gametypeRow, generatorPanel), align="l"))
        newWorldPanel.shrink_wrap()

        result = Dialog(client=newWorldPanel, responses=["Create", "Cancel"]).present()
        if result == "Cancel":
            return
        filename = mcplatform.askCreateWorld(directories.minecraftSaveFileDir)

        if not filename:
            return

        w = newWorldPanel.w
        h = newWorldPanel.h
        x = newWorldPanel.x
        y = newWorldPanel.y
        z = newWorldPanel.z
        f = newWorldPanel.f
        seed = newWorldPanel.seed or None

        self.freezeStatus("Creating world...")
        try:
            newlevel = pymclevel.MCInfdevOldLevel(filename=filename, create=True, random_seed=seed)
            # chunks = list(itertools.product(xrange(w / 2 - w + cx, w / 2 + cx), xrange(h / 2 - h + cz, h / 2 + cz)))

            if generatorPanel.generatorChoice.selectedChoice == "Flatland":
                y = generatorPanel.chunkHeight

            newlevel.setPlayerPosition((x + 0.5, y + 2.8, z + 0.5))
            newlevel.setPlayerOrientation((f * 90.0, 0.0))

            newlevel.setPlayerSpawnPosition((x, y + 1, z))
            newlevel.GameType = gametypeButton.gametype
            newlevel.saveInPlace()
            worker = generatorPanel.generate(newlevel, pymclevel.BoundingBox((x - w * 8, 0, z - h * 8),
                                                                             (w * 16, newlevel.Height, h * 16)))

            if "Canceled" == mceutils.showProgress("Generating chunks...", worker, cancel=True):
                raise RuntimeError("Canceled.")

            if y < 64:
                y = 64
                newlevel.setBlockAt(x, y, z, pymclevel.alphaMaterials.Sponge.ID)
            if newlevel.parentWorld:
                newlevel = newlevel.parentWorld
            newlevel.acquireSessionLock()
            newlevel.saveInPlace()

            self.loadFile(filename)
        except Exception:
            logging.exception(
                'Error while creating world. {world => %s}' % filename
            )
            return

        return newlevel

    def confirmConstruction(self):
        self.currentTool.confirm()

    def selectionToChunks(self, remove=False, add=False):
        box = self.selectionBox()
        if box:
            if box == self.level.bounds:
                self.selectedChunks = set(self.level.allChunks)
                return

            selectedChunks = self.selectedChunks
            boxedChunks = set(box.chunkPositions)
            if boxedChunks.issubset(selectedChunks):
                remove = True

            if remove and not add:
                selectedChunks.difference_update(boxedChunks)
            else:
                selectedChunks.update(boxedChunks)

        self.selectionTool.selectNone()

    def selectAll(self):

        if self.currentViewport is self.chunkViewport:
            self.selectedChunks = set(self.level.allChunks)
        else:
            self.selectionTool.selectAll()

    def deselect(self):
        self.selectionTool.deselect()
        self.selectedChunks.clear()

    def endSelection(self):
        self.selectionTool.endSelection()

    def cutSelection(self):
        self.selectionTool.cutSelection()

    def copySelection(self):
        self.selectionTool.copySelection()

    def pasteSelection(self):
        schematic = self.getLastCopiedSchematic()
        self.pasteSchematic(schematic)

    def pasteSchematic(self, schematic):
        if schematic is None:
            return
        self.currentTool.cancel()
        self.currentTool = self.toolbar.tools[5]
        self.currentTool.loadLevel(schematic)

    def deleteSelectedBlocks(self):
        self.selectionTool.deleteBlocks()

    @mceutils.alertException
    def undo(self):
        if len(self.undoStack) == 0 and len(self.afterSaveUndoStack) == 0:
            return
        with mceutils.setWindowCaption("UNDOING - "):
            self.freezeStatus("Undoing the previous operation...")
            wasSelectionBox = False
            if self.selectionBox():
            	wasSelectionBox = True
            if len(self.undoStack) > 0:
                op = self.undoStack.pop()
                normalUndo = True
            else:
            	op = self.afterSaveUndoStack.pop()
            	normalUndo = False

            if self.recordUndo:
                self.redoStack.append(op)
                if len(self.redoStack) > self.undoLimit:
                    self.redoStack.pop(0)
            op.undo()
            changedBox = op.dirtyBox()
            if changedBox is not None:
                self.invalidateBox(changedBox)
            if not self.selectionBox() and wasSelectionBox:
            	self.toolbar.selectTool(0)
            	self.toolbar.tools[0].currentCorner = 1
            if ".SelectionOperation" not in str(op) and ".NudgeSelectionOperation" not in str(op):
                if normalUndo:
                    self.removeUnsavedEdit()
                else:
                	self.addUnsavedEdit()

        self.root.fix_sticky_ctrl()

    def redo(self):
        if len(self.redoStack) == 0:
            return
        with mceutils.setWindowCaption("REDOING - "):
            self.freezeStatus("Redoing the previous operation...")
            op = self.redoStack.pop()

            if self.recordUndo:
                self.undoStack.append(op)
                if len(self.undoStack) > self.undoLimit:
                    self.undoStack.pop(0)
            op.redo()
            changedBox = op.dirtyBox()
            if changedBox is not None:
                self.invalidateBox(changedBox)
            if op.changedLevel:
                self.addUnsavedEdit()

        self.root.fix_sticky_ctrl()

    def invalidateBox(self, box):
        self.renderer.invalidateChunksInBox(box)

    def invalidateChunks(self, c):
        self.renderer.invalidateChunks(c)

    def invalidateAllChunks(self):
        self.renderer.invalidateAllChunks()

    def discardAllChunks(self):
        self.renderer.discardAllChunks()

    def addDebugString(self, string):
        if self.debug:
            self.debugString += string

    averageFPS = 0.0
    averageCPS = 0.0
    shouldLoadAndRender = True
    showWorkInfo = False

    def gl_draw(self):
        self.debugString = ""
        self.inspectionString = ""

        if not self.level:
            return

        if not self.shouldLoadAndRender:
            return

        self.renderer.loadVisibleChunks()
        self.addWorker(self.renderer)

        if self.currentTool.previewRenderer:
            self.currentTool.previewRenderer.loadVisibleChunks()
            self.addWorker(self.currentTool.previewRenderer)

        self.frames += 1
        frameDuration = self.getFrameDuration()
        while frameDuration > (
            datetime.now() - self.frameStartTime):  # if it's less than 0ms until the next frame, go draw.  otherwise, go work.
            self.doWorkUnit()
        if self.showWorkInfo:
            self.updateWorkInfoPanel()

        frameStartTime = datetime.now()
        timeDelta = frameStartTime - self.frameStartTime

        # self.addDebugString("FrameStart: {0}  CameraTick: {1}".format(frameStartTime, self.mainViewport.lastTick))
        # self.addDebugString("D: %d, " % () )

        self.currentFrameDelta = timeDelta
        self.frameSamples.pop(0)
        self.frameSamples.append(timeDelta)

        frameTotal = numpy.sum(self.frameSamples)

        self.averageFPS = 1000000. / (
        (frameTotal.microseconds + 1000000 * frameTotal.seconds) / float(len(self.frameSamples)) + 0.00001)

        r = self.renderer

        chunkTotal = numpy.sum(r.chunkSamples)
        cps = 1000000. / (
        (chunkTotal.microseconds + 1000000 * chunkTotal.seconds) / float(len(r.chunkSamples)) + 0.00001)
        self.averageCPS = cps

        self.oldFrameStartTime = self.frameStartTime
        self.frameStartTime = frameStartTime

        if self.debug > 0:
            self.debugString = _("FPS: %0.1f/%0.1f, CPS: %0.1f, VD: %d, W: %d, WF: %d, ") % (
            1000000. / (float(timeDelta.microseconds) + 0.000001),
            self.averageFPS,
            cps,
            self.renderer.viewDistance,
            len(self.workers),
            self.renderer.workFactor)

            self.debugString += _("DL: {dl} ({dlcount}), Tx: {t}, gc: {g}, ").format(
                dl=len(glutils.DisplayList.allLists), dlcount=glutils.gl.listCount,
                t=len(glutils.Texture.allTextures), g=len(gc.garbage))

            if self.renderer:
                self.renderer.addDebugInfo(self.addDebugString)

    def createWorkInfoPanel(self):
        infos = []
        for w in sorted(self.workers):
            if isinstance(w, MCRenderer):
                label = Label(_("Rendering chunks") + ((datetime.now().second / 3) % 3) * ".")
                progress = Label(
                    _("{0} chunks ({1} pending updates)").format(len(w.chunkRenderers), len(w.invalidChunkQueue)))
                col = Column((label, progress), align="l", width=200)
                infos.append(col)
            elif isinstance(w,
                            RunningOperation):  # **FIXME** Where is RunningOperation supposed to come from?  -David Sowder 20120311
                label = Label(w.description)
                progress = Label(w.progress)
                col = Column((label, progress), align="l", width=200)
                infos.append(col)

        panel = Panel()
        if len(infos):
            panel.add(Column(infos))
            panel.shrink_wrap()
            return panel

    workInfoPanel = None

    def updateWorkInfoPanel(self):
        if self.workInfoPanel:
            self.workInfoPanel.set_parent(None)
        self.workInfoPanel = self.createWorkInfoPanel()
        if self.workInfoPanel:
            self.workInfoPanel.topright = self.topright
            self.add(self.workInfoPanel)

    def doWorkUnit(self, onMenu=False):
        if len(self.workers):
            try:
                w = self.workers.popleft()
                w.next()
                self.workers.append(w)
            except StopIteration:
                if hasattr(w, "needsRedraw") and w.needsRedraw:
                    self.invalidate()

        elif not onMenu:
            time.sleep(0.001)

    def updateInspectionString(self, blockPosition):
        self.inspectionString += str(blockPosition) + ": "
        x, y, z = blockPosition
        cx, cz = x // 16, z // 16

        try:
            if self.debug:

                if isinstance(self.level, pymclevel.MCIndevLevel):
                    bl = self.level.blockLightAt(*blockPosition)
                    blockID = self.level.blockAt(*blockPosition)
                    bdata = self.level.blockDataAt(*blockPosition)
                    self.inspectionString += _("ID: %d:%d (%s), ") % (
                        blockID, bdata, self.level.materials.names[blockID][bdata])
                    self.inspectionString += _("Data: %d, Light: %d, ") % (bdata, bl)

                elif isinstance(self.level, pymclevel.ChunkedLevelMixin):
                    sl = self.level.skylightAt(*blockPosition)
                    bl = self.level.blockLightAt(*blockPosition)
                    bdata = self.level.blockDataAt(*blockPosition)
                    blockID = self.level.blockAt(*blockPosition)
                    self.inspectionString += _("ID: %d:%d (%s), ") % (
                        blockID, bdata, self.level.materials.names[blockID][bdata])

                    try:
                        path = self.level.getChunk(cx, cz).filename
                    except:
                        path = "chunks.dat"

                    self.inspectionString += _("Data: %d, L: %d, SL: %d") % (
                        bdata, bl, sl)

                    try:
                        hm = self.level.heightMapAt(x, z)
                        self.inspectionString += _(", H: %d") % hm
                    except:
                        pass
                    try:
                        tp = self.level.getChunk(cx, cz).TerrainPopulated
                        self.inspectionString += _(", TP: %d") % tp
                    except:
                        pass

                    self.inspectionString += _(", D: %d") % self.level.getChunk(cx, cz).dirty
                    self.inspectionString += _(", NL: %d") % self.level.getChunk(cx, cz).needsLighting
                    try:
                        biome = self.level.getChunk(cx, cz).Biomes[x & 15, z & 15]
                        from pymclevel import biome_types

                        self.inspectionString += _(", Bio: %s") % biome_types.biome_types[biome]
                    except AttributeError:
                        pass

                    if isinstance(self.level, pymclevel.pocket.PocketWorld):
                        ch = self.level.getChunk(cx, cz)
                        self.inspectionString += _(", DC: %s") % ch.DirtyColumns[z & 15, x & 15]

                    self.inspectionString += _(", Ch(%d, %d): %s") % (cx, cz, path)

                else:  # classic
                    blockID = self.level.blockAt(*blockPosition)
                    self.inspectionString += _("ID: %d (%s), ") % (
                        blockID, self.level.materials.names[blockID][0])

        except Exception, e:
            self.inspectionString += _("Chunk {0} had an error: {1!r}").format(
                (int(numpy.floor(blockPosition[0])) >> 4, int(numpy.floor(blockPosition[2])) >> 4), e)
            pass

    def drawWireCubeReticle(self, color=(1.0, 1.0, 1.0, 1.0), position=None):
        GL.glPolygonOffset(DepthOffset.TerrainWire, DepthOffset.TerrainWire)
        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)

        blockPosition, faceDirection = self.blockFaceUnderCursor
        blockPosition = position or blockPosition

        mceutils.drawTerrainCuttingWire(pymclevel.BoundingBox(blockPosition, (1, 1, 1)), c1=color)

        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

    def drawString(self, x, y, color, string):
        return

    def freezeStatus(self, string):
        return

    #        GL.glColor(1.0, 0., 0., 1.0)
    #
    #        # glDrawBuffer(GL.GL_FRONT)
    #        GL.glMatrixMode(GL.GL_PROJECTION)
    #        GL.glPushMatrix()
    #        glRasterPos(50, 100)
    #        for i in string:
    #            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(i))
    #
    #        # glDrawBuffer(GL.GL_BACK)
    #        GL.glMatrixMode(GL.GL_PROJECTION)
    #        GL.glPopMatrix()
    #        glFlush()
    #        display.flip()
    #        # while(True): pass

    def selectionSize(self):
        return self.selectionTool.selectionSize()

    def selectionBox(self):
        return self.selectionTool.selectionBox()

    def selectionChanged(self):
        if not self.currentTool.toolEnabled():
            self.toolbar.selectTool(0)

        self.currentTool.selectionChanged()

    def addOperation(self, op):
        self.performWithRetry(op)

        if self.recordUndo and op.canUndo:
            self.undoStack.append(op)
            if len(self.undoStack) > self.undoLimit:
                self.undoStack.pop(0)

    recordUndo = True

    def performWithRetry(self, op):
        try:
            op.perform(self.recordUndo)
        except MemoryError:
            self.invalidateAllChunks()
            op.perform(self.recordUndo)

    def quit(self):
        self.mouseLookOff()
        self.mcedit.confirm_quit()

    mouseWasCaptured = False

    def showControls(self):
        self.controlPanel.present(False)

    infoPanel = None

    def showChunkRendererInfo(self):
        if self.infoPanel:
            self.infoPanel.set_parent(None)
            return

        self.infoPanel = infoPanel = Widget(bg_color=(0, 0, 0, 80))
        infoPanel.add(Label(""))

        def idleHandler(evt):

            x, y, z = self.blockFaceUnderCursor[0]
            cx, cz = x // 16, z // 16
            cr = self.renderer.chunkRenderers.get((cx, cz))
            if None is cr:
                return

            crNames = [_("%s - %0.1fkb") % (type(br).__name__, br.bufferSize() / 1000.0) for br in cr.blockRenderers]
            infoLabel = Label("\n".join(crNames))

            infoPanel.remove(infoPanel.subwidgets[0])
            infoPanel.add(infoLabel)
            infoPanel.shrink_wrap()
            self.invalidate()

        infoPanel.idleevent = idleHandler

        infoPanel.topleft = self.viewportContainer.topleft
        self.add(infoPanel)
        infoPanel.click_outside_response = -1
        # infoPanel.present()

    ##    def testGLSL(self):
    ##        print "Hello"
    ##        level = MCLevel.fromFile("mrchunk.schematic")
    ##        blocks = level.Blocks
    ##        blockCount = level.Width * level.Length * level.Height,
    ##        fbo = glGenFramebuffersEXT(1)
    ##        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, fbo)
    ##
    ##        print blockCount, fbo
    ##
    ##        destBlocks = numpy.zeros(blockCount, 'uint8')
    ##        (sourceTex, destTex) = glGenTextures(2)
    ##
    ##        glBindTexture(GL_TEXTURE_3D, sourceTex)
    ##        glTexImage3D(GL_TEXTURE_3D, 0, 1,
    ##                     level.Width, level.Length, level.Height,
    ##                     0, GL_RED, GL.GL_UNSIGNED_BYTE,
    ##                     blocks)
    ##
    ##        # return
    ##
    ##        glBindTexture(GL.GL_TEXTURE_2D, destTex)
    ##        glTexImage2D(GL.GL_TEXTURE_2D, 0, 1,
    ##                     level.Width, level.Length,
    ##                     0, GL_RED, GL.GL_UNSIGNED_BYTE, destBlocks)
    ##        glTexParameter(GL.GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    ##        glFramebufferTexture2DEXT(GL_FRAMEBUFFER_EXT, GL_COLOR_ATTACHMENT0_EXT, GL.GL_TEXTURE_2D, destTex, 0)
    ##
    ##        vertShader = glCreateShader(GL_VERTEX_SHADER)
    ##
    ##        vertShaderSource = """
    ##        void main()
    ##        {
    ##            gl_Position = gl_Vertex
    ##        }
    ##        """
    ##
    ##        glShaderSource(vertShader, vertShaderSource);
    ##        glCompileShader(vertShader);
    ##
    ##        fragShader = glCreateShader(GL_FRAGMENT_SHADER)
    ##
    ##        fragShaderSource = """
    ##        void main()
    ##        {
    ##            gl_FragColor = vec4(1.0, 0.0, 1.0, 0.75);
    ##        }
    ##        """
    ##
    ##        glShaderSource(fragShader, fragShaderSource);
    ##        glCompileShader(fragShader);
    ##
    ##
    ##
    ##        prog = glCreateProgram()
    ##
    ##        glAttachShader(prog, vertShader)
    ##        glAttachShader(prog, fragShader)
    ##        glLinkProgram(prog)
    ##
    ##        glUseProgram(prog);
    ##        # return
    ##        GL.glDisable(GL.GL_DEPTH_TEST);
    ##        GL.glVertexPointer(2, GL.GL_FLOAT, 0, [0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0]);
    ##        GL.glDrawArrays(GL.GL_QUADS, 0, 4);
    ##        GL.glEnable(GL.GL_DEPTH_TEST);
    ##
    ##        glFlush();
    ##        destBlocks = glGetTexImage(GL.GL_TEXTURE_2D, 0, GL_RED, GL.GL_UNSIGNED_BYTE);
    ##        print destBlocks, destBlocks[0:8];
    ##        raise SystemExit;

    def handleMemoryError(self):
        if self.renderer.viewDistance <= 2:
            raise MemoryError("Out of memory. Please restart MCEdit.")
        if hasattr(self.level, 'compressAllChunks'):
            self.level.compressAllChunks()
        self.toolbar.selectTool(0)

        self.renderer.viewDistance = self.renderer.viewDistance - 4
        self.renderer.discardAllChunks()

        logging.warning(
            'Out of memory, decreasing view distance. {view => %s}' % (
                self.renderer.viewDistance
            )
        )

        config.settings.viewDistance.set(self.renderer.viewDistance)
        config.save()


class EditorToolbar(GLOrtho):
    # is_gl_container = True
    toolbarSize = (204, 24)
    tooltipsUp = True

    toolbarTextureSize = (202., 22.)

    currentToolTextureRect = (0., 22., 24., 24.)
    toolbarWidthRatio = 0.5  # toolbar's width as fraction of screen width.

    def toolbarSizeForScreenWidth(self, width):
        f = max(1, int(width + 418) / 420)

        return map(lambda x: x * f, self.toolbarSize)

        # return ( self.toolbarWidthRatio * width,
        #         self.toolbarWidthRatio * width * self.toolbarTextureSize[1] / self.toolbarTextureSize[0] )

    def __init__(self, rect, tools, *args, **kw):
        GLOrtho.__init__(self, xmin=0, ymin=0,
                         xmax=self.toolbarSize[0], ymax=self.toolbarSize[1],
                         near=-4.0, far=4.0)
        self.size = self.toolbarTextureSize
        self.tools = tools
        for i, t in enumerate(tools):
            t.toolNumber = i
            t.hotkey = i + 1

        self.toolTextures = {}
        self.toolbarDisplayList = glutils.DisplayList()
        self.reloadTextures()

    def set_parent(self, parent):
        GLOrtho.set_parent(self, parent)
        self.parent_resized(0, 0)

    def parent_resized(self, dw, dh):
        self.size = self.toolbarSizeForScreenWidth(self.parent.width)
        self.centerx = self.parent.centerx
        self.bottom = self.parent.viewportContainer.bottom
        # xxx resize children when get

    def getTooltipText(self):
        toolNumber = self.toolNumberUnderMouse(mouse.get_pos())
        return self.tools[toolNumber].tooltipText

    tooltipText = property(getTooltipText)

    def toolNumberUnderMouse(self, pos):
        x, y = self.global_to_local(pos)

        (tx, ty, tw, th) = self.toolbarRectInWindowCoords()

        toolNumber = float(len(self.tools)) * x / tw
        return min(int(toolNumber), len(self.tools) - 1)

    def mouse_down(self, evt):
        if self.parent.level:
            toolNo = self.toolNumberUnderMouse(evt.pos)
            if toolNo < 0 or toolNo > len(self.tools) - 1:
                return
            if evt.button == 1:
                self.selectTool(toolNo)
            if evt.button == 3:
                self.showToolOptions(toolNo)

    def showToolOptions(self, toolNumber):
        if toolNumber < len(self.tools) and toolNumber >= 0:
            t = self.tools[toolNumber]
            # if not t.toolEnabled():
            #    return
            if t.optionsPanel:
                t.optionsPanel.present()

    def selectTool(self, toolNumber):
        ''' pass a number outside the bounds to pick the selection tool'''
        if toolNumber >= len(self.tools) or toolNumber < 0:
            toolNumber = 0

        t = self.tools[toolNumber]
        if not t.toolEnabled():
            return
        if self.parent.currentTool == t:
            self.parent.currentTool.toolReselected()
        else:
            self.parent.selectionTool.hidePanel()
            if self.parent.currentTool != None:
                self.parent.currentTool.cancel()
            self.parent.currentTool = t
            self.parent.currentTool.toolSelected()

    def removeToolPanels(self):
        for tool in self.tools:
            tool.hidePanel()

    def toolbarRectInWindowCoords(self):
        """returns a rectangle (x, y, w, h) representing the toolbar's
        location in the window.  use for hit testing."""

        (pw, ph) = self.parent.size
        pw = float(pw)
        ph = float(ph)
        x, y = self.toolbarSizeForScreenWidth(pw)
        tw = x * 200. / 202.
        th = y * 20. / 22.

        tx = (pw - tw) / 2
        ty = ph - th * 22. / 20.

        return tx, ty, tw, th

    def toolTextureChanged(self):
        self.toolbarDisplayList.invalidate()

    def reloadTextures(self):
        self.toolTextureChanged()
        self.guiTexture = mceutils.loadPNGTexture('gui.png')
        self.toolTextures = {}

        for tool in self.tools:
            if hasattr(tool, 'reloadTextures'):
                tool.reloadTextures()
            if hasattr(tool, 'markerList'):
                tool.markerList.invalidate()

    def drawToolbar(self):
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

        GL.glColor(1., 1., 1., 1.)
        w, h = self.toolbarTextureSize

        self.guiTexture.bind()

        GL.glVertexPointer(3, GL.GL_FLOAT, 0, numpy.array((
                                                              1, h + 1, 0.5,
                                                              w + 1, h + 1, 0.5,
                                                              w + 1, 1, 0.5,
                                                              1, 1, 0.5,
                                                          ), dtype="f4"))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, numpy.array((
                                                                0, 0,
                                                                w, 0,
                                                                w, h,
                                                                0, h,
                                                            ), dtype="f4"))

        GL.glDrawArrays(GL.GL_QUADS, 0, 4)

        for i in range(len(self.tools)):
            tool = self.tools[i]
            if tool.toolIconName is None:
                continue
            try:
                if not tool.toolIconName in self.toolTextures:
                    filename = "toolicons" + os.sep + "{0}.png".format(tool.toolIconName)
                    self.toolTextures[tool.toolIconName] = mceutils.loadPNGTexture(filename)
                x = 20 * i + 4
                y = 4
                w = 16
                h = 16

                self.toolTextures[tool.toolIconName].bind()
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, numpy.array((
                                                                      x, y + h, 1,
                                                                      x + w, y + h, 1,
                                                                      x + w, y, 1,
                                                                      x, y, 1,
                                                                  ), dtype="f4"))
                GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, numpy.array((
                                                                        0, 0,
                                                                        w * 16, 0,
                                                                        w * 16, h * 16,
                                                                        0, h * 16,
                                                                    ), dtype="f4"))

                GL.glDrawArrays(GL.GL_QUADS, 0, 4)
            except Exception:
                logging.exception('Error while drawing toolbar.')
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)

    gfont = None

    def gl_draw(self):

        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glEnable(GL.GL_BLEND)
        self.toolbarDisplayList.call(self.drawToolbar)
        GL.glColor(1.0, 1.0, 0.0)

        # GL.glEnable(GL.GL_BLEND)

        # with gl.glPushMatrix(GL_TEXTURE):
        #    GL.glLoadIdentity()
        #    self.gfont.flatPrint("ADLADLADLADLADL")

        try:
            currentToolNumber = self.tools.index(self.parent.currentTool)
        except ValueError:
            pass
        else:
            # draw a bright rectangle around the current tool
            (texx, texy, texw, texh) = self.currentToolTextureRect
            # ===================================================================
            # tx = tx + tw * float(currentToolNumber) / 9.
            # tx = tx - (2./20.)*float(tw) / 9
            # ty = ty - (2./20.)*th
            # # tw = th
            # tw = (24./20.)* th
            # th = tw
            #
            # ===================================================================
            tx = 20. * float(currentToolNumber)
            ty = 0.
            tw = 24.
            th = 24.
            GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

            self.guiTexture.bind()
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, numpy.array((
                                                                  tx, ty, 2,
                                                                  tx + tw, ty, 2,
                                                                  tx + tw, ty + th, 2,
                                                                  tx, ty + th, 2,
                                                              ), dtype="f4"))

            GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, numpy.array((
                                                                    texx, texy + texh,
                                                                    texx + texw, texy + texh,
                                                                    texx + texw, texy,
                                                                    texx, texy,
                                                                ), dtype="f4"))

            GL.glDrawArrays(GL.GL_QUADS, 0, 4)

        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisable(GL.GL_TEXTURE_2D)

        redOutBoxes = numpy.zeros(9 * 4 * 2, dtype='float32')
        cursor = 0
        for i in range(len(self.tools)):
            t = self.tools[i]
            if t.toolEnabled():
                continue
            redOutBoxes[cursor:cursor + 8] = [
                4 + i * 20, 4,
                4 + i * 20, 20,
                20 + i * 20, 20,
                20 + i * 20, 4,
            ]
            cursor += 8

        if cursor:
            GL.glColor(1.0, 0.0, 0.0, 0.3)
            GL.glVertexPointer(2, GL.GL_FLOAT, 0, redOutBoxes)
            GL.glDrawArrays(GL.GL_QUADS, 0, cursor / 2)

        GL.glDisable(GL.GL_BLEND)
