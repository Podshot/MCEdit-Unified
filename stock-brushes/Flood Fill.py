from pymclevel.materials import Block
from editortools.brush import createBrushMask
import numpy
from editortools.operation import mkundotemp
from mceutils import showProgress
import pymclevel
import datetime
import collections
import logging
log = logging.getLogger(__name__)

displayName = 'Flood Fill'

def createInputs(self):
    self.inputs = (
    {'Block': materials.blockWithID(1, 0)},
    {'Indiscriminate': False},
    )

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
    indiscriminate = op.options['Indiscriminate']

    if indiscriminate:
        checkData = False
        if doomedBlock == 2:  # grass
            doomedBlock = 3  # dirt
    if doomedBlock == op.options['Block'].ID and (doomedBlockData == op.options['Block'].blockData or checkData == False):
        return

    x, y, z = point
    saveUndoChunk(x // 16, z // 16)
    op.level.setBlockAt(x, y, z, op.options['Block'].ID)
    op.level.setBlockDataAt(x, y, z, op.options['Block'].blockData)

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
                    op.level.setBlockAt(nx, ny, nz, op.options['Block'].ID)
                    op.level.setBlockDataAt(nx, ny, nz, op.options['Block'].blockData)
                    newcoords.append(p)

        return newcoords

    def spread(coords):
        while len(coords):
            start = datetime.datetime.now()

            num = len(coords)
            coords = processCoords(coords)
            d = datetime.datetime.now() - start
            progress = "Did {0} coords in {1}".format(num, d)
            log.info(progress)
            yield progress

    showProgress("Flood fill...", spread([point]), cancel=True)
    op.editor.invalidateChunks(dirtyChunks)
    op.undoLevel = undoLevel

