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

from OpenGL import GL
from OpenGL.arrays import numbers
from albow import AttrRef, Button, ValueDisplay, Row, Label, ValueButton, Column, IntField, CheckBox, FloatField, alert, Field
from albow.translate import tr
import ast
import bresenham
from clone import CloneTool
import collections
import config
import config
from editortools.blockpicker import BlockPicker
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from editortools.tooloptions import ToolOptions
from glbackground import Panel, GLBackground
from glutils import gl
import itertools
import leveleditor
import logging
from mceutils import ChoiceButton, CheckBoxLabel, showProgress, IntInputRow, alertException, drawTerrainCuttingWire
import mceutils
import mcplatform
from numpy import newaxis
import numpy
from operation import Operation, mkundotemp
import os
from os.path import basename
import pygame
from pymclevel import block_fill, BoundingBox, materials, blockrotation
import pymclevel
from pymclevel.level import extractHeights
from pymclevel.mclevelbase import exhaust
import random
import tempfile
import keys

#intialize currentNumber for brushpresets.
global currentNumber
currentNumber = -1
log = logging.getLogger(__name__)


BrushSettings = config.Settings("Brush")
BrushSettings.brushSizeL = BrushSettings("Brush Shape L", 3)
BrushSettings.brushSizeH = BrushSettings("Brush Shape H", 3)
BrushSettings.brushSizeW = BrushSettings("Brush Shape W", 3)
BrushSettings.updateBrushOffset = BrushSettings("Update Brush Offset", False)
BrushSettings.chooseBlockImmediately = BrushSettings("Choose Block Immediately", False)
BrushSettings.alpha = BrushSettings("Alpha", 0.66)

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


class Modes:
    class Fill(BrushMode):

        name = "Fill"
        options =['airFill']

        def createOptions(self, panel, tool):

            airFill = CheckBoxLabel("Fill Air", ref=AttrRef(tool, 'airFill'))

            col = [
                panel.brushPresetOptions,
                panel.modeStyleGrid,
                panel.noiseInput,
                panel.brushSizeRows,
                panel.blockButton,
                airFill,
            ]
            return col

        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.brushStyleMod)


            blocks = chunk.Blocks[slices]
            data = chunk.Data[slices]

            airFill = op.options['airFill']

            if airFill == False:
                airtable = numpy.zeros((materials.id_limit, 16), dtype='bool')
                airtable[0] = True
                replaceMaskAir = airtable[blocks, data]
                brushMask &= ~replaceMaskAir


            chunk.Blocks[slices][brushMask] = op.blockInfo.ID
            chunk.Data[slices][brushMask] = op.blockInfo.blockData

    class VariedFill(BrushMode):

        name = "Varied Fill"
        options =['airFill','chanceA','chanceB','chanceC','chanceD']

        def createOptions(self, panel, tool):

            airFill = CheckBoxLabel("Fill Air", ref=AttrRef(tool, 'airFill'))


            seperator = Label("---")
            
            chanceA = IntInputRow("Weight 1: ", ref=AttrRef(tool, 'chanceA'), min=0, width=50)
            chanceB = IntInputRow("Weight 2: ", ref=AttrRef(tool, 'chanceB'), min=0, width=50)
            chanceC = IntInputRow("Weight 3: ", ref=AttrRef(tool, 'chanceC'), min=0, width=50)
            chanceD = IntInputRow("Weight 4: ", ref=AttrRef(tool, 'chanceD'), min=0, width=50)
            chanceABcolumns = [chanceA, chanceB]
            chanceCDcolumns = [chanceC, chanceD]
            chanceAB = Row(chanceABcolumns)
            chanceCD = Row(chanceCDcolumns)

            col = [
                panel.brushPresetOptions, 
                panel.modeStyleGrid,
                panel.noiseInput,
                panel.brushSizeRows,
                panel.replaceWith1Button,
                panel.replaceWith2Button,
                panel.replaceWith3Button,
                panel.replaceWith4Button,
                chanceAB,
                chanceCD,
                airFill,
            ]
            return col

        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.brushStyleMod)

            blocks = chunk.Blocks[slices]
            data = chunk.Data[slices]

            airFill = op.options['airFill']
            replaceWith1 = op.options['replaceWith1']
            chanceA = op.options['chanceA']
            replaceWith2 = op.options['replaceWith2']
            chanceB = op.options['chanceB']
            replaceWith3 = op.options['replaceWith3']
            chanceC = op.options['chanceC']
            replaceWith4 = op.options['replaceWith4']
            chanceD = op.options['chanceD']

            totalChance = chanceA + chanceB + chanceC + chanceD

            if totalChance == 0:
                print "Total Chance value can't be 0"
                return

            if airFill == False:
                airtable = numpy.zeros((materials.id_limit, 16), dtype='bool')
                airtable[0] = True
                replaceMaskAir = airtable[blocks, data]
                brushMask &= ~replaceMaskAir

            brushMaskOption1 = numpy.copy(brushMask)
            brushMaskOption2 = numpy.copy(brushMask)
            brushMaskOption3 = numpy.copy(brushMask)
            brushMaskOption4 = numpy.copy(brushMask)

            x=-1
            y=-1
            z=-1

            for array_x in brushMask:
                x += 1
                y = -1
                for array_y in brushMask[x]:
                    y += 1
                    z=-1
                    for array_z in brushMask[x][y]:
                        z += 1
                        if brushMask[x][y][z]:
                            randomChance = random.randint(1, totalChance)
                            if chanceA >= randomChance:
                                brushMaskOption1[x][y][z] = True
                                brushMaskOption2[x][y][z] = False
                                brushMaskOption3[x][y][z] = False
                                brushMaskOption4[x][y][z] = False
                                continue
                            if chanceA + chanceB >= randomChance:
                                brushMaskOption1[x][y][z] = False
                                brushMaskOption2[x][y][z] = True
                                brushMaskOption3[x][y][z] = False
                                brushMaskOption4[x][y][z] = False
                                continue
                            if chanceA + chanceB + chanceC >= randomChance:
                                brushMaskOption1[x][y][z] = False
                                brushMaskOption2[x][y][z] = False
                                brushMaskOption3[x][y][z] = True
                                brushMaskOption4[x][y][z] = False
                                continue
                            if chanceA + chanceB + chanceC + chanceD >= randomChance:
                                brushMaskOption1[x][y][z] = False
                                brushMaskOption2[x][y][z] = False
                                brushMaskOption3[x][y][z] = False
                                brushMaskOption4[x][y][z] = True
                                continue

            blocks[brushMaskOption1] = replaceWith1.ID
            data[brushMaskOption1] = replaceWith1.blockData
            blocks[brushMaskOption2] = replaceWith2.ID
            data[brushMaskOption2] = replaceWith2.blockData
            blocks[brushMaskOption3] = replaceWith3.ID
            data[brushMaskOption3] = replaceWith3.blockData
            blocks[brushMaskOption4] = replaceWith4.ID
            data[brushMaskOption4] = replaceWith4.blockData


    class FloodFill(BrushMode):
        name = "Flood Fill"
        options = ['indiscriminate']

        def createOptions(self, panel, tool):
            col = [
                panel.brushPresetOptions,
                panel.brushModeRow,
                panel.blockButton
            ]
            indiscriminateButton = CheckBoxLabel("Indiscriminate", ref=AttrRef(tool, 'indiscriminate'))

            col.append(indiscriminateButton)
            return col

        def apply(self, op, point):

            undoLevel = pymclevel.MCInfdevOldLevel(mkundotemp(), create=True)
            dirtyChunks = set()

            def saveUndoChunk(cx, cz):
                if (cx, cz) in dirtyChunks:
                    return
                dirtyChunks.add((cx, cz))
                undoLevel.copyChunkFrom(op.level, cx, cz)

            doomedBlock = op.level.blockAt(*point)
            doomedBlockData = op.level.blockDataAt(*point)
            checkData = (doomedBlock not in (8, 9, 10, 11))
            indiscriminate = op.options['indiscriminate']

            if indiscriminate:
                checkData = False
                if doomedBlock == 2:  # grass
                    doomedBlock = 3  # dirt
            if doomedBlock == op.blockInfo.ID and (doomedBlockData == op.blockInfo.blockData or checkData == False):
                return

            x, y, z = point
            saveUndoChunk(x // 16, z // 16)
            op.level.setBlockAt(x, y, z, op.blockInfo.ID)
            op.level.setBlockDataAt(x, y, z, op.blockInfo.blockData)

            def processCoords(coords):
                newcoords = collections.deque()

                for (x, y, z) in coords:
                    for _dir, offsets in pymclevel.faceDirections:
                        dx, dy, dz = offsets
                        p = (x + dx, y + dy, z + dz)

                        nx, ny, nz = p
                        b = op.level.blockAt(nx, ny, nz)
                        if indiscriminate:
                            if b == 2:
                                b = 3
                        if b == doomedBlock:
                            if checkData:
                                if op.level.blockDataAt(nx, ny, nz) != doomedBlockData:
                                    continue

                            saveUndoChunk(nx // 16, nz // 16)
                            op.level.setBlockAt(nx, ny, nz, op.blockInfo.ID)
                            op.level.setBlockDataAt(nx, ny, nz, op.blockInfo.blockData)
                            newcoords.append(p)

                return newcoords

            def spread(coords):
                while len(coords):
                    start = datetime.now()

                    num = len(coords)
                    coords = processCoords(coords)
                    d = datetime.now() - start
                    progress = "Did {0} coords in {1}".format(num, d)
                    log.info(progress)
                    yield progress

            showProgress("Flood fill...", spread([point]), cancel=True)
            op.editor.invalidateChunks(dirtyChunks)
            op.undoLevel = undoLevel

    class Replace(Fill):
        name = "Replace"

        def createOptions(self, panel, tool):
            col = [
                panel.brushPresetOptions,
                panel.modeStyleGrid,
                panel.noiseInput,
                panel.brushSizeRows,
                panel.blockButton,
                panel.replaceBlockButton,
            ]
            return col

        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):

            blocks = chunk.Blocks[slices]
            data = chunk.Data[slices]

            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.brushStyleMod)

            replaceWith = op.options['replaceBlockInfo']
            # xxx pasted from fill.py
            if op.blockInfo.wildcard:
                print "Wildcard replace"
                blocksToReplace = []
                for i in range(16):
                    blocksToReplace.append(op.editor.level.materials.blockWithID(op.blockInfo.ID, i))
            else:
                blocksToReplace = [op.blockInfo]

            replaceTable = block_fill.blockReplaceTable(blocksToReplace)
            replaceMask = replaceTable[blocks, data]
            brushMask &= replaceMask

            blocks[brushMask] = replaceWith.ID
            data[brushMask] = replaceWith.blockData
			
    class Vary(Fill):
        name = "Varied Replace"
        options = ['chanceA','chanceB','chanceC','chanceD']

        def createOptions(self, panel, tool):

            seperator = Label("---")
            
            chanceA = IntInputRow("Weight 1: ", ref=AttrRef(tool, 'chanceA'), min=0, width=50)
            chanceB = IntInputRow("Weight 2: ", ref=AttrRef(tool, 'chanceB'), min=0, width=50)
            chanceC = IntInputRow("Weight 3: ", ref=AttrRef(tool, 'chanceC'), min=0, width=50)
            chanceD = IntInputRow("Weight 4: ", ref=AttrRef(tool, 'chanceD'), min=0, width=50)
            chanceABcolumns = [chanceA, chanceB]
            chanceCDcolumns = [chanceC, chanceD]
            chanceAB = Row(chanceABcolumns)
            chanceCD = Row(chanceCDcolumns)
           
            col = [
                panel.brushPresetOptions,
                panel.modeStyleGrid,
                panel.brushSizeRows,
                panel.blockButton,
                seperator,
                panel.replaceWith1Button,
                panel.replaceWith2Button,
                panel.replaceWith3Button,
                panel.replaceWith4Button,
                chanceAB,
                chanceCD,
                ]
            return col


        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):

            blocks = chunk.Blocks[slices]
            data = chunk.Data[slices]

            replaceWith1 = op.options['replaceWith1']
            chanceA = op.options['chanceA']
            replaceWith2 = op.options['replaceWith2']
            chanceB = op.options['chanceB']
            replaceWith3 = op.options['replaceWith3']
            chanceC = op.options['chanceC']
            replaceWith4 = op.options['replaceWith4']
            chanceD = op.options['chanceD']

            totalChance = chanceA + chanceB + chanceC + chanceD

            if totalChance == 0:
                print "Total Chance value can't be 0"
                return

            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.brushStyleMod)

            # xxx pasted from fill.py
            if op.blockInfo.wildcard:
                print "Wildcard replace"
                blocksToReplace = []
                for i in range(16):
                    blocksToReplace.append(op.editor.level.materials.blockWithID(op.blockInfo.ID, i))
            else:
                blocksToReplace = [op.blockInfo]

            replaceTable = block_fill.blockReplaceTable(blocksToReplace)
            replaceMask = replaceTable[blocks, data]
            brushMask &= replaceMask

            brushMaskOption1 = numpy.copy(brushMask)
            brushMaskOption2 = numpy.copy(brushMask)
            brushMaskOption3 = numpy.copy(brushMask)
            brushMaskOption4 = numpy.copy(brushMask)

            x=-1
            y=-1
            z=-1

            for array_x in brushMask:
                x += 1
                y = -1
                for array_y in brushMask[x]:
                    y += 1
                    z=-1
                    for array_z in brushMask[x][y]:
                        z += 1
                        if brushMask[x][y][z]:
                            randomChance = random.randint(1, totalChance)
                            if chanceA >= randomChance:
                                brushMaskOption1[x][y][z] = True
                                brushMaskOption2[x][y][z] = False
                                brushMaskOption3[x][y][z] = False
                                brushMaskOption4[x][y][z] = False
                                continue
                            if chanceA + chanceB >= randomChance:
                                brushMaskOption1[x][y][z] = False
                                brushMaskOption2[x][y][z] = True
                                brushMaskOption3[x][y][z] = False
                                brushMaskOption4[x][y][z] = False
                                continue
                            if chanceA + chanceB + chanceC >= randomChance:
                                brushMaskOption1[x][y][z] = False
                                brushMaskOption2[x][y][z] = False
                                brushMaskOption3[x][y][z] = True
                                brushMaskOption4[x][y][z] = False
                                continue
                            if chanceA + chanceB + chanceC + chanceD >= randomChance:
                                brushMaskOption1[x][y][z] = False
                                brushMaskOption2[x][y][z] = False
                                brushMaskOption3[x][y][z] = False
                                brushMaskOption4[x][y][z] = True
                                continue
            blocks[brushMaskOption1] = replaceWith1.ID
            data[brushMaskOption1] = replaceWith1.blockData
            blocks[brushMaskOption2] = replaceWith2.ID
            data[brushMaskOption2] = replaceWith2.blockData
            blocks[brushMaskOption3] = replaceWith3.ID
            data[brushMaskOption3] = replaceWith3.blockData
            blocks[brushMaskOption4] = replaceWith4.ID
            data[brushMaskOption4] = replaceWith4.blockData

    class Erode(BrushMode):
        name = "Erode"
        options = ['erosionStrength','erosionNoise']

        def createOptions(self, panel, tool):
            erosionNoise = CheckBoxLabel("Noise", ref=AttrRef(tool, 'erosionNoise'))
            erosionStrength = IntInputRow("Strength: ", ref=AttrRef(tool, 'erosionStrength'), min=1, max=20, tooltipText="Number of times to apply erosion." )
            col = [
                panel.brushPresetOptions,
                panel.modeStyleGrid,
                panel.noiseInput,
                panel.brushSizeRows,
                erosionStrength,
                erosionNoise,
            ]
            return col

        def apply(self, op, point):
            brushBox = self.brushBoxForPointAndOptions(point, op.options).expand(1)

            if brushBox.volume > 1048576:
                raise ValueError("Affected area is too big for this brush mode")
			
            erosionStrength = op.options["erosionStrength"]

			
            erosionArea = op.level.extractSchematic(brushBox, entities=False)
            if erosionArea is None:
                return

            blocks = erosionArea.Blocks
            data = erosionArea.Data
            bins = numpy.bincount(blocks.ravel())
            fillBlockID = bins.argmax()
            xcount = -1

            for x in blocks:
                xcount += 1
                ycount = -1
                for y in blocks[xcount]:
                    ycount += 1
                    zcount = -1
                    for z in blocks[xcount][ycount]:
                        zcount += 1
                        if blocks[xcount][ycount][zcount] == fillBlockID:
                            fillBlockData = data[xcount][ycount][zcount]


            def getNeighbors(solidBlocks):
                neighbors = numpy.zeros(solidBlocks.shape, dtype='uint8')
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[:-2, 1:-1, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[2:, 1:-1, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, :-2, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, 2:, 1:-1]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, 1:-1, :-2]
                neighbors[1:-1, 1:-1, 1:-1] += solidBlocks[1:-1, 1:-1, 2:]
                return neighbors

            for i in range(erosionStrength):
                solidBlocks = blocks != 0
                neighbors = getNeighbors(solidBlocks)

                brushMask = createBrushMask(op.brushSize, op.brushStyle, op.brushStyleMod)
                erodeBlocks = neighbors < 5
                if op.options['erosionNoise']:
                    erodeBlocks &= (numpy.random.random(erodeBlocks.shape) > 0.3)
                erodeBlocks[1:-1, 1:-1, 1:-1] &= brushMask
                blocks[erodeBlocks] = 0

                solidBlocks = blocks != 0
                neighbors = getNeighbors(solidBlocks)

                fillBlocks = neighbors > 2
                fillBlocks &= ~solidBlocks
                fillBlocks[1:-1, 1:-1, 1:-1] &= brushMask
                blocks[fillBlocks] = fillBlockID
                data[fillBlocks] = fillBlockData

            op.level.copyBlocksFrom(erosionArea, erosionArea.bounds.expand(-1), brushBox.origin + (1, 1, 1))

    class Topsoil(BrushMode):
        name = "Topsoil"
        options = ['naturalEarth', 'topsoilDepth']

        def createOptions(self, panel, tool):
            depthRow = IntInputRow("Depth: ", ref=AttrRef(tool, 'topsoilDepth'))
            naturalRow = CheckBoxLabel("Only Change Natural Earth", ref=AttrRef(tool, 'naturalEarth'))
            col = [
                panel.brushPresetOptions,
                panel.modeStyleGrid,
                panel.noiseInput,
                panel.brushSizeRows,
                panel.blockButton,
                depthRow,
                naturalRow
            ]
            return col

        def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):

            depth = op.options['topsoilDepth']
            blocktype = op.blockInfo

            blocks = chunk.Blocks[slices]
            data = chunk.Data[slices]

            brushMask = createBrushMask(op.brushSize, op.brushStyle, brushBox.origin, brushBoxThisChunk, op.noise, op.brushStyleMod)


            if op.options['naturalEarth']:
                try:
                    # try to get the block mask from the topsoil filter
                    import topsoil  # @UnresolvedImport
                    blockmask = topsoil.naturalBlockmask()
                    blockmask[blocktype.ID] = True
                    blocktypeMask = blockmask[blocks]

                except Exception, e:
                    print repr(e), " while using blockmask from filters.topsoil"
                    blocktypeMask = blocks != 0

            else:
                # topsoil any block
                blocktypeMask = blocks != 0

            if depth < 0:
                blocktypeMask &= (blocks != blocktype.ID)

            heightmap = extractHeights(blocktypeMask)

            for x, z in itertools.product(*map(xrange, heightmap.shape)):
                h = heightmap[x, z]
                if h >= brushBoxThisChunk.height:
                    continue
                if depth > 0:
                    idx = x, z, slice(max(0, h - depth), h)
                else:
                    # negative depth values mean to put a layer above the surface
                    idx = x, z, slice(h, min(blocks.shape[2], h - depth))
                mask = brushMask[idx]
                blocks[idx][mask] = blocktype.ID
                data[idx][mask] = blocktype.blockData

    class Paste(BrushMode):

        name = "Paste"
        options = ['level'] + ['center' + c for c in 'xyz']

        def brushBoxForPointAndOptions(self, point, options={}):
            point = [p + options.get('center' + c, 0) for p, c in zip(point, 'xyz')]
            return BoundingBox(point, options['level'].size)

        def createOptions(self, panel, tool):
            col = [
            panel.brushPresetOptions, 
            panel.brushModeRow, 
           ]

            importButton = Button("Import", action=tool.importPaste)
            importLabel = ValueDisplay(width=150, ref=AttrRef(tool, "importFilename"))
            importRow = Row((importButton, importLabel))

            stack = tool.editor.copyStack
            if len(stack) == 0:
                tool.importPaste()
            else:
                tool.loadLevel(stack[0])
            tool.centery = 0
            tool.centerx = -(tool.level.Width / 2)
            tool.centerz = -(tool.level.Length / 2)

            cx, cy, cz = [IntInputRow(c, ref=AttrRef(tool, "center" + c), max=a, min=-a)
                          for a, c in zip(tool.level.size, "xyz")]
            centerRow = Row((cx, cy, cz))

            col.extend([importRow, centerRow])

            return col

        def apply(self, op, point):
            level = op.options['level']
            point = [p + op.options['center' + c] for p, c in zip(point, 'xyz')]

            return op.level.copyBlocksFromIter(level, level.bounds, point, create=True)


class BrushOperation(Operation):

    def __init__(self, editor, level, points, options):
        super(BrushOperation, self).__init__(editor, level)

        # if options is None: options = {}

        self.options = options
        self.editor = editor
        if isinstance(points[0], (int, float)):
            points = [points]

        self.points = points

        self.brushSize = options['brushSize']
        self.blockInfo = options['blockInfo']
        self.brushStyle = options['brushStyle']
        self.brushStyleMod = options['brushStyleMod']
        self.brushMode = options['brushMode']

        if max(self.brushSize) > BrushTool.maxBrushSize:
            self.brushSize = (BrushTool.maxBrushSize,) * 3
        if max(self.brushSize) < 1:
            self.brushSize = (1, 1, 1)

        boxes = [self.brushMode.brushBoxForPointAndOptions(p, options) for p in points]
        self._dirtyBox = reduce(lambda a, b: a.union(b), boxes)

    brushStyles = ["Round", "Square", "Diamond"]
    brushStyleMods = ["Normal", "Hollow", "Wireframe"]
    # brushModeNames = ["Fill", "Flood Fill", "Replace", "Erode", "Topsoil", "Paste"]  # "Smooth", "Flatten", "Raise", "Lower", "Build", "Erode", "Evert"]
    brushModeClasses = [
        Modes.Fill,
        Modes.VariedFill,
        Modes.FloodFill,
        Modes.Replace,
		Modes.Vary,
        Modes.Erode,
        Modes.Topsoil,
        Modes.Paste
    ]
    
    
    @property
    def noise(self):
        return self.options.get('brushNoise', 100)
    
    def dirtyBox(self):
        return self._dirtyBox

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(tr("Cannot perform action while saving is taking place"))
            return
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self._dirtyBox)

        def _perform():
            yield 0, len(self.points), tr("Applying {0} brush...").format(self.brushMode.name)
            if self.brushMode.apply is not NotImplemented: #xxx double negative
                for i, point in enumerate(self.points):
                    f = self.brushMode.apply(self, point)
                    if hasattr(f, "__iter__"):
                        for progress in f:
                            yield progress
                    else:
                        yield i, len(self.points), tr("Applying {0} brush...").format(self.brushMode.name)
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
                            yield j * len(self.points) + i, len(self.points) * self._dirtyBox.chunkCount, tr("Applying {0} brush...").format(self.brushMode.name)

                    chunk.chunkChanged()

        if len(self.points) > 10:
            showProgress("Performing brush...", _perform(), cancel=True)
        else:
            exhaust(_perform())



class BrushPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self)
        
        global currentNumber    
        
        #Creating Ref variables to link objects
        self.noiseOption = AttrRef(tool, "brushNoise")
        self.topsoilDepthOption = AttrRef(tool, 'topsoilDepth')
        self.minimumSpacingOption = AttrRef(tool, "minimumSpacing")
        self.brushStyleOption = AttrRef(tool, "brushStyle")
        self.brushStyleModOption = AttrRef(tool, "brushStyleMod")
        self.brushSizeLOption = getattr(BrushSettings, "brushSizeL")
        self.brushSizeWOption = getattr(BrushSettings, "brushSizeW")
        self.brushSizeHOption = getattr(BrushSettings, "brushSizeH")
        self.brushBlockInfoOption = AttrRef(tool, "blockInfo")
        self.replaceBlockInfoOption = AttrRef(tool, "replaceBlockInfo")
        self.erosionNoiseOption = AttrRef(tool, 'erosionNoise')
        self.erosionStrengthOpion = AttrRef(tool, 'erosionStrength')
        self.replaceWith1Option = AttrRef(tool, 'replaceWith1')
        self.replaceWith2Option = AttrRef(tool, 'replaceWith2')
        self.replaceWith3Option = AttrRef(tool, 'replaceWith3')
        self.replaceWith4Option = AttrRef(tool, 'replaceWith4')
        self.chanceAOption = AttrRef(tool, 'chanceA')
        self.chanceBOption = AttrRef(tool, 'chanceB')
        self.chanceCOption = AttrRef(tool, 'chanceC')
        self.chanceDOption = AttrRef(tool, 'chanceD')
        self.indiscriminateOption= AttrRef(tool, 'indiscriminate')
        self.airFillOption = AttrRef(tool, 'airFill')
        self.naturalEarthOption = AttrRef(tool, 'naturalEarth')
            
        self.saveableBrushOptions={
        "Vary Replace 1":self.replaceWith1Option,
        "Vary Replace 2":self.replaceWith2Option,
        "Vary Replace 3":self.replaceWith3Option,
        "Vary Replace 4":self.replaceWith4Option,
        "Chance to Replace 1":self.chanceAOption,
        "Chance to Replace 2":self.chanceBOption,
        "Chance to Replace 3":self.chanceCOption,
        "Chance to Replace 4":self.chanceDOption,
        "Indiscriminate":self.indiscriminateOption,
        "Fill air":self.airFillOption,
        "Change Natural Earth":self.naturalEarthOption,
        "Topsoil Depth":self.topsoilDepthOption,
        "Erosion Noise":self.erosionNoiseOption,
        "Erosion Strength":self.erosionStrengthOpion,
        "Mode": tool.brushMode.name,
        "Noise": self.noiseOption,
        "Minimum Spacing": self.minimumSpacingOption,
        "Style": self.brushStyleOption,
        "Stylemod": self.brushStyleModOption,
        "Size L": self.brushSizeLOption,
        "Size W": self.brushSizeWOption,
        "Size H": self.brushSizeHOption,
        "Block": self.brushBlockInfoOption,
        "Block To Replace": self.replaceBlockInfoOption,
        }

        
        self.tool = tool
        self.brushPresetOptions = self.createPresetRow()
        self.brushModeButton = ChoiceButton([m.name for m in tool.brushModes],
                                            width=150,
                                            choose=self.brushModeChanged)
        
        #self.brushModeButton.selectedChoice = m.VariedFill

        self.brushModeButton.selectedChoice = tool.brushMode.name
        self.brushModeRow = Row((Label("Mode:"), self.brushModeButton))

        self.brushStyleButton = ValueButton(width=self.brushModeButton.width,
                                        ref=self.brushStyleOption,
                                        action=tool.swapBrushStyles)

        self.brushStyleButton.tooltipText = "Shortcut: Alt-1"

        self.brushStyleRow = Row((Label("Brush:"), self.brushStyleButton))
        
        self.brushStyleModButton = ValueButton(width = self.brushModeButton.width,
                                        ref=self.brushStyleModOption,
                                        action=tool.swapBrushStyleMods)
        self.brushStyleModRow = Row((Label("Text:"), self.brushStyleModButton))

        self.modeStyleGrid = Column([
            self.brushModeRow,
            self.brushStyleRow,
            self.brushStyleModRow,
        ])

        
        shapeRows = []
        columns = []
        for d in ["L", "W", "H"]:
            l = Label(d)
            f = IntField(ref=getattr(BrushSettings, "brushSize" + d).propertyRef(), min=1, max=tool.maxBrushSize)
            row = Row((l, f))
            columns.append(row)
            
            #shapeRows.append(row)
    
        self.brushSizeRows = Row(columns)

        self.noiseInput = IntInputRow("Chance: ", ref=self.noiseOption, min=0, max=100)

        self.blockButton = blockButton = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'blockInfo'),
            recentBlocks=tool.recentFillBlocks,
            allowWildcards=(tool.brushMode.name == "Replace"))

        #col = [modeStyleGrid, hollowRow, noiseInput, shapeRows, blockButton]

        self.replaceBlockButton = replaceBlockButton = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'replaceBlockInfo'),
            recentBlocks=tool.recentReplaceBlocks)
            
        self.replaceWith1Button = replaceWith1Button = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'replaceWith1'),
            recentBlocks = tool.recentReplaceBlocks)
            
        self.replaceWith2Button = replaceWith2Button = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'replaceWith2'),
            recentBlocks = tool.recentReplaceBlocks)
        
        self.replaceWith3Button = replaceWith3Button = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'replaceWith3'),
            recentBlocks = tool.recentReplaceBlocks)
            
        self.replaceWith4Button = replaceWith4Button = BlockButton(
            tool.editor.level.materials,
            ref=AttrRef(tool, 'replaceWith4'),
            recentBlocks = tool.recentReplaceBlocks)    
            
        col = tool.brushMode.createOptions(self, tool)

        if self.tool.brushMode.name != "Flood Fill":
            spaceRow = IntInputRow("Line Spacing", ref=self.minimumSpacingOption, min=1, tooltipText=("Hold {0} to draw lines").format(config.config.get("Keys", "Brush Line Tool")))
            col.append(spaceRow)
        col = Column(col)
        
        self.add(col)
        self.shrink_wrap()
        
    def createPresetRow(self):
        def storeBrushPreset(key, value, currentNumber):
            if not config.config.has_option("BrushPresets", key):
                print "No options for " + key + " found, creating new option array"
                a = [value for i in range(1, 10)]
                a[currentNumber] = value
            else:
                a = config.config.get("BrushPresets", key)
                if type(a) != list:
                    a = ast.literal_eval(a)
                a[currentNumber] = value
            config.config.set("BrushPresets", key, a)   

        def saveBrushPreset(currentNumber):
            print "Saving Preset " + str(currentNumber+1)
            if not config.config.has_section("BrushPresets"):
                config.config.add_section("BrushPresets")
            for key in self.saveableBrushOptions:
                if key not in ["Block","Block To Replace","Vary Replace 1","Vary Replace 2","Vary Replace 3","Vary Replace 4", "Mode"]:
                        value = self.saveableBrushOptions[key].get()
                        storeBrushPreset(key, value, currentNumber)
                elif key == "Mode":
                    storeBrushPreset(key, self.saveableBrushOptions[key], currentNumber)
                else:
                     try:
                        keyID = key + " ID"
                        keyData = key + " Data"
                        value = self.saveableBrushOptions[key]
                        for a, b in zip([keyID, keyData],[value.get().ID, value.get().blockData]):
                            storeBrushPreset(a, b, currentNumber)
                     except:
                        print key + " does not have a value yet."


        def loadBrushPreset(number):
            global currentNumber
            if currentNumber != -1:
                saveBrushPreset(currentNumber)
                currentNumber = (int(number) - 1)
            else:
                currentNumber = 0
            print "Loading Preset " + str(currentNumber+1)
            for key in self.saveableBrushOptions:
                if key not in ["Block","Block To Replace","Vary Replace 1","Vary Replace 2","Vary Replace 3","Vary Replace 4", "Mode"]:
                    a = config.config.get("BrushPresets", key)
                    if type(a) != list:
                        a = ast.literal_eval(a)
                    self.saveableBrushOptions[key].set(a[currentNumber])
                elif key == "Mode":
                    a = config.config.get("BrushPresets", key)
                    if type(a) != list:
                        a = ast.literal_eval(a)
                    for m in self.tool.brushModes:
                        if m.name == a[currentNumber]:
                            self.tool.brushMode = a[currentNumber]
                else:
                    aID = config.config.get("BrushPresets", key + " ID")
                    aData = config.config.get("BrushPresets", key + " Data")
                    if type(aID) != list:
                        print "evalling"
                        aID = ast.literal_eval(aID)
                    if type(aData) != list:
                        print "evalling"
                        aData = ast.literal_eval(aData)
                    print aID[0]
                    blockInfo = materials.Block(self.tool.editor.level.materials, aID[currentNumber], aData[currentNumber])
                    print blockInfo
                    if key == "Block":
                        self.blockButton.blockInfo = blockInfo
                    elif key == "Block To Replace":
                        self.replaceBlockButton.blockInfo = blockInfo
                    elif key == "Vary Replace 1":
                        self.replaceWith1Button.blockInfo = blockInfo
                    elif key == "Vary Replace 2":
                        self.replaceWith2Button.blockInfo = blockInfo
                    elif key == "Vary Replace 3":
                        self.replaceWith3Button.blockInfo = blockInfo
                    elif key == "Vary Replace 4":
                        self.replaceWith4Button.blockInfo = blockInfo
            BrushTool.toolSelected(self.tool)

            
        def numberEnable1():
            global currentNumber
            return 1 !=( currentNumber + 1)
        def numberEnable2():
            global currentNumber
            return 2 !=( currentNumber + 1)
        def numberEnable3():
            global currentNumber
            return 3 != ( currentNumber + 1)
        def numberEnable4():
            global currentNumber
            return 4 != ( currentNumber + 1)
        def numberEnable5():
            global currentNumber
            return 5 != ( currentNumber + 1)
        def numberEnable6():
            global currentNumber
            return 6 != ( currentNumber + 1)
        def numberEnable7():
            global currentNumber
            return 7 != ( currentNumber + 1)
        def numberEnable8():
            global currentNumber
            return 8 != ( currentNumber + 1)
        def numberEnable9():
            global currentNumber
            return 9 != ( currentNumber + 1)
                       
        row = []
        row.append(Button("1", action=loadBrushPreset, enable=numberEnable1))
        row.append(Button("2", action=loadBrushPreset, enable=numberEnable2))
        row.append(Button("3", action=loadBrushPreset, enable=numberEnable3))
        row.append(Button("4", action=loadBrushPreset, enable=numberEnable4))
        row.append(Button("5", action=loadBrushPreset, enable=numberEnable5))
        row.append(Button("6", action=loadBrushPreset, enable=numberEnable6))
        row.append(Button("7", action=loadBrushPreset, enable=numberEnable7))
        row.append(Button("8", action=loadBrushPreset, enable=numberEnable8))
        row.append(Button("9", action=loadBrushPreset, enable=numberEnable9))
        
        row = Row(row)

        widget = GLBackground()
        widget.bg_color = (0.8, 0.8, 0.8, 0.8)
        widget.add(row)
        widget.shrink_wrap()
        widget.anchor = "whtr"
        return widget

    def brushModeChanged(self):
        self.tool.brushMode = self.brushModeButton.selectedChoice

    def pickFillBlock(self):
        self.blockButton.action()
        self.tool.blockInfo = self.blockButton.blockInfo
        self.tool.setupPreview()

    def pickReplaceBlock(self):
        self.replaceBlockButton.action()
        self.tool.replaceBlockInfo = self.replaceBlockButton.blockInfo
        self.tool.setupPreview()

    def swap(self):
        t = self.blockButton.recentBlocks
        self.blockButton.recentBlocks = self.replaceBlockButton.recentBlocks
        self.replaceBlockButton.recentBlocks = t

        self.blockButton.updateRecentBlockView()
        self.replaceBlockButton.updateRecentBlockView()
        b = self.blockButton.blockInfo
        self.blockButton.blockInfo = self.replaceBlockButton.blockInfo
        self.replaceBlockButton.blockInfo = b
        
    def rotate(self):
        print "Rotating"
        Block = [[[0 for k in xrange(1)] for j in xrange(1)] for i in xrange(1)]
        Data = [[[0 for k in xrange(1)] for j in xrange(1)] for i in xrange(1)]
        Block[0][0][0] = self.blockButton.blockInfo.ID
        Data[0][0][0] = self.blockButton.blockInfo.blockData
        blockrotation.RotateLeft(Block, Data)
        self.blockButton.blockInfo.blockData = Data[0][0][0]
        
    def roll(self):
        print "Rolling"
        Block = [[[0 for k in xrange(1)] for j in xrange(1)] for i in xrange(1)]
        Data = [[[0 for k in xrange(1)] for j in xrange(1)] for i in xrange(1)]
        Block[0][0][0] = self.blockButton.blockInfo.ID
        Data[0][0][0] = self.blockButton.blockInfo.blockData
        blockrotation.Roll(Block, Data)
        self.blockButton.blockInfo.blockData = Data[0][0][0]    

class BrushToolOptions(ToolOptions):
    def __init__(self, tool):
        Panel.__init__(self)
        alphaField = FloatField(ref=AttrRef(tool, 'brushAlpha'), min=0.0, max=1.0, width=60)
        alphaField.increment = 0.1
        alphaRow = Row((Label("Alpha: "), alphaField))
        autoChooseCheckBox = CheckBoxLabel("Choose Block Immediately",
                                            ref=AttrRef(tool, "chooseBlockImmediately"),
                                            tooltipText="When the brush tool is chosen, prompt for a block type.")

        updateOffsetCheckBox = CheckBoxLabel("Reset Distance When Brush Size Changes",
                                            ref=AttrRef(tool, "updateBrushOffset"),
                                            tooltipText="Whenever the brush size changes, reset the distance to the brush blocks.")

        col = Column((Label("Brush Options"), alphaRow, autoChooseCheckBox, updateOffsetCheckBox, Button("OK", action=self.dismiss)))
        self.add(col)
        self.shrink_wrap()
        return



class BrushTool(CloneTool):
    tooltipText = "Brush\nRight-click for options"
    toolIconName = "brush"
    minimumSpacing = 1

    def __init__(self, *args):
        CloneTool.__init__(self, *args)
        self.optionsPanel = BrushToolOptions(self)
        self.recentFillBlocks = []
        self.recentReplaceBlocks = []
        self.draggedPositions = []
        self.useKey = 0
        self.brushLineKey = 0

        self.brushModes = [c() for c in BrushOperation.brushModeClasses]
        for m in self.brushModes:
            self.options.extend(m.options)

        self._brushMode = self.brushModes[0]
        BrushSettings.updateBrushOffset.addObserver(self)
        BrushSettings.brushSizeW.addObserver(self, 'brushSizeW', callback=self._setBrushSize)
        BrushSettings.brushSizeH.addObserver(self, 'brushSizeH', callback=self._setBrushSize)
        BrushSettings.brushSizeL.addObserver(self, 'brushSizeL', callback=self._setBrushSize)

    panel = None

    def _setBrushSize(self, _):
        if self.updateBrushOffset:
            self.reticleOffset = self.offsetMax()
            self.resetToolDistance()
        self.previewDirty = True

    previewDirty = False
    updateBrushOffset = True
    _reticleOffset = 1
    naturalEarth = True
    erosionStrength = 1
    indiscriminate = False
    chanceA = 0
    chanceB = 0
    chanceC = 0
    chanceD = 0
    replaceWith1 = 0
    replaceWith2 = 0
    replaceWith3 = 0
    replaceWith4 = 0
    erosionNoise = True
    airFill = True



    @property
    def reticleOffset(self):
        if self.brushMode.name == "Flood Fill":
            return 0
        return self._reticleOffset

    @reticleOffset.setter
    def reticleOffset(self, val):
        self._reticleOffset = val

    brushSizeW, brushSizeH, brushSizeL = 1, 1, 1

    @property
    def brushSize(self):
        if self.brushMode.name == "Flood Fill":
            return 1, 1, 1
        return [self.brushSizeW, self.brushSizeH, self.brushSizeL]

    @brushSize.setter
    def brushSize(self, val):
        (w, h, l) = [max(1, min(i, self.maxBrushSize)) for i in val]
        BrushSettings.brushSizeH.set(h)
        BrushSettings.brushSizeL.set(l)
        BrushSettings.brushSizeW.set(w)

    maxBrushSize = 4096

    brushStyles = BrushOperation.brushStyles
    brushStyle = brushStyles[0]
    brushStyleMods = BrushOperation.brushStyleMods
    brushStyleMod = brushStyleMods[0]
    brushModes = None

    @property
    def brushMode(self):
        return self._brushMode

    @brushMode.setter
    def brushMode(self, val):
        if isinstance(val, str):
            val = [b for b in self.brushModes if b.name == val][0]

        self._brushMode = val

        self.hidePanel()
        self.showPanel()

    brushNoise = 100
    topsoilDepth = 1

    chooseBlockImmediately = BrushSettings.chooseBlockImmediately.configProperty()

    _blockInfo = pymclevel.alphaMaterials.Stone

    @property
    def blockInfo(self):
        return self._blockInfo

    @blockInfo.setter
    def blockInfo(self, bi):
        self._blockInfo = bi
        self.setupPreview()

    _replaceBlockInfo = pymclevel.alphaMaterials.Stone

    @property
    def replaceBlockInfo(self):
        return self._replaceBlockInfo

    @replaceBlockInfo.setter
    def replaceBlockInfo(self, bi):
        self._replaceBlockInfo = bi
        self.setupPreview()    
        
    @property
    def brushAlpha(self):
        return BrushSettings.alpha.get()

    @brushAlpha.setter
    def brushAlpha(self, f):
        f = min(1.0, max(0.0, f))
        BrushSettings.alpha.set(f)
        self.setupPreview()

    def importPaste(self):
        clipFilename = mcplatform.askOpenFile(title='Choose a schematic or level...', schematics=True)
        # xxx mouthful
        if clipFilename:
            try:
                self.loadLevel(pymclevel.fromFile(clipFilename, readonly=True))
            except Exception, e:
                alert("Failed to load file %s" % clipFilename)
                self.brushMode = "Fill"
                return

    def loadLevel(self, level):
        self.level = level
        self.minimumSpacing = min([s / 4 for s in level.size])
        self.centerx, self.centery, self.centerz = -level.Width / 2, 0, -level.Length / 2
        CloneTool.setupPreview(self)

    @property
    def importFilename(self):
        if self.level:
            return basename(self.level.filename or "No name")
        return "Nothing selected"

    @property
    def statusText(self):
        return tr("Click and drag to place blocks. {P}-Click to use the block under the cursor. {R} to increase and {F} to decrease size. {E} to rotate, {G} to roll. Mousewheel to adjust distance.").format(
            P=config.config.get("Keys", "Pick Block"),
            R=config.config.get("Keys", "Roll"),
            F=config.config.get("Keys", "Flip"),
            E=config.config.get("Keys", "Rotate"),
            G=config.config.get("Keys", "Mirror"),
            )

    @property
    def worldTooltipText(self):
        if self.useKey == 1:
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return tr("Click to use {0} ({1}:{2})").format(self.editor.level.materials.names[blockID][blockdata], blockID, blockdata)

            except Exception, e:
                return repr(e)

        if self.brushMode.name == "Flood Fill":
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return tr("Click to replace {0} ({1}:{2})").format(self.editor.level.materials.names[blockID][blockdata], blockID, blockdata)

            except Exception, e:
                return repr(e)

    def swapBrushStyles(self):
        brushStyleIndex = self.brushStyles.index(self.brushStyle) + 1
        brushStyleIndex %= len(self.brushStyles)
        self.brushStyle = self.brushStyles[brushStyleIndex]
        self.setupPreview()    
        
    def swapBrushStyleMods(self):
        brushStyleModIndex = self.brushStyleMods.index(self.brushStyleMod) + 1
        brushStyleModIndex %= len(self.brushStyleMods)
        self.brushStyleMod = self.brushStyleMods[brushStyleModIndex]
        self.setupPreview()

    def swapBrushModes(self):
        brushModeIndex = self.brushModes.index(self.brushMode) + 1
        brushModeIndex %= len(self.brushModes)
        self.brushMode = self.brushModes[brushModeIndex]

    options = [
        'blockInfo',
        'brushStyle',
        'brushMode',
        'brushSize',
        'brushNoise',
        'brushStyleMod',
        'replaceBlockInfo',
        'replaceWith1',
        'replaceWith2',
        'replaceWith3',
        'replaceWith4',
    ]

    def getBrushOptions(self):
        bo = dict(((key, getattr(self, key)) for key in self.options))
        return bo
            
   
    draggedDirection = (0, 0, 0)
    centerx = centery = centerz = 0

    @alertException
    def mouseDown(self, evt, pos, direction):
        if self.useKey == 1:
            id = self.editor.level.blockAt(*pos)
            data = self.editor.level.blockDataAt(*pos)
            if self.brushMode.name == "Replace":
                self.panel.replaceBlockButton.blockInfo = self.editor.level.materials.blockWithID(id, data)
            else:
                self.panel.blockButton.blockInfo = self.editor.level.materials.blockWithID(id, data)

            return

        self.draggedDirection = direction
        point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
        self.dragLineToPoint(point)

    @alertException
    def mouseDrag(self, evt, pos, _dir):
        direction = self.draggedDirection
        if self.brushMode.name != "Flood Fill":
            if len(self.draggedPositions):  # if self.isDragging
                self.lastPosition = lastPoint = self.draggedPositions[-1]
                point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
                if any([abs(a - b) >= self.minimumSpacing
                        for a, b in zip(point, lastPoint)]):
                    self.dragLineToPoint(point)
                    
    def keyDown(self, evt):
        keyname = evt.dict.get('keyname', None) or keys.getKey(evt)
        if keyname == config.config.get('Keys', 'Pick Block'):
            self.useKey = 1
        if keyname == config.config.get("Keys", "Brush Line Tool"):
            self.brushLineKey = 1
            
    def keyUp(self, evt):
        keyname = evt.dict.get('keyname', None) or keys.getKey(evt)
        if keyname == config.config.get('Keys', 'Pick Block'):
            self.useKey = 0
        if keyname == config.config.get("Keys", "Brush Line Tool"):
            self.brushLineKey = 0

    def dragLineToPoint(self, point):
        if self.brushMode.name == "Flood Fill":
            self.draggedPositions = [point]
            return

        if self.brushLineKey == 1:
            for move in self.editor.movements:
                if move in config.config.get("Keys", "Brush Line Tool"):
                    self.editor.save = 1
            self.editor.usedKeys = [0, 0, 0, 0, 0, 0]
            self.editor.cameraInputs = [0., 0., 0.]
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
        self.editor.cameraPanKeys = [0., 0.]
        self.editor.get_root().ctrlClicked = -1
        
        if 0 == len(self.draggedPositions):
            return
        
        size = self.brushSize
        # point = self.getReticlePoint(pos, direction)
        if self.brushMode.name == "Flood Fill":
            self.draggedPositions = self.draggedPositions[-1:]

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
        
        if self.brushLineKey == 1:
            for move in self.editor.movements:
                if move in config.config.get("Keys", "Brush Line Tool"):
                    self.editor.save = 1
            self.editor.usedKeys = [0, 0, 0, 0, 0, 0]
            self.editor.cameraInputs = [0., 0., 0.]
            self.editor.get_root().shiftClicked = 0
            self.editor.get_root().shiftPlaced = -2
            self.editor.get_root().ctrlClicked = 0
            self.editor.get_root().ctrlPlaced = -2
            self.editor.get_root().altClicked = 0
            self.editor.get_root().altPlaced = -2
            
            self.brushLineKey = 0
            
        self.lastPosition = None
        self.editor.cameraPanKeys = [0., 0.]
        self.editor.get_root().ctrlClicked = -1

    def toolEnabled(self):
        return True

    def rotate(self,blocksOnly=False):
        print blocksOnly
        if blocksOnly:
            self.panel.rotate()
            self.toolSelected()
        else:
            offs = self.reticleOffset
            dist = self.editor.cameraToolDistance
            W, H, L = self.brushSize
            self.brushSize = L, H, W
            self.reticleOffset = offs
            self.editor.cameraToolDistance = dist
            rotateBlockBrush = leveleditor.Settings.rotateBlockBrush.get()
            if (rotateBlockBrush):
                self.panel.rotate()
            else:
                print "Not rotating block because rotation is turned off in options menu"

    def mirror(self,blocksOnly=False): #actually roll atm
        print blocksOnly
        if blocksOnly:
            self.panel.roll()
            self.toolSelected()
        else:
            offs = self.reticleOffset
            dist = self.editor.cameraToolDistance
            W, H, L = self.brushSize
            self.brushSize = W, L, H
            self.reticleOffset = offs
            self.editor.cameraToolDistance = dist
            rotateBlockBrush = leveleditor.Settings.rotateBlockBrush.get()
            if (rotateBlockBrush):
                self.panel.roll()
            else:
                print "Not rotating block because rotation is turned off in options menu"

    def toolReselected(self):
        if self.brushMode.name == "Replace":
            self.panel.pickReplaceBlock()
        else:
            self.panel.pickFillBlock()

    def flip(self,blocksOnly=False):
        self.decreaseBrushSize()

    def roll(self,blocksOnly=False):
        self.increaseBrushSize()

    def swap(self):
        self.panel.swap()
        
    def decreaseBrushSize(self):
        self.brushSize = [i - 1 for i in self.brushSize]
        # self.setupPreview()

    def increaseBrushSize(self):
        self.brushSize = [i + 1 for i in self.brushSize]    

    @alertException
    def setupPreview(self):
        self.previewDirty = False
        brushSize = self.brushSize
        brushStyle = self.brushStyle
        brushStyleMod = self.brushStyleMod
        if self.brushMode.name == "Replace":
            blockInfo = self.replaceBlockInfo
        if self.brushMode.name in ["Varied Replace","Varied Fill"]:
            blockInfo = self.replaceWith1
        else:
            blockInfo = self.blockInfo

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
                f.BlockLight = self.zerolight
                f.SkyLight = self.zerolight

                if blockInfo.ID:
                    f.Blocks[mask] = blockInfo.ID
                    f.Data[mask] = blockInfo.blockData

                else:
                    f.Blocks[mask] = 255
                self.chunkCache[cx, cz] = f
                return f

        self.level = FakeLevel()

        CloneTool.setupPreview(self, alpha=self.brushAlpha)

    def resetToolDistance(self):
        distance = max(self.editor.cameraToolDistance, 6 + max(self.brushSize) * 1.25)
        # print "Adjusted distance", distance, max(self.brushSize) * 1.25
        self.editor.cameraToolDistance = distance

    def toolSelected(self):

        if self.chooseBlockImmediately:
            blockPicker = BlockPicker(
                self.blockInfo,
                self.editor.level.materials,
                allowWildcards=self.brushMode.name == "Replace")

            if blockPicker.present():
                self.blockInfo = blockPicker.blockInfo

        if self.updateBrushOffset:
            self.reticleOffset = self.offsetMax()
        self.resetToolDistance()
        self.setupPreview()
        self.showPanel()

#    def cancel(self):
#        self.hidePanel()
#        super(BrushTool, self).cancel()

    def showPanel(self):
        if self.panel:
            self.panel.parent.remove(self.panel)

        panel = BrushPanel(self)
        panel.centery = self.editor.centery
        panel.left = self.editor.left
        panel.anchor = "lwh"

        self.panel = panel
        self.editor.add(panel)

    def increaseToolReach(self):
        # self.reticleOffset = max(self.reticleOffset-1, 0)
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            return False
        self.reticleOffset = self.reticleOffset + 1
        return True

    def decreaseToolReach(self):
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            return False
        self.reticleOffset = max(self.reticleOffset - 1, 0)
        return True

    def resetToolReach(self):
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            self.resetToolDistance()
        else:
            self.reticleOffset = self.offsetMax()
        return True

    cameraDistance = EditorTool.cameraDistance

    def offsetMax(self):
        return max(1, ((0.5 * max(self.brushSize)) + 1))

    def getReticleOffset(self):
        return self.reticleOffset

    def getReticlePoint(self, pos, direction):
        if len(self.draggedPositions):
            direction = self.draggedDirection
        return map(lambda a, b: a + (b * self.getReticleOffset()), pos, direction)

    def drawToolReticle(self):
        for pos in self.draggedPositions:
            drawTerrainCuttingWire(BoundingBox(pos, (1, 1, 1)),
                                   (0.75, 0.75, 0.1, 0.4),
                                   (1.0, 1.0, 0.5, 1.0))

    lastPosition = None

    def drawTerrainReticle(self):
        if self.useKey == 1:
            # eyedropper mode
            self.editor.drawWireCubeReticle(color=(0.2, 0.6, 0.9, 1.0))
        else:
            pos, direction = self.editor.blockFaceUnderCursor
            reticlePoint = self.getReticlePoint(pos, direction)

            self.editor.drawWireCubeReticle(position=reticlePoint)
            if reticlePoint != pos:
                GL.glColor4f(1.0, 1.0, 0.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))  # center of reticle block
                    GL.glVertex3f(*map(lambda a, b: a + 0.5 + b * 0.5, pos, direction))  # top side of surface block

            if self.previewDirty:
                self.setupPreview()

            dirtyBox = self.brushMode.brushBoxForPointAndOptions(reticlePoint, self.getBrushOptions())
            self.drawTerrainPreview(dirtyBox.origin)
            if self.brushLineKey == 1 and self.lastPosition and self.brushMode.name != "Flood Fill":
                GL.glColor4f(1.0, 1.0, 1.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, self.lastPosition))
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))

    def updateOffsets(self):
        pass

    def selectionChanged(self):
        pass

    def option1(self):
        self.swapBrushStyles()

    def option2(self):
        self.swapBrushModes()

    def option3(self):
        self.swapBrushStyleMods()

def createBrushMask(shape, style="Round", offset=(0, 0, 0), box=None, chance=100, styleMods="Normal"):
    """
    Return a boolean array for a brush with the given shape and style.
    If 'offset' and 'box' are given, then the brush is offset into the world
    and only the part of the world contained in box is returned as an array
    """

    # we are returning indices for a Blocks array, so swap axes
    wireframe = False
    hollow = True
    if styleMods == "Normal":
        hollow = False
           
    elif styleMods == "Wireframe":
        hollow = True
        wireframe = True
    
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
        if wireframe and style == "Square":
            newmask = numpy.ones(shape=outputShape, dtype='bool')
            newmask = newmask[1:-1,1:-1,1:-1]
            newmask[0, 1:-1, 1:-1] = False
            newmask[-1, 1:-1, 1:-1] = False
            newmask[1:-1,1:-1]= False
            newmask[1:-1,0,1:-1] = False
            newmask[1:-1,-1,1:-1] = False
            submask &= newmask

            
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
