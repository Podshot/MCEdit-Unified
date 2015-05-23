from pymclevel.materials import Block
from editortools.brush import createBrushMask, createTileEntities
import numpy

displayName = 'Fill'
mainBlock = 'Block'


def createInputs(self):
    self.inputs = (
    {'Hollow': False},
    {'Noise': 100},
    {'W': (3, 1, 4096), 'H': (3, 1, 4096), 'L': (3, 1, 4096)},
    {'Block': materials.blockWithID(1, 0)},
    {'Fill Air': True},
    {'Minimum Spacing': 1}
    )


def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):
    brushMask = createBrushMask(op.tool.getBrushSize(), op.options['Style'], brushBox.origin, brushBoxThisChunk, op.options['Noise'], op.options['Hollow'])

    blocks = chunk.Blocks[slices]
    data = chunk.Data[slices]

    airFill = op.options['Fill Air']

    if not airFill:
        airtable = numpy.zeros((materials.id_limit, 16), dtype='bool')
        airtable[0] = True
        replaceMaskAir = airtable[blocks, data]
        brushMask &= ~replaceMaskAir

    chunk.Blocks[slices][brushMask] = op.options['Block'].ID
    chunk.Data[slices][brushMask] = op.options['Block'].blockData

    createTileEntities(op.options['Block'], brushBoxThisChunk, chunk)
