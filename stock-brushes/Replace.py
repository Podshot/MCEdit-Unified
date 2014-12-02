from pymclevel.materials import Block
from editortools.brush import createBrushMask
from pymclevel import block_fill

displayName = 'Replace'
mainBlock = 'Block'
secondaryBlock = 'Block To Replace With'
wildcardBlocks = ['Block']

def createInputs(self):
    self.inputs = (
    {'Hollow': False},
    {'Noise': 100},
    {'W': (3, 1, 4096), 'H': (3, 1, 4096), 'L': (3, 1, 4096)},
    {'Block': materials.blockWithID(1, 0)},
    {'Block To Replace With': materials.blockWithID(1, 0)},
    {'Minimum Spacing': 1}
    )

def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
    brushMask = createBrushMask(op.tool.getBrushSize(), op.options['Style'], brushBox.origin, brushBoxThisChunk, op.options['Noise'], op.options['Hollow'])

    blocks = chunk.Blocks[slices]
    data = chunk.Data[slices]

    replaceWith = op.options['Block']
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

    chunk.Blocks[slices][brushMask] = op.options['Block To Replace With'].ID
    chunk.Data[slices][brushMask] = op.options['Block To Replace With'].blockData
