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
# .# Marks the layout modifications. -- D.C.-G.

import os
import sys
import subprocess
from OpenGL import GL

import numpy
import pygame
from albow import Row, Label, Button, AttrRef, Column, ask, alert, ChoiceButton, CheckBoxLabel, IntInputRow, \
    showProgress, TextInputRow
from albow.translate import _
from config import config
from depths import DepthOffset
from editortools.editortool import EditorTool
from editortools.nudgebutton import NudgeButton
from editortools.tooloptions import ToolOptions
from glbackground import Panel
from mceutils import alertException, drawCube, drawFace, drawTerrainCuttingWire, setWindowCaption
from operation import Operation
import pymclevel
from pymclevel.box import Vector, BoundingBox, FloatBox
from fill import BlockFillOperation
import tempfile
from pymclevel import nbt
import logging
from albow.root import get_root
from fileEdits import fileEdit, GetSort

log = logging.getLogger(__name__)


def GetSelectionColor(colorWord=None):
    return config.selectionColors[config.convert(colorWord or config.selection.color.get())].get()


class SelectionToolOptions(ToolOptions):
    def updateColors(self):
        names = [name.lower() for (name, value) in config.selectionColors.items()]
        self.colorPopupButton.choices = [name.capitalize() for name in names]

        color = config.selection.color.get()

        if color.lower() not in names:
            config.selection.color.set("White")
            color = "White"

        self.colorPopupButton.choiceIndex = names.index(color.lower())

    def __init__(self, tool):
        ToolOptions.__init__(self, name='Panel.SelectionToolOptions')
        self.tool = tool

        self.colorPopupButton = ChoiceButton([], choose=self.colorChanged)
        self.updateColors()

        colorRow = Row((Label("Color: ", align="r"), self.colorPopupButton))
        okButton = Button("OK", action=self.dismiss)
        showPreviousRow = CheckBoxLabel("Show Previous Selection", ref=AttrRef(tool, 'showPreviousSelection'))
        spaceLabel = Label("")
        # .#
        spaceLabel.height /= 1.5
        # .#
        blocksNudgeLabel = Label("Blocks Fast Nudge Settings:")
        blocksNudgeCheckBox = CheckBoxLabel("Move by the width of selection ",
                                            ref=config.fastNudgeSettings.blocksWidth,
                                            tooltipText="Moves selection by his width")
        blocksNudgeNumber = IntInputRow("Width of blocks movement: ",
                                        ref=config.fastNudgeSettings.blocksWidthNumber, width=100, min=2, max=50)
        selectionNudgeLabel = Label("Selection Fast Nudge Settings:")
        selectionNudgeCheckBox = CheckBoxLabel("Move by the width of selection ",
                                               ref=config.fastNudgeSettings.selectionWidth,
                                               tooltipText="Moves selection by his width")
        selectionNudgeNumber = IntInputRow("Width of selection movement: ",
                                           ref=config.fastNudgeSettings.selectionWidthNumber, width=100, min=2, max=50)
        pointsNudgeLabel = Label("Points Fast Nudge Settings:")
        pointsNudgeCheckBox = CheckBoxLabel("Move by the width of selection ",
                                            ref=config.fastNudgeSettings.pointsWidth,
                                            tooltipText="Moves points by the selection's width")
        pointsNudgeNumber = IntInputRow("Width of points movement: ",
                                        ref=config.fastNudgeSettings.pointsWidthNumber, width=100, min=2, max=50)
        staticCommandsNudgeRow = CheckBoxLabel("Static Coords While Nudging",
                                               ref=config.settings.staticCommandsNudge,
                                               tooltipText="Change static coordinates in command blocks while nudging.")

        moveSpawnerPosNudgeRow = CheckBoxLabel("Change Spawners While Nudging",
                                               ref=config.settings.moveSpawnerPosNudge,
                                               tooltipText="Change the position of the mobs in spawners while nudging.")

        def set_colorvalue(ch):
            i = "RGB".index(ch)

            def _set(val):
                choice = self.colorPopupButton.selectedChoice
                values = GetSelectionColor(choice)
                values = values[:i] + (val / 255.0,) + values[i + 1:]
                config.selectionColors[config.convert(choice)].set(str(values))
                self.colorChanged()

            return _set

        def get_colorvalue(ch):
            i = "RGB".index(ch)

            def _get():
                return int(GetSelectionColor()[i] * 255)

            return _get

        colorValuesInputs = [IntInputRow(ch + ":", get_value=get_colorvalue(ch),
                                         set_value=set_colorvalue(ch),
                                         min=0, max=255)
                             for ch in "RGB"]

        colorValuesRow = Row(colorValuesInputs)
        # .#
        #        col = Column((Label("Selection Options"), colorRow, colorValuesRow, showPreviousRow, spaceLabel, blocksNudgeLabel, blocksNudgeCheckBox, blocksNudgeNumber, spaceLabel, selectionNudgeLabel, selectionNudgeCheckBox, selectionNudgeNumber, spaceLabel,  pointsNudgeLabel, pointsNudgeCheckBox, pointsNudgeNumber, okButton))
        col = Column((Label("Selection Options"), colorRow, colorValuesRow, showPreviousRow, spaceLabel,
                      blocksNudgeLabel, blocksNudgeCheckBox, blocksNudgeNumber, spaceLabel, selectionNudgeLabel,
                      selectionNudgeCheckBox, selectionNudgeNumber, spaceLabel, pointsNudgeLabel, pointsNudgeCheckBox,
                      pointsNudgeNumber, spaceLabel, staticCommandsNudgeRow, moveSpawnerPosNudgeRow, okButton),
                     spacing=2)
        # .#

        self.add(col)
        self.shrink_wrap()

    def colorChanged(self):
        config.selection.color.set(self.colorPopupButton.selectedChoice)
        self.tool.updateSelectionColor()


class SelectionToolPanel(Panel):
    def __init__(self, tool, editor):
        Panel.__init__(self, name='Panel.SelectionToolPanel')
        self.tool = tool
        self.editor = editor

        nudgeBlocksButton = NudgeButton(self.editor)
        nudgeBlocksButton.nudge = tool.nudgeBlocks
        nudgeBlocksButton.bg_color = (0.3, 1.0, 0.3, 0.35)
        self.nudgeBlocksButton = nudgeBlocksButton

        deleteBlocksButton = Button("Delete Blocks", action=self.tool.deleteBlocks)
        deleteBlocksButton.tooltipText = _("Fill the selection with Air. Shortcut: {0}").format(
            _(config.keys.deleteBlocks.get()))
        deleteEntitiesButton = Button("Delete Entities", action=self.tool.deleteEntities)
        deleteEntitiesButton.tooltipText = "Remove all entities within the selection"
        deleteTileTicksButton = Button("Delete Tile Ticks", action=self.tool.deleteTileTicks)
        deleteTileTicksButton.tooltipText = "Removes all tile ticks within selection. Tile ticks are scheduled block updates"
        # deleteTileEntitiesButton = Button("Delete TileEntities", action=self.tool.deleteTileEntities)
        analyzeButton = Button("Analyze", action=self.tool.analyzeSelection)
        analyzeButton.tooltipText = "Count the different blocks and entities in the selection and display the totals."
        cutButton = Button("Cut", action=self.tool.cutSelection)
        cutButton.tooltipText = _(
            "Take a copy of all blocks and entities within the selection, then delete everything within the selection. Shortcut: {0}").format(
            config.keys.cut.get())
        copyButton = Button("Copy", action=self.tool.copySelection)
        copyButton.tooltipText = _("Take a copy of all blocks and entities within the selection. Shortcut: {0}").format(
            _(config.keys.copy.get()))
        pasteButton = Button("Paste", action=self.tool.editor.pasteSelection)
        pasteButton.tooltipText = _("Import the last item taken by Cut or Copy. Shortcut: {0}").format(
            _(config.keys.paste.get()))
        exportButton = Button("Export", action=self.tool.exportSelection)
        exportButton.tooltipText = _("Export the selection to a .schematic file. Shortcut: {0}").format(
            _(config.keys.exportSelection.get()))

        selectButton = Button("Select Chunks")
        selectButton.tooltipText = "Expand the selection to the edges of the chunks within"
        selectButton.action = tool.selectChunks
        selectButton.highlight_color = (0, 255, 0)

        deselectButton = Button("Deselect")
        deselectButton.tooltipText = _("Remove the selection. Shortcut: {0}").format(_(config.keys.deselect.get()))
        deselectButton.action = tool.deselect
        deselectButton.highlight_color = (0, 255, 0)

        openButton = Button("CB Commands")
        openButton.tooltipText = _(
            'Open a text file with all command block commands in the currently selected area.\n'
            'Save file to update command blocks.\nRight-click for options')
        openButton.action = tool.openCommands
        openButton.highlight_color = (0, 255, 0)
        openButton.rightClickAction = tool.CBCommandsOptions

        buttonsColumn = [
            nudgeBlocksButton,
            deselectButton,
            selectButton,
            deleteBlocksButton,
            deleteEntitiesButton,
        ]

        if not hasattr(self.editor.level, "noTileTicks"):
            buttonsColumn.append(deleteTileTicksButton)

        buttonsColumn.extend([
            analyzeButton,
            cutButton,
            copyButton,
            pasteButton,
            exportButton,
        ])

        if hasattr(self.editor.level, "editFileNumber"):
            buttonsColumn.append(openButton)

        buttonsColumn = Column(buttonsColumn)

        self.add(buttonsColumn)
        self.shrink_wrap()


class NudgeBlocksOperation(Operation):
    def __init__(self, editor, level, sourceBox, direction):
        super(NudgeBlocksOperation, self).__init__(editor, level)

        self.sourceBox = sourceBox
        self.destBox = BoundingBox(sourceBox.origin + direction, sourceBox.size)
        self.nudgeSelection = NudgeSelectionOperation(editor.selectionTool, direction)
        self.canUndo = False

    def dirtyBox(self):
        return self.sourceBox.union(self.destBox)

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert("Cannot perform action while saving is taking place")
            return
        level = self.editor.level
        tempSchematic = level.extractSchematic(self.sourceBox)
        if tempSchematic:
            dirtyBox = self.dirtyBox()
            if recordUndo:
                self.undoLevel = self.extractUndo(level, dirtyBox)

            level.fillBlocks(self.sourceBox, level.materials.Air)
            level.removeTileEntitiesInBox(self.sourceBox)
            level.removeTileEntitiesInBox(self.destBox)

            level.removeEntitiesInBox(self.sourceBox)
            level.removeEntitiesInBox(self.destBox)
            staticCommandsNudge = config.settings.staticCommandsNudge.get()
            moveSpawnerPosNudge = config.settings.moveSpawnerPosNudge.get()
            level.copyBlocksFrom(tempSchematic, tempSchematic.bounds, self.destBox.origin,
                                 staticCommands=staticCommandsNudge, moveSpawnerPos=moveSpawnerPosNudge)
            self.editor.invalidateBox(dirtyBox)

            self.nudgeSelection.perform(recordUndo)
            if self.nudgeSelection.canUndo:
                self.canUndo = True

    def undo(self):
        super(NudgeBlocksOperation, self).undo()
        self.nudgeSelection.undo()

    def redo(self):
        super(NudgeBlocksOperation, self).redo()
        self.nudgeSelection.redo()


class SelectionTool(EditorTool):
    color = (0.7, 0., 0.7)
    surfaceBuild = False
    toolIconName = "selection2"
    tooltipText = "Select\nRight-click for options"

    bottomLeftPoint = topRightPoint = None

    bottomLeftColor = (0., 0., 1.)
    bottomLeftSelectionColor = (0.75, 0.62, 1.0)

    topRightColor = (0.89, 0.89, 0.35)
    topRightSelectionColor = (1, 0.99, 0.65)

    nudgePanel = None

    def __init__(self, editor):
        self.editor = editor
        editor.selectionTool = self
        self.selectionPoint = None
        self.infoKey = 0
        self.selectKey = 0
        self.deselectKey = 0
        self.root = get_root()

        self.optionsPanel = SelectionToolOptions(self)

        self.updateSelectionColor()

    # --- Tooltips ---

    def describeBlockAt(self, pos):
        blockID = self.editor.level.blockAt(*pos)
        blockdata = self.editor.level.blockDataAt(*pos)
        text = "X: {pos[0]}\nY: {pos[1]}\nZ: {pos[2]}\n".format(pos=pos)
        text += "Light: {0} Sky: {1}\n".format(self.editor.level.blockLightAt(*pos), self.editor.level.skylightAt(*pos))
        text += "{name} ({bid}:{bdata})\n".format(name=self.editor.level.materials.names[blockID][blockdata],
                                                  bid=blockID, pos=pos, bdata=blockdata)
        t = self.editor.level.tileEntityAt(*pos)
        if t:
            text += "TileEntity:\n"
            try:
                text += "{id}: {pos}\n".format(id=t["id"].value, pos=[t[a].value for a in "xyz"])
            except Exception, e:
                text += repr(e)
            if "Items" in t and self.infoKey == 0:
                text += _("--Items omitted. {0} to view. Double-click to edit.--\n").format(
                    _(config.keys.showBlockInfoModifier.get()))
                t = nbt.TAG_Compound(list(t.value))
                del t["Items"]

            text += str(t)
            
        return text

    @property
    def worldTooltipText(self):
        if self.infoKey == 0:
            return
        pos, face = self.editor.blockFaceUnderCursor
        if pos is None:
            return
        try:
            size = None
            box = self.selectionBoxInProgress()
            if box:
                size = "{s[0]} W x {s[2]} L x {s[1]} H".format(s=box.size)
            if size:
                return size
            elif self.dragResizeFace is not None:
                return None
            else:
                return self.describeBlockAt(pos)

        except Exception, e:
            return repr(e)

    @alertException
    def selectChunks(self):
        box = self.selectionBox()
        newBox = BoundingBox((box.mincx << 4, 0, box.mincz << 4),
                             (box.maxcx - box.mincx << 4, self.editor.level.Height, box.maxcz - box.mincz << 4))
        self.editor.selectionTool.setSelection(newBox)

    def updateSelectionColor(self):
        self.selectionColor = GetSelectionColor()
        from albow import theme

        theme.root.sel_color = tuple(int(x * 112) for x in self.selectionColor)
        if self.nudgePanel is not None:
            self.hideNudgePanel()
            self.showPanel()

    # --- Nudge functions ---

    @alertException
    def nudgeBlocks(self, direction):
        if self.editor.rightClickNudge:
            if config.fastNudgeSettings.blocksWidth.get():
                direction = map(int.__mul__, direction, self.selectionBox().size)
            else:
                nudgeWidth = config.fastNudgeSettings.blocksWidthNumber.get()
                direction = map(lambda x: x * nudgeWidth, direction)

        points = self.getSelectionPoints()
        bounds = self.editor.level.bounds

        if not all((p + direction) in bounds for p in points):
            return

        op = NudgeBlocksOperation(self.editor, self.editor.level, self.selectionBox(), direction)
        self.editor.addOperation(op)
        if op.canUndo:
            self.editor.addUnsavedEdit()

    def nudgeSelection(self, direction):
        if self.editor.rightClickNudge == 1:
            if config.fastNudgeSettings.selectionWidth.get():
                direction = map(int.__mul__, direction, self.selectionBox().size)
            else:
                nudgeWidth = config.fastNudgeSettings.selectionWidthNumber.get()
                direction = map(lambda x: x * nudgeWidth, direction)

        points = self.getSelectionPoints()
        bounds = self.editor.level.bounds

        if not all((p + direction) in bounds for p in points):
            return

        op = NudgeSelectionOperation(self, direction)
        self.editor.addOperation(op)

    def nudgePoint(self, p, n):
        if self.selectionBox() is None:
            return
        if self.editor.rightClickNudge == 1:
            if config.fastNudgeSettings.pointsWidth.get():
                n = map(int.__mul__, n, self.selectionBox().size)
            else:
                nudgeWidth = config.fastNudgeSettings.pointsWidthNumber.get()
                n = map(lambda x: x * nudgeWidth, n)
        self.setSelectionPoint(p, self.getSelectionPoint(p) + n)

    def nudgeBottomLeft(self, n):
        return self.nudgePoint(1 - self._oldCurrentCorner, n)

    def nudgeTopRight(self, n):
        return self.nudgePoint(self._oldCurrentCorner, n)

    # --- Panel functions ---
    def sizeLabelText(self):
        size = self.selectionSize()
        if self.dragResizeFace is not None:
            size = self.draggingSelectionBox().size

        return "{0}W x {2}L x {1}H".format(*size)

    def showPanel(self):
        if self.selectionBox() is None:
            return

        if self.nudgePanel is None:
            self.nudgePanel = Panel(name='Panel.SelectionTool.nudgePanel')

            self.nudgePanel.bg_color = map(lambda x: x * 0.5, self.selectionColor) + [0.5, ]

            self.bottomLeftNudge = bottomLeftNudge = NudgeButton(self.editor)
            bottomLeftNudge.anchor = "brwh"

            self.topRightNudge = topRightNudge = NudgeButton(self.editor)
            topRightNudge.anchor = "blwh"

            if self.currentCorner == 0:
                bottomLeftNudge.nudge = self.nudgeTopRight
                topRightNudge.nudge = self.nudgeBottomLeft
                bottomLeftNudge.bg_color = self.topRightColor + (0.33,)
                topRightNudge.bg_color = self.bottomLeftColor + (0.33,)
            else:
                bottomLeftNudge.nudge = self.nudgeBottomLeft
                topRightNudge.nudge = self.nudgeTopRight
                bottomLeftNudge.bg_color = self.bottomLeftColor + (0.33,)
                topRightNudge.bg_color = self.topRightColor + (0.33,)

            self.nudgeRow = Row((bottomLeftNudge, topRightNudge))
            self.nudgeRow.anchor = "blrh"
            self.nudgePanel.add(self.nudgeRow)

            self.editor.add(self.nudgePanel)

            self.nudgeSelectionButton = NudgeButton(self.editor)
            self.nudgeSelectionButton.nudge = self.nudgeSelection
            self.nudgeSelectionButton.bg_color = self.selectionColor + (0.7,)
            self.nudgeSelectionButton.anchor = "twh"

            self.spaceLabel = Label("")
            self.spaceLabel.anchor = "twh"
            self.spaceLabel.height = 3
            self.nudgePanel.add(self.spaceLabel)

        if hasattr(self, 'sizeLabel'):
            self.nudgePanel.remove(self.sizeLabel)
        self.sizeLabel = Label(self.sizeLabelText())
        self.sizeLabel.anchor = "wh"
        self.sizeLabel.tooltipText = _("{0:n} blocks").format(self.selectionBox().volume)

        self.nudgePanel.top = 0
        self.nudgePanel.left = 0

        self.nudgePanel.add(self.sizeLabel)

        self.nudgePanel.add(self.nudgeSelectionButton)
        self.spaceLabel.height = 3
        self.nudgeSelectionButton.top = self.spaceLabel.bottom
        self.sizeLabel.top = self.nudgeSelectionButton.bottom
        self.nudgeRow.top = self.sizeLabel.bottom

        self.nudgePanel.shrink_wrap()
        self.sizeLabel.centerx = self.nudgePanel.centerx
        self.nudgeRow.centerx = self.nudgePanel.centerx
        self.nudgeSelectionButton.centerx = self.nudgePanel.centerx

        self.nudgePanel.bottom = self.editor.toolbar.top
        self.nudgePanel.centerx = self.editor.centerx

        self.nudgePanel.anchor = "bwh"

        if self.panel is None and self.editor.currentTool in (self, None):
            if self.bottomLeftPoint is not None and self.topRightPoint is not None:
                self.panel = SelectionToolPanel(self, self.editor)
                self.panel.left = self.editor.left
                self.panel.centery = self.editor.centery
                self.editor.add(self.panel)

    def hidePanel(self):
        self.editor.remove(self.panel)
        self.panel = None

    def hideNudgePanel(self):
        self.editor.remove(self.nudgePanel)
        self.nudgePanel = None

    selectionInProgress = False
    dragStartPoint = None

    # --- Event handlers ---

    def toolReselected(self):
        self.selectOtherCorner()

    def toolSelected(self):
        self.showPanel()

    def clampPos(self, pos):
        x, y, z = pos
        w, h, l = self.editor.level.Width, self.editor.level.Height, self.editor.level.Length

        if w > 0:
            if x >= w:
                x = w - 1
            if x < 0:
                x = 0
        if l > 0:
            if z >= l:
                z = l - 1
            if z < 0:
                z = 0

        if y >= h:
            y = h - 1
        if y < 0:
            y = 0

        pos = [x, y, z]
        return pos

    @property
    def currentCornerName(self):
        return (_("Blue"), _("Yellow"))[self.currentCorner]

    @property
    def statusText(self):
        if self.selectionInProgress:
            pd = self.editor.blockFaceUnderCursor
            if pd:
                p, d = pd
                if self.dragStartPoint == p:
                    if self.clickSelectionInProgress:

                        return _(
                            "Click the mouse button again to place the {0} selection corner. Press {1} to switch corners.").format(
                            self.currentCornerName, self.hotkey)
                    else:
                        return _(
                            "Release the mouse button here to place the {0} selection corner. Press {1} to switch corners.").format(
                            self.currentCornerName, self.hotkey)

            if self.clickSelectionInProgress:
                return _("Click the mouse button again to place the other selection corner.")

            return _("Release the mouse button to finish the selection")

        return _(
            "Click or drag to make a selection. Drag the selection walls to resize. Click near the edge to drag the opposite wall.").format(
            self.currentCornerName, self.hotkey)

    clickSelectionInProgress = False

    def endSelection(self):
        self.selectionInProgress = False
        self.clickSelectionInProgress = False
        self.dragResizeFace = None
        self.dragStartPoint = None

    def cancel(self):
        self.endSelection()
        EditorTool.cancel(self)

    dragResizeFace = None
    dragResizeDimension = None
    dragResizePosition = None

    def mouseDown(self, evt, pos, direction):
        pos = self.clampPos(pos)
        if self.selectionBox() and not self.selectionInProgress:
            face, point = self.boxFaceUnderCursor(self.selectionBox())

            if face is not None:
                self.dragResizeFace = face
                self.dragResizeDimension = self.findBestTrackingPlane(face)

                self.dragResizePosition = point[self.dragResizeDimension]

                return

        if self.selectionInProgress is False:
            self.dragStartPoint = pos
        self.selectionInProgress = True

    def mouseUp(self, evt, pos, direction):
        pos = self.clampPos(pos)
        if self.dragResizeFace is not None:
            box = self.selectionBox()
            if box is not None:
                o, m = self.selectionPointsFromDragResize()
                x, y, z = self.bottomLeftPoint
                if (x == o[0] or x == m[0]) and (y == o[1] or y == m[1]) and (z == o[2] or z == m[2]):
                    first = self.bottomLeftPoint
                    isFirst = True
                else:
                    first = self.topRightPoint
                    isFirst = False
                second = []
                for i in range(3):
                    if o[i] == first[i]:
                        second.append(m[i])
                    else:
                        second.append(o[i])

                if isFirst:
                    o = first
                    m = second
                else:
                    o = second
                    m = first
                op = SelectionOperation(self, (o, m))
                self.editor.addOperation(op)

            self.dragResizeFace = None
            return

        if self.editor.viewMode == "Chunk":
            self.clickSelectionInProgress = True

        if self.dragStartPoint is None and not self.clickSelectionInProgress:
            return

        if self.dragStartPoint != pos or self.clickSelectionInProgress:
            self._oldCurrentCorner = self.currentCorner
            if self.panel is not None:
                if self.currentCorner == 0:
                    self.bottomLeftNudge.nudge = self.nudgeTopRight
                    self.topRightNudge.nudge = self.nudgeBottomLeft
                    self.bottomLeftNudge.bg_color = self.topRightColor + (0.33,)
                    self.topRightNudge.bg_color = self.bottomLeftColor + (0.33,)
                else:
                    self.bottomLeftNudge.nudge = self.nudgeBottomLeft
                    self.topRightNudge.nudge = self.nudgeTopRight
                    self.bottomLeftNudge.bg_color = self.bottomLeftColor + (0.33,)
                    self.topRightNudge.bg_color = self.topRightColor + (0.33,)
            op = SelectionOperation(self, (self.dragStartPoint, pos))
            self.editor.addOperation(op)
            self.selectionInProgress = False
            self.clickSelectionInProgress = False
            self.dragStartPoint = None

        else:
            points = self.getSelectionPoints()
            if not all(points):
                points = (pos, pos)  # set both points on the first click
            else:
                points[self.currentCorner] = pos
            if not self.clickSelectionInProgress:
                self.clickSelectionInProgress = True
            else:
                op = SelectionOperation(self, points)
                self.editor.addOperation(op)

                self.selectOtherCorner()
                self.selectionInProgress = False
                self.clickSelectionInProgress = False

        if self.chunkMode:
            if self.selectKey == 1:
                selectKeyBool = True
            else:
                selectKeyBool = False
            if self.deselectKey == 1:
                deselectKeyBool = True
            else:
                deselectKeyBool = False

            self.editor.selectionToChunks(remove=deselectKeyBool, add=selectKeyBool)
            self.editor.toolbar.selectTool(8)

    def keyDown(self, evt):
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        if keyname == config.keys.showBlockInfo.get():
            self.infoKey = 1
        if keyname == config.keys.selectChunks.get():
            self.selectKey = 1
        if keyname == config.keys.deselectChunks.get():
            self.deselectKey = 1

    def keyUp(self, evt):
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        if keyname == config.keys.selectChunks.get():
            self.selectKey = 0
        if keyname == config.keys.deselectChunks.get():
            self.deselectKey = 0

    @property
    def chunkMode(self):
        return self.editor.viewMode == "Chunk" or self.editor.currentTool is self.editor.toolbar.tools[8]

    def selectionBoxInProgress(self):
        if self.editor.blockFaceUnderCursor is None:
            return
        pos = self.editor.blockFaceUnderCursor[0]
        if self.selectionInProgress or self.clickSelectionInProgress:
            return self.selectionBoxForCorners(pos, self.dragStartPoint)

            # requires a selection

    def dragResizePoint(self):
        # returns a point representing the intersection between the mouse ray
        # and an imaginary plane perpendicular to the dragged face

        pos = self.editor.mainViewport.cameraPosition
        dim = self.dragResizeDimension
        distance = self.dragResizePosition - pos[dim]

        mouseVector = self.editor.mainViewport.mouseVector
        scale = distance / (mouseVector[dim] or 0.0001)
        point = map(lambda a, b: a * scale + b, mouseVector, pos)
        return point

    def draggingSelectionBox(self):
        p1, p2 = self.selectionPointsFromDragResize()
        box = self.selectionBoxForCorners(p1, p2)
        return box

    def selectionPointsFromDragResize(self):
        point = self.dragResizePoint()
        # glColor(1.0, 1.0, 0.0, 1.0)
        #        glPointSize(9.0)
        #        glBegin(GL_POINTS)
        #        glVertex3f(*point)
        #        glEnd()
        #

        #        facebox = BoundingBox(box.origin, box.size)
        #        facebox.origin[dim] = self.dragResizePosition
        #        facebox.size[dim] = 0
        #        glEnable(GL_BLEND)
        #
        #        drawFace(facebox, dim * 2)
        #
        #        glDisable(GL_BLEND)
        #
        side = self.dragResizeFace & 1
        dragdim = self.dragResizeFace >> 1
        box = self.selectionBox()

        o, m = list(box.origin), list(box.maximum)
        (m, o)[side][dragdim] = int(numpy.floor(point[dragdim] + 0.5))
        m = map(lambda a: a - 1, m)
        return o, m

    def option1(self):
        self.selectOtherCorner()

    _currentCorner = 1
    _oldCurrentCorner = 1

    @property
    def currentCorner(self):
        return self._currentCorner

    @currentCorner.setter
    def currentCorner(self, value):
        self._currentCorner = value & 1
        self.toolIconName = ("selection", "selection2")[self._currentCorner]
        self.editor.toolbar.toolTextureChanged()

    def selectOtherCorner(self):
        self.currentCorner = 1 - self.currentCorner

    showPreviousSelection = config.selection.showPreviousSelection.property()
    alpha = 0.25

    def drawToolMarkers(self):

        selectionBox = self.selectionBox()
        if selectionBox:
            widg = self.editor.find_widget(pygame.mouse.get_pos())

            # these corners stay even while using the chunk tool.
            GL.glPolygonOffset(DepthOffset.SelectionCorners, DepthOffset.SelectionCorners)
            lineWidth = 3
            if self._oldCurrentCorner == 1:
                bottomLeftColor = self.bottomLeftColor
                topRightColor = self.topRightColor
            else:
                bottomLeftColor = self.topRightColor
                topRightColor = self.bottomLeftColor
            for t, c, n in ((self.bottomLeftPoint, bottomLeftColor, self.bottomLeftNudge),
                            (self.topRightPoint, topRightColor, self.topRightNudge)):
                if t is not None and not self.selectionInProgress:
                    (sx, sy, sz) = t

                    # draw a blue or yellow wireframe box at the selection corner
                    r, g, b = c
                    alpha = 0.4
                    try:
                        bt = self.editor.level.blockAt(sx, sy, sz)
                        if bt:
                            alpha = 0.2
                    except (EnvironmentError, pymclevel.ChunkNotPresent):
                        pass

                    GL.glLineWidth(lineWidth)
                    lineWidth += 1

                    # draw highlighted block faces when nudging
                    if widg.parent == n or widg == n:
                        GL.glEnable(GL.GL_BLEND)
                        nudgefaces = numpy.array([
                            selectionBox.minx, selectionBox.miny, selectionBox.minz,
                            selectionBox.minx, selectionBox.maxy, selectionBox.minz,
                            selectionBox.minx, selectionBox.maxy, selectionBox.maxz,
                            selectionBox.minx, selectionBox.miny, selectionBox.maxz,
                            selectionBox.minx, selectionBox.miny, selectionBox.minz,
                            selectionBox.maxx, selectionBox.miny, selectionBox.minz,
                            selectionBox.maxx, selectionBox.miny, selectionBox.maxz,
                            selectionBox.minx, selectionBox.miny, selectionBox.maxz,
                            selectionBox.minx, selectionBox.miny, selectionBox.minz,
                            selectionBox.minx, selectionBox.maxy, selectionBox.minz,
                            selectionBox.maxx, selectionBox.maxy, selectionBox.minz,
                            selectionBox.maxx, selectionBox.miny, selectionBox.minz,
                        ], dtype='float32')

                        if sx != selectionBox.minx:
                            nudgefaces[0:12:3] = selectionBox.maxx
                        if sy != selectionBox.miny:
                            nudgefaces[13:24:3] = selectionBox.maxy
                        if sz != selectionBox.minz:
                            nudgefaces[26:36:3] = selectionBox.maxz

                        GL.glColor(r, g, b, 0.3)
                        GL.glVertexPointer(3, GL.GL_FLOAT, 0, nudgefaces)
                        GL.glEnable(GL.GL_DEPTH_TEST)
                        GL.glDrawArrays(GL.GL_QUADS, 0, 12)
                        GL.glDisable(GL.GL_DEPTH_TEST)

                        GL.glDisable(GL.GL_BLEND)

                    GL.glColor(r, g, b, alpha)
                    drawCube(BoundingBox((sx, sy, sz), (1, 1, 1)), GL.GL_LINE_STRIP)

            if not (not self.showPreviousSelection and self.selectionInProgress):
                # draw the current selection as a white box.  hangs around when you use other tools.
                GL.glPolygonOffset(DepthOffset.Selection, DepthOffset.Selection)
                color = self.selectionColor + (self.alpha,)
                if self.dragResizeFace is not None:
                    box = self.draggingSelectionBox()
                else:
                    box = selectionBox

                if self.panel and (widg is self.panel.nudgeBlocksButton or widg.parent is self.panel.nudgeBlocksButton):
                    color = (0.3, 1.0, 0.3, self.alpha)
                self.editor.drawConstructionCube(box, color)

                # highlight the face under the cursor, or the face being dragged
                if self.dragResizeFace is None:
                    if self.selectionInProgress or self.clickSelectionInProgress:
                        pass
                    else:
                        face, point = self.boxFaceUnderCursor(box)

                        if face is not None:
                            GL.glEnable(GL.GL_BLEND)
                            GL.glColor(*color)

                            # Shrink the highlighted face to show the click-through edges

                            offs = [s * self.edge_factor for s in box.size]
                            offs[face >> 1] = 0
                            origin = [o + off for o, off in zip(box.origin, offs)]
                            size = [s - off * 2 for s, off in zip(box.size, offs)]

                            cv = self.editor.mainViewport.cameraVector
                            for i in range(3):
                                if cv[i] > 0:
                                    origin[i] -= offs[i]
                                    size[i] += offs[i]
                                else:
                                    size[i] += offs[i]

                            smallbox = FloatBox(origin, size)

                            drawFace(smallbox, face)

                            GL.glColor(0.9, 0.6, 0.2, 0.8)
                            GL.glLineWidth(2.0)
                            drawFace(box, face, type=GL.GL_LINE_STRIP)
                            GL.glDisable(GL.GL_BLEND)
                else:
                    face = self.dragResizeFace
                    point = self.dragResizePoint()
                    dim = face >> 1
                    pos = point[dim]

                    side = face & 1
                    o, m = selectionBox.origin, selectionBox.maximum
                    otherFacePos = (m, o)[side ^ 1][dim]  # ugly
                    direction = (-1, 1)[side]
                    # print "pos", pos, "otherFace", otherFacePos, "dir", direction
                    # print "m", (pos - otherFacePos) * direction
                    if (pos - otherFacePos) * direction > 0:
                        face ^= 1

                    GL.glColor(0.9, 0.6, 0.2, 0.5)
                    drawFace(box, face, type=GL.GL_LINE_STRIP)
                    GL.glEnable(GL.GL_BLEND)
                    GL.glEnable(GL.GL_DEPTH_TEST)

                    drawFace(box, face)
                    GL.glDisable(GL.GL_BLEND)
                    GL.glDisable(GL.GL_DEPTH_TEST)

        selectionColor = map(lambda a: a * a * a * a, self.selectionColor)

        # draw a colored box representing the possible selection
        otherCorner = self.dragStartPoint
        if self.dragResizeFace is not None:
            self.showPanel()  # xxx do this every frame while dragging because our UI kit is bad

        if (self.selectionInProgress or self.clickSelectionInProgress) and otherCorner is not None:
            GL.glPolygonOffset(DepthOffset.PotentialSelection, DepthOffset.PotentialSelection)

            pos, direction = self.editor.blockFaceUnderCursor
            if pos is not None:
                box = self.selectionBoxForCorners(otherCorner, pos)
                if self.chunkMode:
                    box = box.chunkBox(self.editor.level)
                    if self.deselectKey == 1:
                        selectionColor = [1., 0., 0.]
                self.editor.drawConstructionCube(box, selectionColor + [self.alpha, ])
        else:
            # don't draw anything at the mouse cursor if we're resizing the box
            if self.dragResizeFace is None:
                box = self.selectionBox()
                if box:
                    face, point = self.boxFaceUnderCursor(box)
                    if face is not None:
                        return
            else:
                return

    def drawToolReticle(self):
        GL.glPolygonOffset(DepthOffset.SelectionReticle, DepthOffset.SelectionReticle)
        pos, direction = self.editor.blockFaceUnderCursor

        # draw a selection-colored box for the cursor reticle
        selectionColor = map(lambda a: a * a * a * a, self.selectionColor)
        r, g, b = selectionColor
        alpha = 0.3

        try:
            bt = self.editor.level.blockAt(*pos)
            if bt:
                # #                textureCoords = materials[bt][0]
                alpha = 0.12
        except (EnvironmentError, pymclevel.ChunkNotPresent):
            pass

        # cube sides
        GL.glColor(r, g, b, alpha)
        GL.glDepthMask(False)
        GL.glEnable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DEPTH_TEST)
        drawCube(BoundingBox(pos, (1, 1, 1)))
        GL.glDepthMask(True)
        GL.glDisable(GL.GL_DEPTH_TEST)

        drawTerrainCuttingWire(BoundingBox(pos, (1, 1, 1)),
                               (r, g, b, 0.4),
                               (1., 1., 1., 1.0)
                               )

        GL.glDisable(GL.GL_BLEND)

    def setSelection(self, box):
        if box is None:
            self.selectNone()
        else:
            self.setSelectionPoints(self.selectionPointsFromBox(box))

    @staticmethod
    def selectionPointsFromBox(box):
        return box.origin, map(lambda x: x - 1, box.maximum)

    def selectNone(self):
        self.setSelectionPoints(None)

    def selectAll(self):
        box = self.editor.level.bounds
        op = SelectionOperation(self, self.selectionPointsFromBox(box))
        self.editor.addOperation(op)

    def deselect(self):
        if self.selectionBox() is not None:
            op = SelectionOperation(self, None)
            self.editor.addOperation(op)

    def setSelectionPoint(self, pointNumber, newPoint):
        points = self.getSelectionPoints()
        points[pointNumber] = newPoint
        self.setSelectionPoints(points)

    def setSelectionPoints(self, points, changeSelection=True):
        if points:
            self.bottomLeftPoint, self.topRightPoint = [Vector(*p) if p else None for p in points]
        else:
            self.bottomLeftPoint = self.topRightPoint = None

        if changeSelection:
            self._selectionChanged()
            self.editor.selectionChanged()

    def _selectionChanged(self):
        if self.selectionBox():
            self.showPanel()
        else:
            self.hidePanel()
            self.hideNudgePanel()

    def getSelectionPoint(self, pointNumber):
        return (self.bottomLeftPoint, self.topRightPoint)[pointNumber]

    def getSelectionPoints(self):
        return [self.bottomLeftPoint, self.topRightPoint]

    @alertException
    def deleteBlocks(self):
        box = self.selectionBox()
        if None is box:
            return
        if box == box.chunkBox(self.editor.level):
            resp = ask(
                "You are deleting a chunk-shaped selection. Fill the selection with Air, or delete the chunks themselves?",
                responses=["Fill with Air", "Delete Chunks", "Cancel"])
            if resp == "Delete Chunks":
                self.editor.toolbar.tools[8].destroyChunks(box.chunkPositions)
            elif resp == "Fill with Air":
                self._deleteBlocks()
                self.editor.renderer.discardAllChunks()
        else:
            self._deleteBlocks()

    def _deleteBlocks(self):
        box = self.selectionBox()
        if None is box:
            return
        op = BlockFillOperation(self.editor, self.editor.level, box, self.editor.level.materials.Air, [])
        with setWindowCaption("DELETING - "):
            self.editor.freezeStatus(_("Deleting {0} blocks").format(box.volume))

            self.editor.addOperation(op)
            self.editor.invalidateBox(box)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @alertException
    def deleteTileTicks(self, recordUndo=True):
        box = self.selectionBox()

        with setWindowCaption("WORKING - "):
            self.editor.freezeStatus("Removing Tile Ticks...")
            level = self.editor.level
            editor = self.editor

            class DeleteTileTicksOperation(Operation):
                def __init__(self, editor, level):
                    self.editor = editor
                    self.level = level
                    self.canUndo = True

                def perform(self, recordUndo=True):
                    self.undoTileTicks = level.getTileTicksInBox(box)
                    level.removeTileTicksInBox(box)
                    editor.renderer.invalidateTileTicksInBox(box)

                def undo(self):
                    self.redoTileTicks = level.getTileTicksInBox(box)
                    level.removeTileTicksInBox(box)
                    level.addTileTicks(self.undoTileTicks)
                    editor.renderer.invalidateTileTicksInBox(box)

                def redo(self):
                    self.undoTileTicks = level.getTileTicksInBox(box)
                    level.removeTileTicksInBox(box)
                    level.addTileTicks(self.redoTileTicks)
                    editor.renderer.invalidateTileTicksInBox(box)

            op = DeleteTileTicksOperation(self.editor, self.editor.level)
            op.canUndo = recordUndo
            self.editor.addOperation(op)
            self.editor.invalidateBox(box)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @alertException
    def deleteEntities(self, recordUndo=True):
        box = self.selectionBox()
        if box is None:
            return

        with setWindowCaption("WORKING - "):
            self.editor.freezeStatus("Removing entities...")
            level = self.editor.level
            editor = self.editor

            class DeleteEntitiesOperation(Operation):
                def __init__(self, editor, level):
                    self.editor = editor
                    self.level = level
                    self.canUndo = True

                def perform(self, recordUndo=True):
                    self.undoEntities = level.getEntitiesInBox(box)
                    level.removeEntitiesInBox(box)
                    editor.renderer.invalidateEntitiesInBox(box)

                def undo(self):
                    self.redoEntities = level.getEntitiesInBox(box)
                    level.removeEntitiesInBox(box)
                    level.addEntities(self.undoEntities)
                    editor.renderer.invalidateEntitiesInBox(box)

                def redo(self):
                    self.undoEntities = level.getEntitiesInBox(box)
                    level.removeEntitiesInBox(box)
                    level.addEntities(self.redoEntities)
                    editor.renderer.invalidateEntitiesInBox(box)

            op = DeleteEntitiesOperation(self.editor, self.editor.level)
            op.canUndo = recordUndo
            self.editor.addOperation(op)
            self.editor.invalidateBox(box)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @alertException
    def analyzeSelection(self):
        box = self.selectionBox()
        self.editor.analyzeBox(self.editor.level, box)

    @alertException
    def cutSelection(self):
        if not self.selectionBox():
            return
        self.copySelection()
        self.deleteBlocks()
        self.deleteEntities(False)
        self.deleteTileTicks(False)

    @alertException
    def copySelection(self):
        schematic = self._copySelection()
        if schematic:
            self.editor.addCopiedSchematic(schematic)

    def _copySelection(self):
        box = self.selectionBox()
        if not box:
            return

        shape = box.size

        self.editor.mouseLookOff()

        print "Clipping: ", shape

        fileFormat = "schematic"
        if box.volume > self.maxBlocks:
            fileFormat = "schematic.zip"

        if fileFormat == "schematic.zip":
            missingChunks = filter(lambda x: not self.editor.level.containsChunk(*x), box.chunkPositions)
            if len(missingChunks):
                if not ((box.origin[0] & 0xf == 0) and (box.origin[2] & 0xf == 0)):
                    if ask(
                            "This is an uneven selection with missing chunks. Expand the selection to chunk edges, or copy air within the missing chunks?",
                            ["Expand Selection", "Copy Air"]) == "Expand Selection":
                        self.selectChunks()
                        box = self.selectionBox()

        cancelCommandBlockOffset = config.schematicCopying.cancelCommandBlockOffset.get()
        with setWindowCaption("Copying - "):
            filename = tempfile.mkdtemp(".zip", "mceditcopy")
            os.rmdir(filename)

            status = _("Copying {0:n} blocks...").format(box.volume)
            if fileFormat == "schematic":
                schematic = showProgress(status,
                                         self.editor.level.extractSchematicIter(box, cancelCommandBlockOffset=cancelCommandBlockOffset), cancel=True)
            else:
                schematic = showProgress(status,
                                         self.editor.level.extractZipSchematicIter(box, filename, cancelCommandBlockOffset=cancelCommandBlockOffset), cancel=True)
            if schematic == "Canceled":
                return None

            return schematic

    @alertException
    def exportSelection(self):
        schematic = self._copySelection()
        
        if schematic:
            # result = ask("Select a format:", ["schematic", "structure", "Cancel"])
            # if result == "schematic":
            self.editor.exportSchematic(schematic)
            # elif result == "structure":
            #    print "Author: {}".format(author)

    @alertException
    def openCommands(self):
        name = "CommandsFile" + str(self.editor.level.editFileNumber) + "." + config.commands.fileFormat.get()
        filename = os.path.join(self.editor.level.fileEditsFolder.filename, name)
        fp = open(filename, 'w')
        first = True
        space = config.commands.space.get()
        sorting = config.commands.sorting.get()
        edit = fileEdit(filename, os.path.getmtime(filename), self.editor.selectionBox(), self.editor,
                        self.editor.level)

        order = []
        if sorting == "chain":
            skip = []
            done = []
            chainStored = []
            for coords in GetSort(self.editor.selectionBox(), sorting):
                (x, y, z) = coords
                if (x, y, z) in skip:
                    skip.remove((x, y, z))
                    continue
                blockID = self.editor.level.blockAt(x, y, z)
                if blockID == 211:
                    chainStored.append((x, y, z))
                    continue
                if blockID == 137 or blockID == 210:
                    edit.writeCommandInFile(first, space, (x, y, z), fp, skip, True, done, order)
                    first = False
            for (x, y, z) in chainStored:
                if (x, y, z) in done:
                    continue
                edit.writeCommandInFile(first, space, (x, y, z), fp, skip, True, done, order)

        else:
            for coords in GetSort(self.editor.selectionBox(), sorting):
                if sorting == "xz":
                    (x, y, z) = coords
                else:
                    (z, y, x) = coords
                blockID = self.editor.level.blockAt(x, y, z)
                if blockID == 137 or blockID == 210 or blockID == 211:
                    edit.writeCommandInFile(first, space, (x, y, z), fp, None, False, None, order)
                    first = False
        fp.close()
        if first:
            os.remove(filename)
            alert("No command blocks found")
            del edit
            return
        edit.order = order
        self.editor.level.editFileNumber += 1
        self.root.filesToChange.append(edit)
        if sys.platform == "win32":
            os.startfile(filename)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, filename])

    def CBCommandsOptions(self):
        panel = CBCommandsOptionsPanel()
        panel.present()


class CBCommandsOptionsPanel(ToolOptions):
    def __init__(self):
        Panel.__init__(self, name='Panel.CBCommandsOptionsPanel')

        empty = Label("")

        self.sorting = ChoiceButton(["chain", "xz", "zx"], choose=self.changeSorting)
        self.sorting.selectedChoice = config.commands.sorting.get()
        sortingRow = Row((Label("Sort Order"), self.sorting))
        space = CheckBoxLabel("Space between lines",
                              tooltipText="Make space between the lines",
                              ref=config.commands.space)
        fileFormat = TextInputRow("File format",
                                  tooltipText="Choose the file format for the files",
                                  ref=config.commands.fileFormat)
        okButton = Button("OK", action=self.dismiss)

        col = Column((Label("Command Blocks Commands Options"), sortingRow, empty, space, empty, fileFormat, okButton),
                     spacing=2)

        self.add(col)
        self.shrink_wrap()

    def changeSorting(self):
        config.commands.sorting.set(self.sorting.selectedChoice)


class SelectionOperation(Operation):
    changedLevel = False

    def __init__(self, selectionTool, points):
        super(SelectionOperation, self).__init__(selectionTool.editor, selectionTool.editor.level)
        self.selectionTool = selectionTool
        self.points = points
        self.canUndo = True

    def perform(self, recordUndo=True):
        self.undoPoints = self.selectionTool.getSelectionPoints()
        self.selectionTool.setSelectionPoints(self.points)

    def undo(self):
        self.redoPoints = self.selectionTool.getSelectionPoints()
        points = self.points
        self.points = self.undoPoints
        self.undoPoints = self.selectionTool.getSelectionPoints()
        changeSelection = "select" in "{}".format(self.editor.currentTool)
        self.selectionTool.setSelectionPoints(self.points, changeSelection)
        self.points = points

    def redo(self):
        self.undoPoints = self.selectionTool.getSelectionPoints()
        points = self.points
        self.points = self.redoPoints
        self.undoPoints = self.selectionTool.getSelectionPoints()
        changeSelection = "select" in "{}".format(self.editor.currentTool)
        self.selectionTool.setSelectionPoints(self.points, changeSelection)
        self.points = points


class NudgeSelectionOperation(Operation):
    changedLevel = False

    def __init__(self, selectionTool, direction):
        super(NudgeSelectionOperation, self).__init__(selectionTool.editor, selectionTool.editor.level)
        self.selectionTool = selectionTool
        self.direction = direction
        self.undoPoints = selectionTool.getSelectionPoints()
        self.newPoints = [p + direction for p in self.undoPoints]
        self.canUndo = True

    def perform(self, recordUndo=True):
        self.selectionTool.setSelectionPoints(self.newPoints)

    oldSelection = None

    def undo(self):
        self.redoPoints = self.selectionTool.getSelectionPoints()
        self.selectionTool.setSelectionPoints(self.undoPoints)

    def redo(self):
        self.undoPoints = self.selectionTool.getSelectionPoints()
        self.selectionTool.setSelectionPoints(self.redoPoints)
