from editortools.brush import createBrushMask, createTileEntities
from pymclevel.level import extractHeights
import itertools

displayName = "Topsoil"


def createInputs(self):
    self.inputs = (
    {'Hollow': False},
    {'Noise': 100},
    {'W': (3, 1, 4096), 'H': (3, 1, 4096), 'L': (3, 1, 4096)},
    {'Block': materials.blockWithID(1, 0)},
    {'Depth': 1},
    {'Only Change Natural Earth': False},
    {'Minimum Spacing': 1},
    )


def applyToChunkSlices(self, op, chunk, slices, brushBox, brushBoxThisChunk):

    depth = op.options['Depth']
    blocktype = op.options['Block']

    blocks = chunk.Blocks[slices]
    data = chunk.Data[slices]

    brushMask = createBrushMask(op.tool.getBrushSize(), op.options['Style'], brushBox.origin, brushBoxThisChunk, op.options['Noise'], op.options['Hollow'])

    if op.options['Only Change Natural Earth']:
        try:
            # try to get the block mask from the topsoil filter
            import topsoil  # @UnresolvedImport
            blockmask = topsoil.naturalBlockmask()
            blockmask[blocktype.ID] = True
            blocktypeMask = blockmask[blocks]

        except Exception, e:
            print repr(e), " while using blockmask from filters.topsoil"
            blocktypeMask = blocks != 0

    else:
        # topsoil any block
        blocktypeMask = blocks != 0

    if depth < 0:
        blocktypeMask &= (blocks != blocktype.ID)
    
    if len(blocktypeMask) == 0:
        return
    heightmap = extractHeights(blocktypeMask)

    for x, z in itertools.product(*map(xrange, heightmap.shape)):
        h = heightmap[x, z]
        if h >= brushBoxThisChunk.height:
            continue
        if depth > 0:
            idx = x, z, slice(max(0, h - depth), h)
        else:
            # negative depth values mean to put a layer above the surface
            idx = x, z, slice(h, min(blocks.shape[2], h - depth))
        mask = brushMask[idx]
        blocks[idx][mask] = blocktype.ID
        data[idx][mask] = blocktype.blockData

    createTileEntities(blocktype, brushBoxThisChunk, chunk)
