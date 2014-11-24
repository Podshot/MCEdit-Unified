from pymclevel.materials import Block
from editortools.brush import createBrushMask
import mcplatform
import pymclevel

displayName = 'Paste'
addPasteButton = True

def createInputs(self):
    self.inputs = (
    )    
        
def getDirtyBox(self, point, tool):
    point = []
    for p, c in zip(point, ['center' + ['x', 'y', 'z']]):
        point.append(p + tool.options[c])
    return BoundingBox(point, tool.level.size)


def apply(self, op, chunk, slices, brushBox, brushBoxThisChunk):
    brushMask = createBrushMask(op.tool.getBrushSize(), op.options['Style'], brushBox.origin, brushBoxThisChunk, op.options['Noise'], op.options['Hollow'])

    blocks = chunk.Blocks[slices]
    data = chunk.Data[slices]

    airFill = op.options['Fill Air']

    if airFill == False:
        airtable = numpy.zeros((materials.id_limit, 16), dtype='bool')
        airtable[0] = True
        replaceMaskAir = airtable[blocks, data]
        brushMask &= ~replaceMaskAir

    chunk.Blocks[slices][brushMask] = op.options['Block'].ID
    chunk.Data[slices][brushMask] = op.options['Block'].blockData