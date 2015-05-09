from pymclevel.materials import Block
from pymclevel.entity import TileEntity
from editortools.brush import createBrushMask
import numpy
from editortools.operation import mkundotemp
from albow import showProgress
import pymclevel
import datetime
import collections
from pymclevel import BoundingBox
import logging
log = logging.getLogger(__name__)

displayName = 'Flood Fill'
disableStyleButton = True


def createInputs(self):
    self.inputs = (
    {'Block': materials.blockWithID(1, 0)},
    {'Indiscriminate': False},
    )

def createTileEntities(tileEntityTag, level):
    x, y, z = TileEntity.pos(tileEntityTag)

    try:
        chunk = level.getChunk(x >> 4, z >> 4)
    except (pymclevel.ChunkNotPresent, pymclevel.ChunkMalformed):
        return

    chunk.TileEntities.append(tileEntityTag)
    chunk._fakeEntities = None

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
    if doomedBlock == op.options['Block'].ID and (doomedBlockData == op.options['Block'].blockData or not checkData):
        return

    tileEntity = None
    if op.options['Block'].stringID in TileEntity.stringNames.keys():
        tileEntity = TileEntity.stringNames[op.options['Block'].stringID]

    x, y, z = point
    saveUndoChunk(x // 16, z // 16)
    op.level.setBlockAt(x, y, z, op.options['Block'].ID)
    op.level.setBlockDataAt(x, y, z, op.options['Block'].blockData)
    if tileEntity:
        if op.level.tileEntityAt(x, y, z):
            op.level.removeTileEntitiesInBox(BoundingBox((x, y, z), (1, 1, 1)))
        tileEntityObject = TileEntity.Create(tileEntity, (x, y, z))
        createTileEntities(tileEntityObject, op.level)

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
                    if tileEntity:
                        if op.level.tileEntityAt(nx, ny, nz):
                            op.level.removeTileEntitiesInBox(BoundingBox((nx, ny, nz), (1, 1, 1)))
                        tileEntityObject = TileEntity.Create(tileEntity, (nx, ny, nz))
                        createTileEntities(tileEntityObject, op.level)
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
