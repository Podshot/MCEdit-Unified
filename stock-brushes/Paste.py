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
    return BoundingBox(point, tool.level.size)


def apply(self, op, point):
    return op.level.copyBlocksFromIter(op.tool.level, op.tool.level.bounds, point, create=True)
