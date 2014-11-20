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

# class BrushOperation(Operation):
#     def __init__(self, editor, level, points, options):
#         super(BrushOperation, self).__init__(editor, level)
#  
#         # if options is None: options = {}
#  
#         self.options = options
#         self.editor = editor
#         if isinstance(points[0], (int, float)):
#             points = [points]
#  
#         self.points = points
#  
#         self.brushSize = options['brushSize']
#         self.blockInfo = options['blockInfo']
#         self.brushStyle = options['brushStyle']
#         self.brushMode = options['brushMode']
#  
#         if max(self.brushSize) > BrushTool.maxBrushSize:
#             self.brushSize = (BrushTool.maxBrushSize,) * 3
#         if max(self.brushSize) < 1:
#             self.brushSize = (1, 1, 1)
#  
#         boxes = [self.brushMode.brushBoxForPointAndOptions(p, options) for p in points]
#         self._dirtyBox = reduce(lambda a, b: a.union(b), boxes)
#  
#     brushStyles = ["Round", "Square", "Diamond"]
#     brushModeClasses = [
#         Modes.Fill,
#         Modes.VariedFill,
#         Modes.FloodFill,
#         Modes.Replace,
# 		Modes.Vary,
#         Modes.Erode,
#         Modes.Topsoil,
#         Modes.Paste
#     ]


    @property
    def noise(self):
        return self.options.get('brushNoise', 100)

    @property
    def hollow(self):
        return self.options.get('brushHollow', False)
    
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
        presets = self.createPresetRow()
        self.brushModeButton = ChoiceButton([m for m in tool.brushModes],
                                       width=150,
                                       choose=self.brushModeChanged)
        self.brushModeButton.selectedChoice = self.tool.selectedBrushMode
        optionsColumn = []
        optionsColumn.extend([presets, self.brushModeButton])
        m = tool.brushModes[self.tool.selectedBrushMode]
        for r in m.inputs:
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
                                 ref = reference,
                                 recentBlocks = self.tool.recentBlocks[key],
                                 allowWildcards = True
                                 )
        return object
    
    def brushModeChanged(self):
        self.tool.selectedBrushMode = self.brushModeButton.selectedChoice
    
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
    
    options = {}
    settings = {
    'chooseBlockImmediately':False,
    'updateBrushOffset':False            
    }
    brushModes = {}
    recentBlocks = {}

    def __init__(self, *args):
        CloneTool.__init__(self, *args)
        self.optionsPanel = BrushToolOptions(self)
        self.recentFillBlocks = []
        self.recentReplaceBlocks = []
        self.draggedPositions = []
        self.useKey = 0
        self.brushLineKey = 0
    
    def setupBrushModes(self):
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
        sys.path.append(directories.brushesDir)
        modes = (self.tryImport(x[:-3]) for x in filter(lambda x: x.endswith(".py"), os.listdir(directories.brushesDir)))
        modes = filter(lambda m: (hasattr(m, "apply") or hasattr(m, 'applyToChunkSlices')) and hasattr(m, 'inputs'), modes)
        return modes
    
    def tryImport(self, name):
        try:
            globals()[name] = m = imp.load_source(name, os.path.join(directories.brushesDir, (name+ ".py")))
            m.materials = self.editor.level.materials
            m.createInputs(m)
            return m
        except Exception, e:
            print traceback.format_exc()
            alert(_(u"Exception while importing brush mode {}. See console for details.\n\n{}").format(name, e))
            return object()

        
    def toolSelected(self): #Called on selecting tool. Applies options of BrushToolOptions, then sets up panel and other stuff.
        if self.settings['chooseBlockImmediately']:
            blockPicker = BlockPicker(self.options['blockInfo'], self.editor.level.materials, allowWildcards=True)
            if blockPicker.present():
                self.options['blockInfo'] = blockPicker.blockInfo
        if self.settings['updateBrushOffset']:
            self.options['reticleOffset'] = self.offsetMax()
        self.setupBrushModes()
        self.selectedBrushMode = [m for m in self.brushModes][0]
        #self.resetToolDistance()
        #self.setupPreview()
        self.showPanel()
        
    
    def showPanel(self): #Remove old panels, make new panel instance and add it to leveleditor.
        if self.panel:
            self.panel.parent.remove(self.panel)
        panel = BrushPanel(self)
        panel.centery = self.editor.centery
        panel.left = self.editor.left
        panel.anchor = "lwh"
        self.panel = panel
        self.editor.add(panel)

    def offsetMax(self): #Sets the offset to match the Brush Size
        brushSizeOffset = max(self.getBrushSize + 1)
        return max(1, (0.5 * brushSizeOffset))
                   
    def resetToolDistance(self): #'Undocumented, no idea what it does' - Rubisk
        distance = max(self.editor.cameraToolDistance, 6 + max(self.getBrushSize()) * 1.25)
        self.editor.cameraToolDistance = distance
        
    def getBrushSize(self): #Used to calculate brush size out of 3 integer values of W, H, L 
        size = []
        for dim in ['W','H','L']:
            size.append(self.options[dim])
        return size
    
    @alertException 
    def setupPreview(self): #Creates the Brush Preview (Still needs better documentation).
        brushSize = self.getBrushSize()
        brushStyle = self.options['brushStyle']
        blockInfo = self.options['blockInfo']

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

                mask = createBrushMask(brushSize, brushStyle, (0, 0, 0), BoundingBox((cx << 4, 0, cz << 4), (16, self.Height, 16)))
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
        CloneTool.setupPreview(self, alpha=self.settings[brushAlpha])

