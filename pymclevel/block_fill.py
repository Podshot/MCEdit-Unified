import logging
import materials

log = logging.getLogger(__name__)

import numpy

from mclevelbase import exhaust
import blockrotation
from entity import TileEntity


def blockReplaceTable(blocksToReplace):
    blocktable = numpy.zeros((materials.id_limit, 16), dtype='bool')
    for b in blocksToReplace:
            blocktable[b.ID, b.blockData] = True
    return blocktable


def fillBlocks(level, box, blockInfo, blocksToReplace=()):
    return exhaust(level.fillBlocksIter(box, blockInfo, blocksToReplace))


def fillBlocksIter(level, box, blockInfo, blocksToReplace=()):
    if box is None:
        chunkIterator = level.getAllChunkSlices()
        box = level.bounds
    else:
        chunkIterator = level.getChunkSlices(box)

    log.info("Replacing {0} with {1}".format(blocksToReplace, blockInfo))

    changesLighting = True
    blocktable = None
    if len(blocksToReplace):
        blocktable = blockReplaceTable(blocksToReplace)

        newAbsorption = level.materials.lightAbsorption[blockInfo.ID]
        oldAbsorptions = [level.materials.lightAbsorption[b.ID] for b in blocksToReplace]
        changesLighting = False
        for a in oldAbsorptions:
            if a != newAbsorption:
                changesLighting = True

        newEmission = level.materials.lightEmission[blockInfo.ID]
        oldEmissions = [level.materials.lightEmission[b.ID] for b in blocksToReplace]
        for a in oldEmissions:
            if a != newEmission:
                changesLighting = True

    i = 0
    skipped = 0
    replaced = 0

    for (chunk, slices, point) in chunkIterator:
        i += 1
        if i % 100 == 0:
            log.info(u"Chunk {0}...".format(i))
        yield i, box.chunkCount

        blocks = chunk.Blocks[slices]
        data = chunk.Data[slices]
        mask = slice(None)

        needsLighting = changesLighting

        if blocktable is not None:
            mask = blocktable[blocks, data]

            blockCount = mask.sum()
            replaced += blockCount

            # don't waste time relighting and copying if the mask is empty
            if blockCount:
                blocks[:][mask] = blockInfo.ID
                data[mask] = blockInfo.blockData
            else:
                skipped += 1
                needsLighting = False

            def include(tileEntity):
                p = TileEntity.pos(tileEntity)
                x, y, z = map(lambda a, b, c: (a - b) - c, p, point, box.origin)
                return not ((p in box) and mask[x, z, y])

            chunk.TileEntities[:] = filter(include, chunk.TileEntities)

        else:
            blocks[:] = blockInfo.ID
            data[:] = blockInfo.blockData
            chunk.removeTileEntitiesInBox(box)

        chunk.chunkChanged(needsLighting)

    if len(blocksToReplace):
        log.info(u"Replace: Skipped {0} chunks, replaced {1} blocks".format(skipped, replaced))
