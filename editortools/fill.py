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
from OpenGL import GL
import numpy
from albow import Label, Button, Column, alert, AttrRef, showProgress, CheckBoxLabel
from albow.translate import _
from depths import DepthOffset
from editortools.blockpicker import BlockPicker
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from editortools.tooloptions import ToolOptions
from glbackground import Panel
from glutils import Texture
from mceutils import alertException, setWindowCaption
from operation import Operation
from pymclevel.blockrotation import Roll, RotateLeft, FlipVertical, FlipEastWest, FlipNorthSouth

from config import config
from albow.root import get_root
import pymclevel
from numpy import array


class BlockFillOperation(Operation):
    def __init__(self, editor, destLevel, destBox, blockInfo, blocksToReplace, noData=False):
        super(BlockFillOperation, self).__init__(editor, destLevel)
        self.noData = noData
        self.destBox = destBox
        self.blockInfo = blockInfo
        self.blocksToReplace = blocksToReplace
        self.canUndo = False

    def name(self):
        return _("Fill with ") + self.blockInfo.name

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert("Cannot perform action while saving is taking place")
            return
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self.destBox)

        destBox = self.destBox
        if self.level.bounds == self.destBox:
            destBox = None

        fill = self.level.fillBlocksIter(destBox, self.blockInfo, blocksToReplace=self.blocksToReplace, noData=self.noData)
        showProgress("Replacing blocks...", fill, cancel=True)
        self.canUndo = True

    def bufferSize(self):
        return self.destBox.volume * 2

    def dirtyBox(self):
        return self.destBox


class FillToolPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self, name='Panel.FillToolPanel')
        self.tool = tool
        replacing = tool.replacing

        self.blockButton = BlockButton(tool.editor.level.materials)
        self.blockButton.blockInfo = tool.blockInfo
        self.blockButton.action = self.pickFillBlock

        self.fillWithLabel = Label("Fill with:", width=self.blockButton.width, align="c")
        self.fillButton = Button("Fill", action=tool.confirm, width=self.blockButton.width)
        self.fillButton.tooltipText = "Shortcut: Enter"

        rollkey = config.keys.replaceShortcut.get()

        self.replaceLabel = replaceLabel = Label("Replace", width=self.blockButton.width)
        replaceLabel.mouse_down = lambda a: self.tool.toggleReplacing()
        replaceLabel.fg_color = (177, 177, 255, 255)
        # replaceLabelRow = Row( (Label(rollkey), replaceLabel) )
        replaceLabel.tooltipText = _("Shortcut: {0}").format(_(rollkey))
        replaceLabel.align = "c"
        self.noDataCheckBox = CheckBoxLabel("Keep Data Intact", ref=AttrRef(self.tool, "noData"))
        
        col = (self.fillWithLabel,
               self.blockButton,
               # swapRow,
               replaceLabel,
               # self.replaceBlockButton,
               self.fillButton)

        if replacing:
            self.fillWithLabel = Label("Find:", width=self.blockButton.width, align="c")

            self.replaceBlockButton = BlockButton(tool.editor.level.materials)
            self.replaceBlockButton.blockInfo = tool.replaceBlockInfo
            self.replaceBlockButton.action = self.pickReplaceBlock
            self.replaceLabel.text = "Replace with:"
            self.replaceLabel.tooltipText = _("Shortcut: {0}").format(_("Esc"))

            self.swapButton = Button("Swap", action=self.swapBlockTypes, width=self.blockButton.width)
            self.swapButton.fg_color = (255, 255, 255, 255)
            self.swapButton.highlight_color = (60, 255, 60, 255)
            swapkey = config.keys.swap.get()

            self.swapButton.tooltipText = _("Shortcut: {0}").format(_(swapkey))

            self.fillButton = Button("Replace", action=tool.confirm, width=self.blockButton.width)
            self.fillButton.tooltipText = "Shortcut: Enter"

            col = (self.fillWithLabel,
                   self.blockButton,
                   replaceLabel,
                   self.replaceBlockButton,
                   self.noDataCheckBox,
                   self.swapButton,
                   self.fillButton)

        col = Column(col)

        self.add(col)
        self.shrink_wrap()

    def swapBlockTypes(self):
        t = self.tool.replaceBlockInfo
        self.tool.replaceBlockInfo = self.tool.blockInfo
        self.tool.blockInfo = t

        self.replaceBlockButton.blockInfo = self.tool.replaceBlockInfo
        self.blockButton.blockInfo = self.tool.blockInfo  # xxx put this in a property

    def pickReplaceBlock(self):
        blockPicker = BlockPicker(self.tool.replaceBlockInfo, self.tool.editor.level.materials)
        if blockPicker.present():
            self.replaceBlockButton.blockInfo = self.tool.replaceBlockInfo = blockPicker.blockInfo

    def pickFillBlock(self):
        blockPicker = BlockPicker(self.tool.blockInfo, self.tool.editor.level.materials, allowWildcards=True)
        if blockPicker.present():
            self.tool.blockInfo = blockPicker.blockInfo


class FillToolOptions(ToolOptions):
    def __init__(self, tool):
        ToolOptions.__init__(self, name='Panel.FillToolOptions')
        self.tool = tool
        self.autoChooseCheckBoxFill = CheckBoxLabel("Open Block Picker for Fill",
                                                ref=config.fill.chooseBlockImmediately,
                                                tooltipText="When the fill tool is chosen, prompt for a block type.")
        self.autoChooseCheckBoxReplace = CheckBoxLabel("Open Block Picker for Replace",
                                                       ref=config.fill.chooseBlockImmediatelyReplace,
                                                       tooltipText="When the replace tool is chosen, prompt for a block type.")
        col = Column((Label("Fill and Replace Options"), self.autoChooseCheckBoxFill, self.autoChooseCheckBoxReplace, Button("OK", action=self.dismiss)))

        self.add(col)
        self.shrink_wrap()


class FillTool(EditorTool):
    toolIconName = "fill"
    _blockInfo = pymclevel.alphaMaterials.Stone
    replaceBlockInfo = pymclevel.alphaMaterials.Air
    tooltipText = "Fill and Replace\nRight-click for options"
    replacing = False
    color = (0.75, 1.0, 1.0, 0.7)

    def __init__(self, *args, **kw):
        EditorTool.__init__(self, *args, **kw)
        self.optionsPanel = FillToolOptions(self)
        self.pickBlockKey = 0
        self.root = get_root()
        
    noData = False


    @property
    def blockInfo(self):
        return self._blockInfo

    @blockInfo.setter
    def blockInfo(self, bt):
        self._blockInfo = bt
        if self.panel:
            self.panel.blockButton.blockInfo = bt

    def levelChanged(self):
        pass

    def showPanel(self):
        if self.panel:
            self.panel.parent.remove(self.panel)

        panel = FillToolPanel(self)
        panel.centery = self.editor.centery
        panel.left = self.editor.left
        panel.anchor = "lwh"

        self.panel = panel
        self.editor.add(panel)

    def toolEnabled(self):
        return not (self.selectionBox() is None)

    def toolSelected(self):
        box = self.selectionBox()
        if None is box:
            return

        self.replacing = False
        self.showPanel()

        if self.chooseBlockImmediately:
            blockPicker = BlockPicker(self.blockInfo, self.editor.level.materials, allowWildcards=True)

            if blockPicker.present():
                self.blockInfo = blockPicker.blockInfo
                self.showPanel()

    chooseBlockImmediately = config.fill.chooseBlockImmediately.property()
    chooseBlockImmediatelyReplace = config.fill.chooseBlockImmediatelyReplace.property()

    def toolReselected(self):
        if not self.replacing:
            self.showPanel()
            self.panel.pickFillBlock()

    def cancel(self):
        self.hidePanel()

    @alertException
    def confirm(self):
        box = self.selectionBox()
        if None is box:
            return

        with setWindowCaption("REPLACING - "):
            self.editor.freezeStatus("Replacing %0.1f million blocks" % (float(box.volume) / 1048576.,))

            self.blockInfo = self.panel.blockButton.blockInfo

            if self.replacing:
                self.replaceBlockInfo = self.panel.replaceBlockButton.blockInfo
                if self.blockInfo.wildcard:
                    print "Wildcard replace"
                    blocksToReplace = []
                    for i in range(16):
                        blocksToReplace.append(self.editor.level.materials.blockWithID(self.blockInfo.ID, i))
                else:
                    blocksToReplace = [self.blockInfo]

                op = BlockFillOperation(self.editor, self.editor.level, self.selectionBox(), self.replaceBlockInfo,
                                        blocksToReplace, noData=self.noData)

            else:
                blocksToReplace = []
                op = BlockFillOperation(self.editor, self.editor.level, self.selectionBox(), self.blockInfo,
                                        blocksToReplace)

        self.editor.addOperation(op)

        self.editor.addUnsavedEdit()
        self.editor.invalidateBox(box)
        self.editor.toolbar.selectTool(-1)

    def roll(self, amount=1, blocksOnly=False):
        if blocksOnly:
            id = [self._blockInfo.ID]
            data = [self._blockInfo.blockData]
            Roll(id,data)
            self.blockInfo = self.editor.level.materials[(id[0], data[0])]
        else:
            self.toggleReplacing()

    def mirror(self, amount=1, blocksOnly=False):
        if blocksOnly:
            id = [self._blockInfo.ID]
            data = [self._blockInfo.blockData]
            yaw = int(self.editor.mainViewport.yaw) % 360
            if (45 <= yaw < 135) or (225 < yaw <= 315):
                FlipEastWest(id,data)
            else:
                FlipNorthSouth(id,data)
            self.blockInfo = self.editor.level.materials[(id[0], data[0])]

    def flip(self, amount=1, blocksOnly=False):
        if blocksOnly:
            id = [self._blockInfo.ID]
            data = [self._blockInfo.blockData]
            FlipVertical(id,data)
            self.blockInfo = self.editor.level.materials[(id[0], data[0])]

    def rotate(self, amount=1, blocksOnly=False):
        if blocksOnly:
            id = [self._blockInfo.ID]
            data = [self._blockInfo.blockData]
            RotateLeft(id,data)
            self.blockInfo = self.editor.level.materials[(id[0], data[0])]

    def toggleReplacing(self):
        self.replacing = not self.replacing

        self.hidePanel()
        self.showPanel()
        if self.replacing and self.chooseBlockImmediatelyReplace:
            self.panel.pickReplaceBlock()

    def openReplace(self):
        if not self.replacing:
            self.replacing = True
            self.hidePanel()
            self.showPanel()
            if self.chooseBlockImmediatelyReplace:
                self.panel.pickReplaceBlock()
        else:
            self.panel.pickReplaceBlock()

    @alertException
    def swap(self):
        if self.panel and self.replacing:
            self.panel.swapBlockTypes()

    def blockTexFunc(self, terrainTexture, tex):
        def _func():
            s, t = tex
            if not hasattr(terrainTexture, "data"):
                return
            w, h = terrainTexture.data.shape[:2]
            pixelWidth = 512 if self.editor.level.materials.name in ("Pocket", "Alpha") else 256
            s = s * w / pixelWidth
            t = t * h / pixelWidth
            texData = numpy.array(terrainTexture.data[t:t + h / 32, s:s + w / 32])
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w / 32, h / 32, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
                            texData)

        return _func

    def drawToolReticle(self):
        if self.pickBlockKey == 1:
            # eyedropper mode
            self.editor.drawWireCubeReticle(color=(0.2, 0.6, 0.9, 1.0))

    def drawToolMarkers(self):
        if self.editor.currentTool != self:
            return

        if self.panel and self.replacing:
            blockInfo = self.replaceBlockInfo
        else:
            blockInfo = self.blockInfo

        color = 1.0, 1.0, 1.0, 0.35
        if blockInfo:
            terrainTexture = self.editor.level.materials.terrainTexture
            tex = self.editor.level.materials.blockTextures[blockInfo.ID, blockInfo.blockData, 0]  # xxx
            tex = Texture(self.blockTexFunc(terrainTexture, tex))

            # color = (1.5 - alpha, 1.0, 1.5 - alpha, alpha - 0.35)
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glPushMatrix()
            GL.glScale(16., 16., 16.)

        else:
            tex = None
            # color = (1.0, 0.3, 0.3, alpha - 0.35)

        GL.glPolygonOffset(DepthOffset.FillMarkers, DepthOffset.FillMarkers)
        self.editor.drawConstructionCube(self.selectionBox(),
                                         color,
                                         texture=tex)

        if blockInfo:
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glPopMatrix()

    @property
    def statusText(self):
        return _("Press {hotkey} to choose a block. Press {R} to enter replace mode. Click Fill or press Enter to confirm.").format(
            hotkey=self.hotkey, R=config.keys.replaceShortcut.get())

    @property
    def worldTooltipText(self):
        if self.pickBlockKey == 1:
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return _("Click to use {0} ({1}:{2})").format(
                    self.editor.level.materials.blockWithID(blockID, blockdata).name, blockID, blockdata)

            except Exception, e:
                return repr(e)

    def mouseUp(self, *args):
        return self.editor.selectionTool.mouseUp(*args)

    @alertException
    def mouseDown(self, evt, pos, dir):
        if self.pickBlockKey == 1:
            id = self.editor.level.blockAt(*pos)
            data = self.editor.level.blockDataAt(*pos)

            self.blockInfo = self.editor.level.materials.blockWithID(id, data)
        else:
            return self.editor.selectionTool.mouseDown(evt, pos, dir)

    def keyDown(self, evt):
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        if keyname == config.keys.pickBlock.get():
            self.pickBlockKey = 1

    def keyUp(self, evt):
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        if keyname == config.keys.pickBlock.get():
            self.pickBlockKey = 0
