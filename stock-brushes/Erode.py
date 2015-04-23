from pymclevel.materials import Block
from editortools.brush import createBrushMask
import numpy

displayName = 'Erode'


def createInputs(self):
    self.inputs = (
    {'Hollow': False},
    {'Noise': 100},
    {'W': (3, 1, 4096), 'H': (3, 1, 4096), 'L': (3, 1, 4096)},
    {'Strength': (1, 1, 20)},
    {'Old (Messy)': False},
    {'Minimum Spacing': 1}
    )


def apply(self, op, point):
    brushBox = op.tool.getDirtyBox(point, op.tool).expand(1)

    if brushBox.volume > 1048576:
        print "Affected area is too big for this brush mode"
        return

    erosionStrength = op.options["Strength"]

    erosionArea = op.level.extractSchematic(brushBox, entities=False)
    if erosionArea is None:
        return

    blocks = erosionArea.Blocks
    data = erosionArea.Data
    bins = numpy.bincount(blocks.ravel())
    fillBlockID = bins.argmax()
    xcount = -1

    for _ in blocks:
        xcount += 1
        ycount = -1
        for _ in blocks[xcount]:
            ycount += 1
            zcount = -1
            for _ in blocks[xcount][ycount]:
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

        brushMask = createBrushMask(op.tool.getBrushSize(), op.options['Style'])
        erodeBlocks = neighbors < 5
        if op.options['Old (Messy)']:
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
