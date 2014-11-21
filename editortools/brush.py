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

#Modified by D.C.-G. for translation purposes
import imp
import traceback
from OpenGL import GL
from albow import AttrRef, ItemRef, Button, ValueDisplay, Row, Label, ValueButton, Column, IntField, FloatField, alert, CheckBox, TextField, TableView, TableColumn
from albow.dialogs import Dialog
from albow.translate import _
import ast
import bresenham
from clone import CloneTool
import collections
import config
import directories
from editortools.blockpicker import BlockPicker
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from editortools.tooloptions import ToolOptions
from glbackground import Panel, GLBackground
from glutils import gl
import itertools
import keys
import leveleditor
import logging
from mceutils import ChoiceButton, CheckBoxLabel, showProgress, IntInputRow, FloatInputRow, alertException, drawTerrainCuttingWire
import mcplatform
from numpy import newaxis
import numpy
from operation import Operation, mkundotemp
import os
import sys
from os.path import basename
from pymclevel import block_fill, BoundingBox, materials, blockrotation
import pymclevel
from pymclevel.level import extractHeights
from pymclevel.mclevelbase import exhaust
import random
from __builtin__ import __import__


log = logging.getLogger(__name__)

class BrushMode(object):
    options = []

    def brushBoxForPointAndOptions(self, point, options={}):
        # Return a box of size options['brushSize'] centered around point.
        # also used to position the preview reticle
        size = options['brushSize']
        origin = map(lambda x, s: x - (s >> 1), point, size)
        return BoundingBox(origin, size)

    def apply(self, op, point):
        """
        Called by BrushOperation for brush modes that can't be implemented using applyToChunk
        """
        pass
    apply = NotImplemented

    def applyToChunk(self, op, chunk, point):
        """
        Called by BrushOperation to apply this brush mode to the given chunk with a brush centered on point.
        Default implementation will compute:
          brushBox: a BoundingBox for the world area affected by this brush,
          brushBoxThisChunk: a box for the portion of this chunk affected by this brush,
          slices: a tuple of slices that can index the chunk's Blocks array to select the affected area.

        These three parameters are passed to applyToChunkSlices along with the chunk and the brush operation.
        Brush modes must implement either applyToChunk or applyToChunkSlices
        """
        brushBox = self.brushBoxForPointAndOptions(point, op.options)

        brushBoxThisChunk, slices = chunk.getChunkSlicesForBox(brushBox)
        if brushBoxThisChunk.volume == 0: return

        return self.applyToChunkSlices(op, chunk, slices, brushBox, brushBoxThisChunk)

    def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
        raise NotImplementedError

    def createOptions(self, panel, tool):
        pass

class BrushOperation(Operation):
    def __init__(self, tool):
        super(BrushOperation, self).__init__(tool.editor, tool.level)
        self.tool = tool
        self.editor = tool.editor
        if isinstance(points[0], (int, float)):
            points = [points]
        self.points = points
  
        if max(self.brushSize) > BrushTool.maxBrushSize:
            self.brushSize = (BrushTool.maxBrushSize,) * 3
        if max(self.brushSize) < 1:
            self.brushSize = (1, 1, 1)
  
        boxes = [self.tool.getDirtyBox(p, options) for p in points]
        self._dirtyBox = reduce(lambda a, b: a.union(b), boxes)
    
    def dirtyBox(self):
        return self._dirtyBox

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self._dirtyBox)

        def _perform():
            yield 0, len(self.points), _("Applying {0} brush...").format(self.brushMode.name)
            if self.brushMode.apply is not NotImplemented: #xxx double negative
                for i, point in enumerate(self.points):
                    f = self.brushMode.apply(self, point)
                    if hasattr(f, "__iter__"):
                        for progress in f:
                            yield progress
                    else:
                        yield i, len(self.points), _("Applying {0} brush...").format(self.brushMode.name)
            else:

                for j, cPos in enumerate(self._dirtyBox.chunkPositions):
                    if not self.level.containsChunk(*cPos):
                        continue
                    chunk = self.level.getChunk(*cPos)
                    for i, point in enumerate(self.points):

                        f = self.brushMode.applyToChunk(self, chunk, point)

                        if hasattr(f, "__iter__"):
                            for progress in f:
                                yield progress
                        else:
                            yield j * len(self.points) + i, len(self.points) * self._dirtyBox.chunkCount, _("Applying {0} brush...").format(self.brushMode.name)

                    chunk.chunkChanged()

        if len(self.points) > 10:
            showProgress("Performing brush...", _perform(), cancel=True)
        else:
            exhaust(_perform())

        self.editor.get_root().ctrlClicked = -1



class BrushPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self)
        self.tool = tool
        """
        presets, modeRow and styleRow are always created, no matter
        what brush is selected. styleRow can be disabled by putting disableStyleButton = True
        in the brush file.
        """
        presets = self.createPresetRow()
        
        self.brushModeButtonLabel = Label("Mode:")
        self.brushModeButton = ChoiceButton([mode for mode in tool.brushModes],
                                       width=150,
                                       choose=self.brushModeChanged)
        modeRow = Row([self.brushModeButtonLabel, self.brushModeButton])   
             
        self.brushStyleButtonLabel = Label("Style:")
        self.brushStyleButton = ValueButton(ref=ItemRef(self.tool.options, "Style"),
                                            action=self.tool.swapBrushStyles,
                                            width=150)
        
        styleRow = Row([self.brushStyleButtonLabel, self.brushStyleButton])
        self.brushModeButton.selectedChoice = self.tool.selectedBrushMode
        optionsColumn = []
        optionsColumn.extend([presets, modeRow])
        if not getattr(tool.brushMode, 'disableStyleButton', False):
            optionsColumn.append(styleRow)
        """
        We're going over all options in the selected brush module, and making
        a field for all of them.
        """
        for r in tool.brushMode.inputs:
            row = []
            for key, value in r.iteritems():
                field = self.createField(key, value)
                row.append(field)
            row = Row(row)
            optionsColumn.append(row)
        optionsColumn = Column(optionsColumn)
        self.add(optionsColumn)
        self.shrink_wrap()
        
    def createField(self, key, value): #Creates a field matching the input type
        type = value.__class__.__name__
        reference = ItemRef(self.tool.options, key)
        if type == 'int':
            object = IntInputRow(key, ref=reference, width=50)
        elif type == 'float':
            object = FloatInputRow(key, ref=reference, width=50)
        elif type == 'bool':
            object = CheckBoxLabel(key, ref=reference)
        elif type == 'Block':
            if not hasattr(self.tool.recentBlocks, key):
                self.tool.recentBlocks[key] = []
            object = BlockButton(self.tool.editor.level.materials,
                                 ref=reference,
                                 recentBlocks = self.tool.recentBlocks[key],
                                 allowWildcards = True
                                 )
        return object
    
    def brushModeChanged(self):
        self.tool.selectedBrushMode = self.brushModeButton.selectedChoice
        self.tool.brushMode = self.tool.brushModes[selectedBrushMode]
    
    def createPresetRow(self): #Creates the brush preset row, called by BrushPanel when creating the panel
        """
        Currently doesn't do anything yet, just a placeholder to create the widget
        """
        self.presets = ["Load Preset:"]
        #self.presets.extend(self.getBrushFileList())
        #self.presets.append('Remove Presets')
        
        self.presetListButton = ChoiceButton(self.presets, width=100, choose=None)
        self.presetListButton.selectedChoice = "Load Preset:"
        self.saveButton = Button("Save as preset", action=None)
        
        presetListButtonRow = Row([self.presetListButton])
        saveButtonRow = Row([self.saveButton])
        row = Row([presetListButtonRow, saveButtonRow])
        widget = GLBackground()
        widget.bg_color = (0.8, 0.8, 0.8, 0.8)
        widget.add(row)
        widget.shrink_wrap()
        widget.anchor = "whtr"
        return widget

        
        
        
class BrushToolOptions(ToolOptions):
    def __init__(self, tool):
        Panel.__init__(self)
        alphaField = FloatField(ref=ItemRef(tool.settings, 'brushAlpha'), min=0.0, max=1.0, width=60)
        alphaField.increment = 0.1
        alphaRow = Row((Label("Alpha: "), alphaField))
        autoChooseCheckBox = CheckBoxLabel("Choose Block Immediately",
                                            ref=ItemRef(tool.settings, "chooseBlockImmediately"),
                                            tooltipText="When the brush tool is chosen, prompt for a block type.")

        updateOffsetCheckBox = CheckBoxLabel("Reset Distance When Brush Size Changes",
                                            ref=ItemRef(tool.settings, "updateBrushOffset"),
                                            tooltipText="Whenever the brush size changes, reset the distance to the brush blocks.")

        col = Column((Label("Brush Options"), alphaRow, autoChooseCheckBox, updateOffsetCheckBox, Button("OK", action=self.dismiss)))
        self.add(col)
        self.shrink_wrap()
        return
    
class BrushTool(CloneTool):
    tooltipText = "Brush\nRight-click for options"
    toolIconName = "brush"
    
    options = {
    'Style':'Round',
    }
    settings = {
    'chooseBlockImmediately':False,
    'updateBrushOffset':False,
    'brushAlpha':1.0,      
    }
    brushModes = {}
    recentBlocks = {}
    

    def __init__(self, *args):
        """
        Called on starting mcedit.
        Creates some basic variables.
        """
        CloneTool.__init__(self, *args)
        self.optionsPanel = BrushToolOptions(self)
        self.recentFillBlocks = []
        self.recentReplaceBlocks = []
        self.draggedPositions = []
        self.pickBlockKey = False
        self.lineToolKey = False
        
        
    """
    Property reticleOffset.
    Used to determine the distance between the block the cursor is pointing at, and the center of the brush.
    Increased by scrolling up, decreased by scrolling down (default keys)
    """
    _reticleOffset = 1
    @property
    def reticleOffset(self):
        if getattr(self.brushMode, 'draggableBrush', True):
            return self._reticleOffset
        return 0
    @reticleOffset.setter
    def reticleOffset(self, val):
        self._reticleOffset = val

        
    def toolEnabled(self):
        """
        Brush tool is always enabled on the toolbar.
        It does not need a selection.
        """
        return True
    
    def setupBrushModes(self):
        """
        Makes a dictionary of all mode names and their corresponding module. If no name is found, it uses the name of the file.
        Creates dictionary entries for all inputs in import brush modules.
        Called by toolSelected
        """
        self.importedBrushModes = self.importBrushModes()
        for m in self.importedBrushModes:
            if m.displayName:
                self.brushModes[m.displayName] = m
            else:
                self.brushModes[m.__name__] = m
            if m.inputs:
                for r in m.inputs:
                    for key in r:
                        if not hasattr(self.options, key):
                            self.options[key] = r[key]

    def importBrushModes(self):
        """
        Imports all Brush Modes from their files.
        Called by setupBrushModes
        """
        sys.path.append(directories.brushesDir)
        modes = (self.tryImport(x[:-3]) for x in filter(lambda x: x.endswith(".py"), os.listdir(directories.brushesDir)))
        modes = filter(lambda m: (hasattr(m, "apply") or hasattr(m, 'applyToChunkSlices')) and hasattr(m, 'inputs'), modes)
        return modes
    
    def tryImport(self, name):
        """
        Imports a brush module. Called by importBrushModules
        :param name, name of the module to import. 
        """
        try:
            globals()[name] = m = imp.load_source(name, os.path.join(directories.brushesDir, (name+ ".py")))
            m.materials = self.editor.level.materials
            m.createInputs(m)
            return m
        except Exception, e:
            print traceback.format_exc()
            alert(_(u"Exception while importing brush mode {}. See console for details.\n\n{}").format(name, e))
            return object()

        
    def toolSelected(self):
        """
        Applies options of BrushToolOptions.
        It then imports all brush modes from their files,
        sets up the panel,
        and sets up the brush preview.
        Called on pressing "2" or pressing the brush button in the hotbar when brush is not selected.
        """
        self.setupBrushModes()
        self.selectedBrushMode = [m for m in self.brushModes][0]
        self.brushMode = self.brushModes[self.selectedBrushMode]
        if self.settings['chooseBlockImmediately']:
            key = getattr(self.brushMode, 'mainBlock', 'Block')
            blockPicker = BlockPicker(self.options[key], self.editor.level.materials, allowWildcards=True)
            if blockPicker.present():
                    self.options[key] = blockPicker.blockInfo
        if self.settings['updateBrushOffset']:
            self.reticleOffset = self.offsetMax()
        self.resetToolDistance()
        self.setupPreview()
        self.showPanel()
        
    @property
    def worldTooltipText(self):
        """
        Displays the corresponding tooltip if ALT is pressed.
        Called by leveleditor every tick.
        """
        if self.pickBlockKey == True:
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return _("Click to use {0} ({1}:{2})").format(self.editor.level.materials.names[blockID][blockdata], blockID, blockdata)
            except Exception, e:
                return repr(e)

        
    def keyDown(self, evt):
        """
        Triggered on pressing a key,
        sets the corresponding variable to True
        """
        keyname = evt.dict.get('keyname', None) or keys.getKey(evt)
        if keyname == config.config.get('Keys', 'Pick Block'):
            self.pickBlockKey = True
        if keyname == config.config.get("Keys", "Brush Line Tool"):
            self.lineToolKey = True

    def keyUp(self, evt):
        """
        Triggered on releasing a key,
        sets the corresponding variable to False
        """
        keyname = evt.dict.get('keyname', None) or keys.getKey(evt)
        if keyname == config.config.get('Keys', 'Pick Block'):
            self.pickBlockKey = False
        if keyname == config.config.get("Keys", "Brush Line Tool"):
            self.lineToolKey = False
            self.lastPosition = None
            
    @alertException
    def mouseDown(self, evt, pos, direction):
        """
        Called on pressing the mouseButton.
        Sets bllockButton if pickBlock is True.
        Also starts dragging.
        """
        if self.pickBlockKey == True:
            id = self.editor.level.blockAt(*pos)
            data = self.editor.level.blockDataAt(*pos)
            key = getattr(self.brushMode, 'MainBlock', 'Block')
            self.options[key] = self.editor.level.materials.blockWithID(id, data)
            self.showPanel()
        else:
            self.draggedDirection = direction
            point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
            self.dragLineToPoint(point)

    @alertException
    def mouseDrag(self, evt, pos, _dir):
        """
        Called on dragging the mouse.
        Adds the current point to draggedPositions.
        """
        direction = self.draggedDirection
        if self.brushMode.name != "Flood Fill":
            if len(self.draggedPositions):  # if self.isDragging
                self.lastPosition = lastPoint = self.draggedPositions[-1]
                point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
                if any([abs(a - b) >= self.minimumSpacing
                        for a, b in zip(point, lastPoint)]):
                    self.dragLineToPoint(point)
    
        def dragLineToPoint(self, point):
            if self.brushMode.name == "Flood Fill":
                self.draggedPositions = [point]
                return
    
            if self.lineToolKey == True:
                for move in self.editor.movements:
                    if move in config.config.get("Keys", "Brush Line Tool"):
                        self.editor.save = 1
                self.editor.get_root().shiftClicked = 0
                self.editor.get_root().shiftPlaced = -2
                self.editor.get_root().ctrlClicked = 0
                self.editor.get_root().ctrlPlaced = -2
                self.editor.get_root().altClicked = 0
                self.editor.get_root().altPlaced = -2
    
                if len(self.draggedPositions):
                    points = bresenham.bresenham(self.draggedPositions[-1], point)
                    self.draggedPositions.extend(points[::self.minimumSpacing][1:])
                elif self.lastPosition is not None:
                    points = bresenham.bresenham(self.lastPosition, point)
                    self.draggedPositions.extend(points[::self.minimumSpacing][1:])
            else:
                self.draggedPositions.append(point)

    @alertException
    def mouseUp(self, evt, pos, direction):
        """
        Called on releasing the Mouse Button.
        Creates Operation object and passes it to the leveleditor.
        """
        self.editor.get_root().ctrlClicked = -1
        if 0 == len(self.draggedPositions):
            return
        size = self.getBrushSize()
        op = BrushOperation(self.editor,
                            self.editor.level,
                            self.draggedPositions,
                            self.getBrushOptions())
        box = op.dirtyBox()
        self.editor.addOperation(op)
        self.editor.addUnsavedEdit()

        self.editor.invalidateBox(box)
        self.lastPosition = self.draggedPositions[-1]

        self.draggedPositions = []

        if self.lineToolKey == True:
            self.editor.get_root().shiftClicked = 0
            self.editor.get_root().shiftPlaced = -2
            self.editor.get_root().ctrlClicked = 0
            self.editor.get_root().ctrlPlaced = -2
            self.editor.get_root().altClicked = 0
            self.editor.get_root().altPlaced = -2
            self.lineToolKey = False
        self.editor.get_root().ctrlClicked = -1

    def swapBrushStyles(self):
        """
        Swaps the BrushStyleButton to the next Brush Style.
        Called by pressing BrushStyleButton in panel.
        """
        styles = ["Square","Round","Diamond"]
        brushStyleIndex = styles.index(self.options["Style"]) + 1
        brushStyleIndex %= 3
        self.options["Style"] = styles[brushStyleIndex]
        self.setupPreview()
    
    def showPanel(self):
        """
        Removes old panels.
        Makes new panel instance and add it to leveleditor.
        """
        if self.panel:
            self.panel.parent.remove(self.panel)
        panel = BrushPanel(self)
        panel.centery = self.editor.centery
        panel.left = self.editor.left
        panel.anchor = "lwh"
        self.panel = panel
        self.editor.add(panel)

    def offsetMax(self):
        """
        Sets the Brush Offset (space between face the cursor is pointing at and center of brush.
        Called by toolSelected if updateBrushOffset is Checked in BrushOptions
        """
        brushSizeOffset = max(self.getBrushSize + 1)
        return max(1, (0.5 * brushSizeOffset))
                   
    def resetToolDistance(self):
        """
        Resets the distance of the brush in right-click mode, appropriate to the size of the brush.
        """
        distance = max(self.editor.cameraToolDistance, 6 + max(self.getBrushSize()) * 1.25)
        self.editor.cameraToolDistance = distance
        
    def getBrushSize(self):
        """
        Returns an array of the sizes of the brush.
        Called by methods that need the size of the brush like createBrushMask
        """ 
        size = []
        for dim in ['W','H','L']:
            size.append(self.options[dim])
        return size
    
    @alertException 
    def setupPreview(self): 
        """
        Creates the Brush Preview
        Passes it as a FakeLevel object to the renderer
        Called whenever the preview needs to be recalculated
        """
        self.previewDirty = False
        brushSize = self.getBrushSize()
        brushStyle = self.options['Style']
        key = getattr(self.brushMode, 'mainBlock', 'Block')
        blockInfo = self.options[key]

        class FakeLevel(pymclevel.MCLevel):
            filename = "Fake Level"
            materials = self.editor.level.materials

            def __init__(self):
                self.chunkCache = {}

            Width, Height, Length = brushSize
            zerolight = numpy.zeros((16, 16, Height), dtype='uint8')
            zerolight[:] = 15

            def getChunk(self, cx, cz):
                if (cx, cz) in self.chunkCache:
                    return self.chunkCache[cx, cz]

                class FakeBrushChunk(pymclevel.level.FakeChunk):
                    Entities = []
                    TileEntities = []

                f = FakeBrushChunk()
                f.world = self
                f.chunkPosition = (cx, cz)

                mask = createBrushMask(self.getBrushSize(), self.options['Style'], (0, 0, 0), BoundingBox((cx << 4, 0, cz << 4), (16, self.Height, 16)))
                f.Blocks = numpy.zeros(mask.shape, dtype='uint8')
                f.Data = numpy.zeros(mask.shape, dtype='uint8')

                if blockInfo.ID:
                    f.Blocks[mask] = blockInfo.ID
                    f.Data[mask] = blockInfo.blockData

                else:
                    f.Blocks[mask] = 255
                self.chunkCache[cx, cz] = f
                return f

        self.level = FakeLevel()
        CloneTool.setupPreview(self, alpha=self.settings['brushAlpha'])
        
    def getReticlePoint(self, pos, direction):
        """
        Calculates the position of the reticle.
        Called by drawTerrainReticle.
        """
        if len(self.draggedPositions):
            direction = self.draggedDirection
        return map(lambda a, b: a + (b * self.reticleOffset), pos, direction)
    
    def drawToolReticle(self):
        """
        Draws a yellow reticle at every position where you dragged the brush.
        Called by leveleditor.render
        """
        for pos in self.draggedPositions:
            drawTerrainCuttingWire(BoundingBox(pos, (1, 1, 1)),
                                   (0.75, 0.75, 0.1, 0.4),
                                   (1.0, 1.0, 0.5, 1.0))
            
    def getDirtyBox(self, point, size):
        """
        Returns a box around the Brush given point and size of the brush.
        """
        if hasattr(self.brushMode, 'createDirtyBox'):
            dirtyBox = self.brushMode.createDirtyBox(point, size)
        else:
            origin = map(lambda x, s: x - (s >> 1), point, size)
            dirtyBox = BoundingBox(origin, size)
        return dirtyBox
        
    def drawTerrainReticle(self):
        """
        Draws the white reticle where the cursor is pointing.
        Called by leveleditor.render
        """
        if self.pickBlockKey == 1: #Alt is pressed
            self.editor.drawWireCubeReticle(color=(0.2, 0.6, 0.9, 1.0))
        else:
            pos, direction = self.editor.blockFaceUnderCursor
            reticlePoint = self.getReticlePoint(pos, direction)

            self.editor.drawWireCubeReticle(position=reticlePoint)
            if reticlePoint != pos:
                GL.glColor4f(1.0, 1.0, 0.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))  #Center of reticle block
                    GL.glVertex3f(*map(lambda a, b: a + 0.5 + b * 0.5, pos, direction))  #Top side of surface block

            if self.previewDirty:
                self.setupPreview()
            dirtyBox = self.getDirtyBox(reticlePoint, self.getBrushSize())
            self.drawTerrainPreview(dirtyBox.origin)
            if self.lineToolKey == True and self.lastPosition and getattr(self.brushMode, 'draggableBrush', True): #If dragging mouse with Linetool pressed.
                GL.glColor4f(1.0, 1.0, 1.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, self.lastPosition))
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))


    def createBrushMask(shape, style="Round", offset=(0, 0, 0), box=None, chance=100, hollow=False):
        """
        Return a boolean array for a brush with the given shape and style.
        If 'offset' and 'box' are given, then the brush is offset into the world
        and only the part of the world contained in box is returned as an array.
        :param shape, UNKWOWN
        :keyword style, style of the brush. Round if not given.
        :keyword offset, UNKWOWN
        :keyword box, UNKWOWN
        :keyword chance, also known as Noise. Input in stock-brushes like Fill and Replace.
        :keyword hollow, input to calculate a hollow brush.
        """
    
        #We are returning indices for a Blocks array, so swap axes
        if box is None:
            box = BoundingBox(offset, shape)
        if chance < 100 or hollow:
            box = box.expand(1)
    
        outputShape = box.size
        outputShape = (outputShape[0], outputShape[2], outputShape[1])
    
        shape = shape[0], shape[2], shape[1]
        offset = numpy.array(offset) - numpy.array(box.origin)
        offset = offset[[0, 2, 1]]
    
        inds = numpy.indices(outputShape, dtype=float)
        halfshape = numpy.array([(i >> 1) - ((i & 1 == 0) and 0.5 or 0) for i in shape])
    
        blockCenters = inds - halfshape[:, newaxis, newaxis, newaxis]
        blockCenters -= offset[:, newaxis, newaxis, newaxis]
    
        # odd diameter means measure from the center of the block at 0,0,0 to each block center
        # even diameter means measure from the 0,0,0 grid point to each block center
    
        # if diameter & 1 == 0: blockCenters += 0.5
        shape = numpy.array(shape, dtype='float32')
    
        # if not isSphere(shape):
        if style == "Round":
            blockCenters *= blockCenters
            shape /= 2
            shape *= shape
    
            blockCenters /= shape[:, newaxis, newaxis, newaxis]
            distances = sum(blockCenters, 0)
            mask = distances < 1
        elif style == "Cylinder":
            pass
    
    
        elif style == "Square":
            # mask = ones(outputShape, dtype=bool)
            # mask = blockCenters[:, newaxis, newaxis, newaxis] < shape
            blockCenters /= shape[:, None, None, None]
    
            distances = numpy.absolute(blockCenters).max(0)
            mask = distances < .5
    
        elif style == "Diamond":
            blockCenters = numpy.abs(blockCenters)
            shape /= 2
            blockCenters /= shape[:, newaxis, newaxis, newaxis]
            distances = sum(blockCenters, 0)
            mask = distances < 1
        else:
            raise ValueError, "Unknown style: " + style
    
        if (chance < 100 or hollow) and max(shape) > 1:
            threshold = chance / 100.0
            exposedBlockMask = numpy.ones(shape=outputShape, dtype='bool')
            exposedBlockMask[:] = mask
            submask = mask[1:-1, 1:-1, 1:-1]
            exposedBlockSubMask = exposedBlockMask[1:-1, 1:-1, 1:-1]
            exposedBlockSubMask[:] = False
    
            for dim in (0, 1, 2):
                slices = [slice(1, -1), slice(1, -1), slice(1, -1)]
                slices[dim] = slice(None, -2)
                exposedBlockSubMask |= (submask & (mask[slices] != submask))
                slices[dim] = slice(2, None)
                exposedBlockSubMask |= (submask & (mask[slices] != submask))
    
            if hollow:
                mask[~exposedBlockMask] = False
            if chance < 100:
                rmask = numpy.random.random(mask.shape) < threshold
    
                mask[exposedBlockMask] = rmask[exposedBlockMask]
    
        if chance < 100 or hollow:
            return mask[1:-1, 1:-1, 1:-1]
        else:
            return mask
        
        
