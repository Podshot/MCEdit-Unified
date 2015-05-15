from pymclevel.materials import Block
from editortools.brush import createBrushMask, createTileEntities
from albow import alert
from pymclevel import block_fill
import numpy
import random

displayName = "Varied Replace"
mainBlock = "Block 1"
secondaryBlock = "Block"


def createInputs(self):
    self.inputs = (
    {'Hollow': False, 'Noise': 100},
    {'W': (3, 1, 4096), 'H': (3, 1, 4096), 'L': (3, 1, 4096)},
    {'Block': materials.blockWithID(1, 0)},
    {'Block 1': materials.blockWithID(1, 0)},
    {'Block 2': materials.blockWithID(1, 0)},
    {'Block 3': materials.blockWithID(1, 0)},
    {'Block 4': materials.blockWithID(1, 0)},
    {'Weight 1': (1, 0, None), 'Weight 2': (1, 0, None)},
    {'Weight 3': (1, 0, None), 'Weight 4': (1, 0, None)},
    {'Minimum Spacing': 1},
    )


def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
    brushMask = createBrushMask(op.tool.getBrushSize(), op.options['Style'], brushBox.origin, brushBoxThisChunk, op.options['Noise'], op.options['Hollow'])

    replaceWith1 = op.options['Block 1']
    chanceA = op.options['Weight 1']
    replaceWith2 = op.options['Block 2']
    chanceB = op.options['Weight 2']
    replaceWith3 = op.options['Block 3']
    chanceC = op.options['Weight 3']
    replaceWith4 = op.options['Block 4']
    chanceD = op.options['Weight 4']

    totalChance = chanceA + chanceB + chanceC + chanceD

    if totalChance == 0:
        print "Total Chance value can't be 0."
        return

    blocks = chunk.Blocks[slices]
    data = chunk.Data[slices]

    if op.options['Block'].wildcard:
        print "Wildcard replace"
        blocksToReplace = []
        for i in range(16):
            blocksToReplace.append(op.editor.level.materials.blockWithID(op.options['Block'].ID, i))
    else:
        blocksToReplace = [op.options['Block']]

    replaceTable = block_fill.blockReplaceTable(blocksToReplace)
    replaceMask = replaceTable[blocks, data]
    brushMask &= replaceMask

    brushMaskOption1 = numpy.copy(brushMask)
    brushMaskOption2 = numpy.copy(brushMask)
    brushMaskOption3 = numpy.copy(brushMask)
    brushMaskOption4 = numpy.copy(brushMask)

    x = -1

    for _ in brushMask:
        x += 1
        y = -1
        for _ in brushMask[x]:
            y += 1
            z = -1
            for _ in brushMask[x][y]:
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

    UsedAlready = []
    createTileEntities(replaceWith1, brushBoxThisChunk, chunk)
    UsedAlready.append(replaceWith1.ID)
    if replaceWith2.ID not in UsedAlready:
        createTileEntities(replaceWith2, brushBoxThisChunk, chunk)
        UsedAlready.append(replaceWith2.ID)
    if replaceWith3.ID not in UsedAlready:
        createTileEntities(replaceWith3, brushBoxThisChunk, chunk)
        UsedAlready.append(replaceWith3.ID)
    if replaceWith4.ID not in UsedAlready:
        createTileEntities(replaceWith4, brushBoxThisChunk, chunk)
