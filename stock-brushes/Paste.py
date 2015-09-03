from pymclevel.materials import Block
from editortools.brush import createBrushMask
import mcplatform
import pymclevel
from pymclevel import BoundingBox

displayName = 'Schematic'
addPasteButton = True
disableStyleButton = True


def createInputs(self):
    self.inputs= (         
    )
    pass
        

def createDirtyBox(self, point, tool):
    newpoint = []
    for p in point:
        newpoint.append(p-1)
    return BoundingBox(newpoint, tool.level.size)


def apply(self, op, point):
    level = op.tool.level
    newpoint = []
    for p in point:
        newpoint.append(p-1)
    return op.level.copyBlocksFromIter(level, level.bounds, newpoint, create=True)
