from pymclevel.materials import Block
from editortools.brush import createBrushMask
import mcplatform
import pymclevel

displayName = 'Paste'
addPasteButton = True

def createInputs(self):
    self.inputs= (         
    )
    pass
        
def getDirtyBox(self, point, tool):
    return BoundingBox(point, tool.level.size)

def apply(self, op, point):
    level = op.tool.level
    point = [p + op.options['center' + c] for p, c in zip(point, 'xyz')]
    return op.level.copyBlocksFromIter(level, level.bounds, point, create=True)
