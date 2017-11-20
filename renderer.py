"""Copyright (c) 2010-2012 David Rio Vierra

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""

"""
renderer.py

What is going on in this file?

Here is an attempt to show the relationships between classes and
their responsibilities

MCRenderer:
    has "position", "origin", optionally "viewFrustum"
    Loads chunks near position+origin, draws chunks offset by origin
    Calls visible on viewFrustum to exclude chunks


    (+) ChunkRenderer
        Has "chunkPosition", "invalidLayers", "lists"
        One per chunk and detail level.
        Creates display lists from BlockRenderers

        (*) BlockRenderer
            Has "vertexArrays"
            One per block type, plus one for low detail and one for Entity

BlockRender documentation

  Each Block renderer renders a particular block types or entities.

  The block renderer that is chosen to draw that block type(by ID)
  is the block renderer class that is lowest in the list within the
  makeRenderstates method. Each blockRenderer is assigned a materialIndex
  and the blockMaterial parameter indicates what material index each block
  in the chunk is therefore what block renderer is used to render it.

  Vertex arrays are arrays of vertices(groups of six elements) and
  every group of 4 vertices is a quad that will be drawn.

  Before the vertex arrays will be drawn `.ravel()` will be called
    (flattened to one dimension arrays).

    The vertex arrays will draw quads and each vertex elements
    with the foramt:
      0:3 index - xyz values
      3:5 index - st(texture coordinates) values
      5   index - rgba(colour) value
                  Note: each element of rgba value is a uint8 type(the 4 colour
                        elements makes up 32 bits) to view/change the values use
                        `.view('uint8')` to change the view of the array into uint8 type.

  To implement a block renderer either makeVertices or makeFaceVertices
  needs to be implemented. The base class BlockRenderer implements
  makeVertices in terms of makeFaceVertices, by iterating over the different
  face directions.

  The makeVertices function is called on the block renderer to gat a
  list of vertexArrays that will draw the blocks for a 16x16x16 chunk.

   parameters:

    all parameters are in xzy order

    facingBlockIndices:
      list of 6, (16, 16, 16) numpy boolean arrays

      each array corresponds to the blocks within the chunk that
      has it face exposed in that direction. The direction is the
      index into the list defined by the constants in pymclevel/faces.py

      This is used to only draw exposed faces

    blocks:
      (16, 16, 16) numpy array of the id of blocks in the chunk

    blockMaterials:
      (16, 16, 16) numpy array of the material index of each block in the chunk

      each material refers to a different block renderer to get the
      material index for this block renderer `self.materialIndex`

    blockData:
      (16, 16, 16) numpy array of the metadata value of each block
      in the chunk

    areaBlockLights:
      (18, 18, 18) numpy array of light value(max of block light and
      skylight) of the chunk and 1 block 'border' aroun it.

    texMap:
      function that takes id, data value and directions
      and returns texture coordinates

    returns a list of vertex arrays in the form of float32 numpy arrays.
    For this chunk.

  The makeFaceVertices gets an vertexArray for a particular face.

   parameters:

    all parameters are in xzy order

    direction:
      the face defined by constants in pymclevel/faces.py

    materialIndices:
      list of (x, z, y) indices of blocks in this chunks that
      is of this material(in blocktypes).

    exposedFaceIndices:
      list of (x, z, y) indices of blocks that has an exposed face
      in the direction `direction`.

    blocks:
      (16, 16, 16) numpy array of the id of blocks in the chunk

    blockData:
      (16, 16, 16) numpy array of the metadata value of each block
      in the chunk

    blockLights:
      (16, 16, 16) numpy array of light values(max of block light and
      skylight) of the blocks in the chunk chunk.

    facingBlockLight:
      (16, 16, 16) numpy array of light values(max of block light and
      skylight) of the blocks just in front of the face.

      i.e.
        if direction = pymclevel.faces.FaceXDecreasing
        facingBlockLight[1, 0, 0] refers to the light level
        at position (0, 0, 0) within the chunk.

    texMap:
      function that takes id, data value and directions
      and returns texture coordinates

    returns a list of vertex arrays in the form of float32 numpy arrays.

  Fields

    blocktypes / getBlocktypes(mats)
      list of block ids the block renderer handles

    detailLevels
      what detail level the renderer render at

    layer
      what layer is this block renderer in

    renderstate
      the render state this block renderer uses

  Models:

    There are also several functions that make it easy to translate
    json models to block renderer.

    makeVertexTemplatesFromJsonModel:
      creates a template from information that is in json models

    rotateTemplate:
      rotate templates. This is equivalent to the rotation in block states files.

    makeVerticesFromModel:
      creates function based on templates to be used for makeVertices function in block renderer.

  Helper functions:

    self.MaterialIndices(blockMaterial):
      Given blockMaterial(parameter in makeVertices) it return a list of
      (x, z, y) indices of blocks in the chunk that are of this block renderer
      material(blocktypes).

    self.makeTemplate(direction, blockIndices):
      get a vertex array filled with default values for face `direction`
      and for the block relating to `blockIndices`

    makeVertexTemplates(xmin=0, ymin=0, zmin=0, xmax=1, ymax=1, zmax=1):
      returns a numpy array with dimensions (6, 4, 6) filled with values to create
      a vertex array for a cube.

  For Entities:

    renderer's for entities are similar to blocks but:
      - they extend EntityRendererGeneric class
      - they are added to the list in calcFacesForChunkRenderer method
      - makeChunkVertices(chunk) where chunk is a chunk object
        is called rather than makeVertices

    there is also a helper method _computeVertices(positions, colors, offset, chunkPosition):
     parameters:
      positions
        locations of entity
      colors
        colors of entity boxes
      offset
        whether to offset the box
      chunkPosition
        chunk position of the chunk

      creates a vertex array that draws entity boxes

"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from depths import DepthOffset
from glutils import gl, Texture
from albow.resource import _2478aq_heot
import logging
import numpy
from OpenGL import GL
import pymclevel
from pymclevel.materials import alphaMaterials, pocketMaterials
import sys
from config import config
# import time

def get_materials():
    alphaMaterials = pymclevel.materials.alphaMaterials
    pocketMaterials = pymclevel.materials.pocketMaterials

def chunkMarkers(chunkSet):
    """ Returns a mapping { size: [position, ...] } for different powers of 2
    as size.
    """

    sizedChunks = defaultdict(list)
    size = 1

    def all4(cx, cz):
        cx &= ~size
        cz &= ~size
        return [(cx, cz), (cx + size, cz), (cx + size, cz + size), (cx, cz + size)]

    # lastsize = 6
    size = 1
    while True:
        nextsize = size << 1
        chunkSet = set(chunkSet)
        while len(chunkSet):
            cx, cz = chunkSet.pop()
            chunkSet.add((cx, cz))
            o = all4(cx, cz)
            others = set(o).intersection(chunkSet)
            if len(others) == 4:
                sizedChunks[nextsize].append(o[0]) # Possibly cache append?
                for c in others:
                    chunkSet.discard(c)
            else:
                for c in others:
                    sizedChunks[size].append(c) # Possibly cache append?
                    chunkSet.discard(c)

        if len(sizedChunks[nextsize]):
            chunkSet = set(sizedChunks[nextsize])
            sizedChunks[nextsize] = []
            size <<= 1
        else:
            break
    return sizedChunks


class ChunkRenderer(object):
    maxlod = 2
    minlod = 0

    def __init__(self, renderer, chunkPosition):
        self.renderer = renderer
        self.blockRenderers = []
        self.detailLevel = 0
        self.invalidLayers = set(Layer.AllLayers)

        self.chunkPosition = chunkPosition
        self.bufferSize = 0
        self.renderstateLists = None

    @property
    def visibleLayers(self):
        return self.renderer.visibleLayers

    def forgetDisplayLists(self, states=None):
        if self.renderstateLists is not None:
            # print "Discarded {0}, gained {1} bytes".format(self.chunkPosition,self.bufferSize)

            for k in states or self.renderstateLists.iterkeys():
                a = self.renderstateLists.get(k, [])
                # print a
                for i in a:
                    gl.glDeleteLists(i, 1)

            if states:
                del self.renderstateLists[states]
            else:
                self.renderstateLists = None

            self.needsRedisplay = True
            self.renderer.discardMasterList()

    def debugDraw(self):
        for blockRenderer in self.blockRenderers:
            blockRenderer.drawArrays(self.chunkPosition, False)

    def makeDisplayLists(self):
        if not self.needsRedisplay:
            return
        self.forgetDisplayLists()
        if not self.blockRenderers:
            return

        lists = defaultdict(list)

        showRedraw = self.renderer.showRedraw

        if not (showRedraw and self.needsBlockRedraw):
            GL.glEnableClientState(GL.GL_COLOR_ARRAY)

        renderers = self.blockRenderers

        for blockRenderer in renderers:
            if self.detailLevel not in blockRenderer.detailLevels:
                continue
            if blockRenderer.layer not in self.visibleLayers:
                continue

            l = blockRenderer.makeArrayList(self.chunkPosition, self.needsBlockRedraw and showRedraw)
            lists[blockRenderer.renderstate].append(l)

        if not (showRedraw and self.needsBlockRedraw):
            GL.glDisableClientState(GL.GL_COLOR_ARRAY)

        self.needsRedisplay = False
        self.renderstateLists = lists

    @property
    def needsBlockRedraw(self):
        return Layer.Blocks in self.invalidLayers

    def invalidate(self, layers=None):
        if layers is None:
            layers = Layer.AllLayers

        if layers:
            layers = set(layers)
            self.invalidLayers.update(layers)
            blockRenderers = [br for br in self.blockRenderers
                              if br.layer is Layer.Blocks
                              or br.layer not in layers]
            if len(blockRenderers) < len(self.blockRenderers):
                self.forgetDisplayLists()
            self.blockRenderers = blockRenderers

            if self.renderer.showRedraw and Layer.Blocks in layers:
                self.needsRedisplay = True

    def calcFaces(self):
        minlod = self.renderer.detailLevelForChunk(self.chunkPosition)

        minlod = min(minlod, self.maxlod)
        if self.detailLevel != minlod:
            self.forgetDisplayLists()
            self.detailLevel = minlod
            self.invalidLayers.add(Layer.Blocks)

            # discard the standard detail renderers
            if minlod > 0:
                blockRenderers = []
                append = blockRenderers.append
                for br in self.blockRenderers:
                    if br.detailLevels != (0,):
                        append(br)

                self.blockRenderers = blockRenderers

        if self.renderer.chunkCalculator:
            for _ in self.renderer.chunkCalculator.calcFacesForChunkRenderer(self):
                yield

        else:
            raise StopIteration

    def vertexArraysDone(self):
        bufferSize = 0
        for br in self.blockRenderers:
            bufferSize += br.bufferSize()
            if self.renderer.alpha != 0xff:
                br.setAlpha(self.renderer.alpha)
        self.bufferSize = bufferSize
        self.invalidLayers = set()
        self.needsRedisplay = True
        self.renderer.invalidateMasterList()

    needsRedisplay = False

    @property
    def done(self):
        return not self.invalidLayers


_XYZ = numpy.s_[..., 0:3]
_ST = numpy.s_[..., 3:5]
_XYZST = numpy.s_[..., :5]
_RGBA = numpy.s_[..., 20:24]
_RGB = numpy.s_[..., 20:23]
_A = numpy.s_[..., 23]


def makeVertexTemplatesFromJsonModel(fromVertices, toVertices, uv):
    """
    This is similar to makeVertexTemplates but is a more convenient
    when reading off of the json model files.
    :param fromVertices: from
    :param toVertices:   to
    :param uv:           keywords uv map
    :return:             template for a cube
    """
    xmin = fromVertices[0] / 16.
    xmax = toVertices[0] / 16.
    ymin = fromVertices[1] / 16.
    ymax = toVertices[1] / 16.
    zmin = fromVertices[2] / 16.
    zmax = toVertices[2] / 16.
    return numpy.array([
        # FaceXIncreasing:
        [[xmax, ymin, zmax, uv["east"][0], uv["east"][3], 0x0b],
         [xmax, ymin, zmin, uv["east"][2], uv["east"][3], 0x0b],
         [xmax, ymax, zmin, uv["east"][2], uv["east"][1], 0x0b],
         [xmax, ymax, zmax, uv["east"][0], uv["east"][1], 0x0b],
        ],

        # FaceXDecreasing:
        [[xmin, ymin, zmin, uv["west"][0], uv["west"][3], 0x0b],
         [xmin, ymin, zmax, uv["west"][2], uv["west"][3], 0x0b],
         [xmin, ymax, zmax, uv["west"][2], uv["west"][1], 0x0b],
         [xmin, ymax, zmin, uv["west"][0], uv["west"][1], 0x0b]],


        # FaceYIncreasing:
        [[xmin, ymax, zmin, uv["up"][0], uv["up"][1], 0x11],  # ne
         [xmin, ymax, zmax, uv["up"][0], uv["up"][3], 0x11],  # nw
         [xmax, ymax, zmax, uv["up"][2], uv["up"][3], 0x11],  # sw
         [xmax, ymax, zmin, uv["up"][2], uv["up"][1], 0x11]],  # se

        # FaceYDecreasing:
        [[xmin, ymin, zmin, uv["down"][0], uv["down"][3], 0x08],
         [xmax, ymin, zmin, uv["down"][2], uv["down"][3], 0x08],
         [xmax, ymin, zmax, uv["down"][2], uv["down"][1], 0x08],
         [xmin, ymin, zmax, uv["down"][0], uv["down"][1], 0x08]],

        # FaceZIncreasing:
        [[xmin, ymin, zmax, uv["south"][0], uv["south"][3], 0x0d],
         [xmax, ymin, zmax, uv["south"][2], uv["south"][3], 0x0d],
         [xmax, ymax, zmax, uv["south"][2], uv["south"][1], 0x0d],
         [xmin, ymax, zmax, uv["south"][0], uv["south"][1], 0x0d]],

        # FaceZDecreasing:
        [[xmax, ymin, zmin, uv["north"][0], uv["north"][3], 0x0d],
         [xmin, ymin, zmin, uv["north"][2], uv["north"][3], 0x0d],
         [xmin, ymax, zmin, uv["north"][2], uv["north"][1], 0x0d],
         [xmax, ymax, zmin, uv["north"][0], uv["north"][1], 0x0d],
        ],

    ])


def rotateTemplate(template, x=0, y=0):
    """
    Rotate template around x-axis and then around
    y-axis. Both angles must to multiples of 90.
    TODO: Add ability for multiples of 45
    """
    template = template.copy()
    for _ in xrange(0, x, 90):
        # y -> -z and z -> y
        template[..., (1, 2)] = template[..., (2, 1)]
        template[..., 2] -= 0.5
        template[..., 2] *= -1
        template[..., 2] += 0.5

    for _ in xrange(0, y, 90):
        # z -> -x and x -> z
        template[..., (0, 2)] = template[..., (2, 0)]
        template[..., 0] -= 0.5
        template[..., 0] *= -1
        template[..., 0] += 0.5
    return template


def makeVerticesFromModel(templates, dataMask=0):
    """
    Returns a function that creates vertex arrays.

    This produces vertex arrays based on the passed
    templates. This doesn't cull any faces based on
    if they are exposed.

    :param templates: list of templates to draw
    :param dataMask:  mask to mask the data
    """
    if isinstance(templates, list):
        templates = numpy.array(templates)
    if templates.shape == (6, 4, 6):
        templates = numpy.array([templates])
    if len(templates.shape) == 4:
        templates = templates[numpy.newaxis, ...]
    elements = templates.shape[0]

    def makeVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        mask = self.getMaterialIndices(blockMaterials)
        blockIndices = mask.nonzero()
        yield

        data = blockData[mask]
        data &= dataMask
        self.vertexArrays = []
        append = self.vertexArrays.append
        for i in xrange(elements):
            vertexArray = numpy.zeros((len(blockIndices[0]), 6, 4, 6), dtype='float32')
            for indicies in xrange(3):
                dimension = (0, 2, 1)[indicies]

                vertexArray[..., indicies] = blockIndices[dimension][:, numpy.newaxis,
                                             numpy.newaxis]  # xxx swap z with y using ^
                
            vertexArray[..., 0:5] += templates[i, data][..., 0:5]
            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices] & 15)[..., numpy.newaxis, :]

            vertexArray.view('uint8')[_RGB] = templates[i, data][..., 5][..., numpy.newaxis]
            vertexArray.view('uint8')[_A] = 0xFF
            vertexArray.view('uint8')[_RGB] *= areaBlockLights[1:-1, 1:-1, 1:-1][blockIndices][
                ..., numpy.newaxis, numpy.newaxis, numpy.newaxis]
            vertexArray.shape = (vertexArray.shape[0] * 6, 4, 6)
            yield
            append(vertexArray)
    return makeVertices


def makeVertexTemplates(xmin=0, ymin=0, zmin=0, xmax=1, ymax=1, zmax=1):
    return numpy.array([

        # FaceXIncreasing:
        [[xmax, ymin, zmax, (zmin * 16), 16 - (ymin * 16), 0x0b],
         [xmax, ymin, zmin, (zmax * 16), 16 - (ymin * 16), 0x0b],
         [xmax, ymax, zmin, (zmax * 16), 16 - (ymax * 16), 0x0b],
         [xmax, ymax, zmax, (zmin * 16), 16 - (ymax * 16), 0x0b],
        ],

        # FaceXDecreasing:
        [[xmin, ymin, zmin, (zmin * 16), 16 - (ymin * 16), 0x0b],
         [xmin, ymin, zmax, (zmax * 16), 16 - (ymin * 16), 0x0b],
         [xmin, ymax, zmax, (zmax * 16), 16 - (ymax * 16), 0x0b],
         [xmin, ymax, zmin, (zmin * 16), 16 - (ymax * 16), 0x0b]],


        # FaceYIncreasing:
        [[xmin, ymax, zmin, xmin * 16, 16 - (zmax * 16), 0x11],  # ne
         [xmin, ymax, zmax, xmin * 16, 16 - (zmin * 16), 0x11],  # nw
         [xmax, ymax, zmax, xmax * 16, 16 - (zmin * 16), 0x11],  # sw
         [xmax, ymax, zmin, xmax * 16, 16 - (zmax * 16), 0x11]],  # se

        # FaceYDecreasing:
        [[xmin, ymin, zmin, xmin * 16, 16 - (zmax * 16), 0x08],
         [xmax, ymin, zmin, xmax * 16, 16 - (zmax * 16), 0x08],
         [xmax, ymin, zmax, xmax * 16, 16 - (zmin * 16), 0x08],
         [xmin, ymin, zmax, xmin * 16, 16 - (zmin * 16), 0x08]],

        # FaceZIncreasing:
        [[xmin, ymin, zmax, xmin * 16, 16 - (ymin * 16), 0x0d],
         [xmax, ymin, zmax, xmax * 16, 16 - (ymin * 16), 0x0d],
         [xmax, ymax, zmax, xmax * 16, 16 - (ymax * 16), 0x0d],
         [xmin, ymax, zmax, xmin * 16, 16 - (ymax * 16), 0x0d]],

        # FaceZDecreasing:
        [[xmax, ymin, zmin, xmin * 16, 16 - (ymin * 16), 0x0d],
         [xmin, ymin, zmin, xmax * 16, 16 - (ymin * 16), 0x0d],
         [xmin, ymax, zmin, xmax * 16, 16 - (ymax * 16), 0x0d],
         [xmax, ymax, zmin, xmin * 16, 16 - (ymax * 16), 0x0d],
        ],

    ])


elementByteLength = 24


def createPrecomputedVertices():
    height = 16
    precomputedVertices = [numpy.zeros(shape=(16, 16, height, 4, 6),  # x,y,z,s,t,rg, ba
                                       dtype='float32') for d in faceVertexTemplates]

    xArray = numpy.arange(16)[:, numpy.newaxis, numpy.newaxis, numpy.newaxis]
    zArray = numpy.arange(16)[numpy.newaxis, :, numpy.newaxis, numpy.newaxis]
    yArray = numpy.arange(height)[numpy.newaxis, numpy.newaxis, :, numpy.newaxis]

    for dir in xrange(len(faceVertexTemplates)):
        precomputedVertices[dir][_XYZ][..., 0] = xArray
        precomputedVertices[dir][_XYZ][..., 1] = yArray
        precomputedVertices[dir][_XYZ][..., 2] = zArray
        precomputedVertices[dir][_XYZ] += faceVertexTemplates[dir][..., 0:3]  # xyz

        precomputedVertices[dir][_ST] = faceVertexTemplates[dir][..., 3:5]  # s
        precomputedVertices[dir].view('uint8')[_RGB] = faceVertexTemplates[dir][..., 5, numpy.newaxis]
        precomputedVertices[dir].view('uint8')[_A] = 0xff

    return precomputedVertices


faceVertexTemplates = makeVertexTemplates()


class ChunkCalculator(object):
    cachedTemplate = None
    cachedTemplateHeight = 0

    whiteLight = numpy.array([[[15] * 16] * 16] * 16, numpy.uint8)
    precomputedVertices = createPrecomputedVertices()

    def __init__(self, level):
        if not hasattr(alphaMaterials, 'Stone'):
            get_materials()
        self.stoneid = stoneid = alphaMaterials.Stone.ID
        self.hiddenOreMaterials[alphaMaterials.Dirt.ID] = stoneid
        self.hiddenOreMaterials[alphaMaterials.Grass.ID] = stoneid
        self.hiddenOreMaterials[alphaMaterials.Sand.ID] = stoneid
        self.hiddenOreMaterials[alphaMaterials.Gravel.ID] = stoneid
        self.hiddenOreMaterials[alphaMaterials.Netherrack.ID] = stoneid

        self.level = level
        self.makeRenderstates(level.materials, getattr(level, "mods_materials", {}))

        # del xArray, zArray, yArray
        self.nullVertices = numpy.zeros((0,) * len(self.precomputedVertices[0].shape),
                                        dtype=self.precomputedVertices[0].dtype)
        config.settings.fastLeaves.addObserver(self)
        config.settings.roughGraphics.addObserver(self)

    class renderstatePlain(object):
        @classmethod
        def bind(cls):
            pass

        @classmethod
        def release(cls):
            pass

    class renderstateVines(object):
        @classmethod
        def bind(cls):
            GL.glDisable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_ALPHA_TEST)

        @classmethod
        def release(cls):
            GL.glEnable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_ALPHA_TEST)

    class renderstateLowDetail(object):
        @classmethod
        def bind(cls):
            GL.glDisable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_TEXTURE_2D)

        @classmethod
        def release(cls):
            GL.glEnable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_TEXTURE_2D)

    class renderstateAlphaTest(object):
        @classmethod
        def bind(cls):
            GL.glEnable(GL.GL_ALPHA_TEST)

        @classmethod
        def release(cls):
            GL.glDisable(GL.GL_ALPHA_TEST)

    class _renderstateAlphaBlend(object):
        @classmethod
        def bind(cls):
            GL.glEnable(GL.GL_BLEND)

        @classmethod
        def release(cls):
            GL.glDisable(GL.GL_BLEND)

    class renderstateWater(_renderstateAlphaBlend):
        pass

    class renderstateIce(_renderstateAlphaBlend):
        pass

    class renderstateEntity(object):
        @classmethod
        def bind(cls):
            GL.glDisable(GL.GL_DEPTH_TEST)
            # GL.glDisable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_TEXTURE_2D)
            GL.glEnable(GL.GL_BLEND)

        @classmethod
        def release(cls):
            GL.glEnable(GL.GL_DEPTH_TEST)
            # GL.glEnable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glDisable(GL.GL_BLEND)

    renderstates = (
        renderstatePlain,
        renderstateVines,
        renderstateLowDetail,
        renderstateAlphaTest,
        renderstateIce,
        renderstateWater,
        renderstateEntity,
    )

    def makeRenderstates(self, materials, mod_materials={}):
        # mod_materials: {"modid": MCMatrial object}
        self.blockRendererClasses = [
            GenericBlockRenderer,
#             ModRenderer,
            LeafBlockRenderer,
            PlantBlockRenderer,
            TorchBlockRenderer,
            WaterBlockRenderer,
            SlabBlockRenderer,
#             ModRenderer,
        ]
        if materials.name in ("Alpha", "Pocket"):
            self.blockRendererClasses += [
                RailBlockRenderer,
                LadderBlockRenderer,
                SnowBlockRenderer,
                CarpetBlockRenderer,
                CactusBlockRenderer,
                PaneBlockRenderer,
                CakeBlockRenderer,
                DaylightBlockRenderer,
                StandingSignRenderer,
                WallSignBlockRenderer,
                LeverBlockRenderer,
                BedBlockRenderer,
                EnchantingBlockRenderer,
                RedstoneBlockRenderer,
                IceBlockRenderer,
                DoorRenderer,
                ButtonRenderer,
                TrapDoorRenderer,
                FenceBlockRenderer,
                FenceGateBlockRenderer,
                StairBlockRenderer,
                RepeaterBlockRenderer,
                VineBlockRenderer,
                PlateBlockRenderer,
                EndRodRenderer,
                # button, floor plate, door -> 1-cube features
                # lever, sign, wall sign, stairs -> 2-cube features
                # fence
                # portal
            ]

        self.materialMap = materialMap = numpy.zeros((pymclevel.materials.id_limit,), 'uint8')
        materialMap[1:] = 1  # generic blocks

        materialCount = 2

        for br in self.blockRendererClasses[1:]:  # skip generic blocks
# #             materialMap[br.getBlocktypes(materials)] = materialCount
#             materialMap[br(self).getBlocktypes(materials)] = materialCount
            # Parse also the mod materials here
            all_mats = mod_materials.values() + [materials]
            for mats in all_mats:
                materialMap[br(self).getBlocktypes(mats)] = materialCount
                br.materialIndex = materialCount
                materialCount += 1
            
#             materialMap[br(self).getBlocktypes(materials, mod_materials)] = materialCount
#             br.materialIndex = materialCount
#             materialCount += 1

        self.exposedMaterialMap = numpy.array(materialMap)
        self.addTransparentMaterials(self.exposedMaterialMap, materialCount)

    def addTransparentMaterials(self, mats, materialCount):
        logging.debug("renderer::ChunkCalculator: Dynamically adding transparent materials.")
#         for b in self.level.materials:
#             yaml = getattr(b, 'yaml', None)
#             if yaml is not None and yaml.get('opacity', 1) < 1:
#                 logging.debug("Adding '%s'" % b)
#                 mats[b.ID] = materialCount
#                 materialCount += 1

        # Also use the mod materials
        all_materials = (getattr(self.level, "mod_materials", {}).values() or [] ) + [self.level.materials]
        for materials in all_materials:
            for b in materials:
                yaml = getattr(b, 'yaml', None)
                if yaml is not None and yaml.get('opacity', 1) < 1:
                    logging.debug("Adding '%s'" % b)
                    mats[b.ID] = materialCount
                    materialCount += 1

        logging.debug("renderer::ChunkCalculator: Transparent materials added.")


    # don't show boundaries between dirt,grass,sand,gravel,or stone.
    # This hiddenOreMaterial definition shall be delayed after the level is loaded, in order to get the exact ones from the game versionned data.
    hiddenOreMaterials = numpy.arange(pymclevel.materials.id_limit, dtype='uint16')

    roughMaterials = numpy.ones((pymclevel.materials.id_limit,), dtype='uint8')
    roughMaterials[0] = 0

    def calcFacesForChunkRenderer(self, cr):
        if not cr.invalidLayers:
            return

        lod = cr.detailLevel
        cx, cz = cr.chunkPosition
        level = cr.renderer.level
        try:
            chunk = level.getChunk(cx, cz)
        except Exception as e:
            if "Session lock lost" in e.message:
                yield
                return
            logging.warn(u"Error reading chunk: %s", e)
            yield
            return

        yield
        brs = []
        append = brs.append
        classes = (
            TileEntityRenderer,
            MonsterRenderer,
            ItemRenderer,
            TileTicksRenderer,
            TerrainPopulatedRenderer,
            ChunkBorderRenderer,
            LowDetailBlockRenderer,
            OverheadBlockRenderer,
        )
        existingBlockRenderers = dict(((type(b), b) for b in cr.blockRenderers))

        for blockRendererClass in classes:
            if cr.detailLevel not in blockRendererClass.detailLevels:
                continue
            if blockRendererClass.layer not in cr.visibleLayers:
                continue
            if blockRendererClass.layer not in cr.invalidLayers:
                if blockRendererClass in existingBlockRenderers:
                    append(existingBlockRenderers[blockRendererClass])

                continue

            br = blockRendererClass(self)
            br.detailLevel = cr.detailLevel

            for _ in br.makeChunkVertices(chunk):
                yield
            append(br)

        blockRenderers = []

        # Recalculate high detail blocks if needed, otherwise retain the high detail renderers
        if lod == 0 and Layer.Blocks in cr.invalidLayers:
            for _ in self.calcHighDetailFaces(cr, blockRenderers):
                yield
        else:
            blockRenderers.extend(br for br in cr.blockRenderers if not isinstance(br, classes))

        # Add the layer renderers
        blockRenderers.extend(brs)
        cr.blockRenderers = blockRenderers

        cr.vertexArraysDone()
        raise StopIteration

    @staticmethod
    def getNeighboringChunks(chunk):
        cx, cz = chunk.chunkPosition
        level = chunk.world

        neighboringChunks = {}
        for dir, dx, dz in ((pymclevel.faces.FaceXDecreasing, -1, 0),
                            (pymclevel.faces.FaceXIncreasing, 1, 0),
                            (pymclevel.faces.FaceZDecreasing, 0, -1),
                            (pymclevel.faces.FaceZIncreasing, 0, 1)):
            if not level.containsChunk(cx + dx, cz + dz):
                neighboringChunks[dir] = pymclevel.infiniteworld.ZeroChunk(level.Height)
            else:
                try:
                    neighboringChunks[dir] = level.getChunk(cx + dx, cz + dz)
                except (EnvironmentError, pymclevel.mclevelbase.ChunkNotPresent, pymclevel.mclevelbase.ChunkMalformed):
                    neighboringChunks[dir] = pymclevel.infiniteworld.ZeroChunk(level.Height)
        return neighboringChunks

    @staticmethod
    def getAreaBlocks(chunk, neighboringChunks):
        chunkWidth, chunkLength, chunkHeight = chunk.Blocks.shape

        areaBlocks = numpy.zeros((chunkWidth + 2, chunkLength + 2, chunkHeight + 2), numpy.uint16)
        areaBlocks[1:-1, 1:-1, 1:-1] = chunk.Blocks
        zeros = numpy.zeros((16, 16, 128), dtype=areaBlocks.dtype)

        nb_fxd = neighboringChunks[pymclevel.faces.FaceXDecreasing].Blocks
        if nb_fxd.shape[2] == chunkHeight / 2:
            nb_fxd = numpy.concatenate((nb_fxd, zeros), axis=2)
        areaBlocks[:1, 1:-1, 1:-1] = nb_fxd[-1:, :chunkLength,
                                     :chunkHeight]
        nb_fxi = neighboringChunks[pymclevel.faces.FaceXIncreasing].Blocks
        if nb_fxi.shape[2] == chunkHeight / 2:
            nb_fxi = numpy.concatenate((nb_fxi, zeros), axis=2)
        areaBlocks[-1:, 1:-1, 1:-1] = nb_fxi[:1, :chunkLength,
                                      :chunkHeight]
        nb_fzd = neighboringChunks[pymclevel.faces.FaceZDecreasing].Blocks
        if nb_fzd.shape[2] == chunkHeight / 2:
            nb_fzd = numpy.concatenate((nb_fzd, zeros), axis=2)
        areaBlocks[1:-1, :1, 1:-1] = nb_fzd[:chunkWidth, -1:,
                                     :chunkHeight]
        nb_fzi = neighboringChunks[pymclevel.faces.FaceZIncreasing].Blocks
        if nb_fzi.shape[2] == chunkHeight / 2:
            nb_fzi = numpy.concatenate((nb_fzi, zeros), axis=2)
        areaBlocks[1:-1, -1:, 1:-1] = nb_fzi[:chunkWidth, :1,
                                      :chunkHeight]
        return areaBlocks

    @staticmethod
    def getFacingBlockIndices(areaBlocks, areaBlockMats):
        facingBlockIndices = [None] * 6

        exposedFacesX = (areaBlockMats[:-1, 1:-1, 1:-1] != areaBlockMats[1:, 1:-1, 1:-1])

        facingBlockIndices[pymclevel.faces.FaceXDecreasing] = exposedFacesX[:-1]
        facingBlockIndices[pymclevel.faces.FaceXIncreasing] = exposedFacesX[1:]

        exposedFacesZ = (areaBlockMats[1:-1, :-1, 1:-1] != areaBlockMats[1:-1, 1:, 1:-1])

        facingBlockIndices[pymclevel.faces.FaceZDecreasing] = exposedFacesZ[:, :-1]
        facingBlockIndices[pymclevel.faces.FaceZIncreasing] = exposedFacesZ[:, 1:]

        exposedFacesY = (areaBlockMats[1:-1, 1:-1, :-1] != areaBlockMats[1:-1, 1:-1, 1:])

        facingBlockIndices[pymclevel.faces.FaceYDecreasing] = exposedFacesY[:, :, :-1]
        facingBlockIndices[pymclevel.faces.FaceYIncreasing] = exposedFacesY[:, :, 1:]
        return facingBlockIndices

    def getAreaBlockLights(self, chunk, neighboringChunks):
        chunkWidth, chunkLength, chunkHeight = chunk.Blocks.shape
        lights = chunk.BlockLight
        skyLight = chunk.SkyLight
        finalLight = self.whiteLight

        if lights is not None:
            finalLight = lights
        if skyLight is not None:
            finalLight = numpy.maximum(skyLight, lights)

        areaBlockLights = numpy.ones((chunkWidth + 2, chunkLength + 2, chunkHeight + 2), numpy.uint8)
        areaBlockLights[:] = 15

        areaBlockLights[1:-1, 1:-1, 1:-1] = finalLight

        zeros = numpy.zeros((16, 16, 128), dtype=areaBlockLights.dtype)

        skyLight, blockLight = neighboringChunks[pymclevel.faces.FaceXDecreasing].SkyLight, neighboringChunks[pymclevel.faces.FaceXDecreasing].BlockLight
        if skyLight.shape[2] == chunkHeight / 2:
            skyLight = numpy.concatenate((skyLight, zeros), axis=2)
            blockLight = numpy.concatenate((blockLight, zeros), axis=2)
        numpy.maximum(skyLight[-1:, :chunkLength, :chunkHeight],
                      blockLight[-1:, :chunkLength, :chunkHeight],
                      areaBlockLights[0:1, 1:-1, 1:-1])

        skyLight, blockLight = neighboringChunks[pymclevel.faces.FaceXIncreasing].SkyLight, neighboringChunks[pymclevel.faces.FaceXIncreasing].BlockLight
        if skyLight.shape[2] == chunkHeight / 2:
            skyLight = numpy.concatenate((skyLight, zeros), axis=2)
            blockLight = numpy.concatenate((blockLight, zeros), axis=2)
        numpy.maximum(skyLight[:1, :chunkLength, :chunkHeight],
                      blockLight[:1, :chunkLength, :chunkHeight],
                      areaBlockLights[-1:, 1:-1, 1:-1])

        skyLight, blockLight = neighboringChunks[pymclevel.faces.FaceZDecreasing].SkyLight, neighboringChunks[pymclevel.faces.FaceZDecreasing].BlockLight
        if skyLight.shape[2] == chunkHeight / 2:
            skyLight = numpy.concatenate((skyLight, zeros), axis=2)
            blockLight = numpy.concatenate((blockLight, zeros), axis=2)
        numpy.maximum(skyLight[:chunkWidth, -1:, :chunkHeight],
                      blockLight[:chunkWidth, -1:, :chunkHeight],
                      areaBlockLights[1:-1, 0:1, 1:-1])

        skyLight, blockLight = neighboringChunks[pymclevel.faces.FaceZIncreasing].SkyLight, neighboringChunks[pymclevel.faces.FaceZIncreasing].BlockLight
        if skyLight.shape[2] == chunkHeight / 2:
            skyLight = numpy.concatenate((skyLight, zeros), axis=2)
            blockLight = numpy.concatenate((blockLight, zeros), axis=2)
        numpy.maximum(skyLight[:chunkWidth, :1, :chunkHeight],
                      blockLight[:chunkWidth, :1, :chunkHeight],
                      areaBlockLights[1:-1, -1:, 1:-1])

        fxd = neighboringChunks[pymclevel.faces.FaceXDecreasing]
        fxi = neighboringChunks[pymclevel.faces.FaceXIncreasing]
        fzd = neighboringChunks[pymclevel.faces.FaceZDecreasing]
        fzi = neighboringChunks[pymclevel.faces.FaceZIncreasing]
        fxd_skyLight = fxd.SkyLight
        fxi_skyLight = fxi.SkyLight
        fzd_skyLight = fzd.SkyLight
        fzi_skyLight = fzi.SkyLight
        fxd_blockLight = fxd.BlockLight
        fxi_blockLight = fxi.BlockLight
        fzd_blockLight = fzd.BlockLight
        fzi_blockLight = fzi.BlockLight
        if fxd_skyLight.shape[2] == chunkHeight / 2:
            fxd_skyLight = numpy.concatenate((fxd_skyLight, zeros), axis=2)
            fxd_blockLight = numpy.concatenate((fxd_blockLight, zeros), axis=2)
        if fxi_skyLight.shape[2] == chunkHeight / 2:
            fxi_skyLight = numpy.concatenate((fxi_skyLight, zeros), axis=2)
            fxi_blockLight = numpy.concatenate((fxi_blockLight, zeros), axis=2)
        if fzd_skyLight.shape[2] == chunkHeight / 2:
            fzd_skyLight = numpy.concatenate((fzd_skyLight, zeros), axis=2)
            fzd_blockLight = numpy.concatenate((fzd_blockLight, zeros), axis=2)
        if fzi_skyLight.shape[2] == chunkHeight / 2:
            fzi_skyLight = numpy.concatenate((fzi_skyLight, zeros), axis=2)
            fzi_blockLight = numpy.concatenate((fzi_blockLight, zeros), axis=2)
        numpy.maximum(fxd_skyLight[-1:, :chunkLength, :chunkHeight],
                      fxd_blockLight[-1:, :chunkLength, :chunkHeight],
                      areaBlockLights[0:1, 1:-1, 1:-1])

        numpy.maximum(fxi_skyLight[:1, :chunkLength, :chunkHeight],
                      fxi_blockLight[:1, :chunkLength, :chunkHeight],
                      areaBlockLights[-1:, 1:-1, 1:-1])

        numpy.maximum(fzd_skyLight[:chunkWidth, -1:, :chunkHeight],
                      fzd_blockLight[:chunkWidth, -1:, :chunkHeight],
                      areaBlockLights[1:-1, 0:1, 1:-1])

        numpy.maximum(fzi_skyLight[:chunkWidth, :1, :chunkHeight],
                      fzi_blockLight[:chunkWidth, :1, :chunkHeight],
                      areaBlockLights[1:-1, -1:, 1:-1])

        minimumLight = 4
        numpy.clip(areaBlockLights, minimumLight, 16, areaBlockLights)

        return areaBlockLights

    def calcHighDetailFaces(self, cr, blockRenderers):
        """ calculate the geometry for a chunk renderer from its blockMats, data,
        and lighting array. fills in the cr's blockRenderers with verts
        for each block facing and material"""

        # chunkBlocks and chunkLights shall be indexed [x,z,y] to follow infdev's convention
        cx, cz = cr.chunkPosition
        level = cr.renderer.level

        chunk = level.getChunk(cx, cz)
#         if isinstance(chunk, pymclevel.level.FakeChunk):
#             return
        neighboringChunks = self.getNeighboringChunks(chunk)

        areaBlocks = self.getAreaBlocks(chunk, neighboringChunks)
        yield

        areaBlockLights = self.getAreaBlockLights(chunk, neighboringChunks)
        yield

        allSlabs = list(set([b.ID for b in level.materials.allBlocks if "Slab" in b.name]))
        for mod_mats in getattr(level, "mod_materials", {}).values():
            allSlabs += list(set([b.ID for b in mod_mats.allBlocks if "Slab" in b.name]))
        for slab in allSlabs:
            slabs = areaBlocks == slab
            if slabs.any():
                areaBlockLights[slabs] = areaBlockLights[:, :, 1:][slabs[:, :, :-1]]
            yield

        showHiddenOres = cr.renderer.showHiddenOres
        if showHiddenOres:
            facingMats = self.hiddenOreMaterials[areaBlocks]
        else:
            facingMats = self.exposedMaterialMap[areaBlocks]

        yield

        if self.roughGraphics:
            areaBlockMats = self.roughMaterials[areaBlocks]
        else:
            areaBlockMats = self.materialMap[areaBlocks]

        facingBlockIndices = self.getFacingBlockIndices(areaBlocks, facingMats)
        yield

        for _ in self.computeGeometry(chunk, areaBlockMats, facingBlockIndices, areaBlockLights, cr, blockRenderers):
            yield

    def computeGeometry(self, chunk, areaBlockMats, facingBlockIndices, areaBlockLights, chunkRenderer, blockRenderers):
        blocks, blockData = chunk.Blocks, chunk.Data
        blockData &= 0xf
        blockMaterials = areaBlockMats[1:-1, 1:-1, 1:-1]
        if self.roughGraphics:
            blockMaterials.clip(0, 1, blockMaterials)
        else:
            # Special case for doors
            #
            # Each part of a door itself does not have all of the information required
            # to render, as direction/whether its open is on the lower part and the hinge
            # side is on the upper part. So here we combine the metadata of the bottom part
            # with the top to form 0-32 metadata(which would be used in door renderer).
            #
            copied = False
            for door in DoorRenderer.blocktypes:
                doors = blocks == door
                if doors.any():
                    if not copied:
                        # copy if required but only once
                        blockData = blockData.copy()
                        copied = True
                    # only accept lower part one block below upper part
                    valid = doors[:, :, :-1] & doors[:, :, 1:] & (blockData[:, :, :-1] < 8) & (blockData[:, :, 1:] >= 8)
                    mask = valid.nonzero()
                    upper_mask = (mask[0], mask[1], mask[2]+1)
                    blockData[mask] += (blockData[upper_mask] - 8) * 16
                    blockData[upper_mask] = blockData[mask] + 8

        sx = sz = slice(0, 16)
        asx = asz = slice(0, 18)

        for y in xrange(0, chunk.world.Height, 16):
            sy = slice(y, y + 16)
            asy = slice(y, y + 18)

            for _ in self.computeCubeGeometry(
                    y,
                    blockRenderers,
                    blocks[sx, sz, sy],
                    blockData[sx, sz, sy],
                    chunk.materials,
                    blockMaterials[sx, sz, sy],
                    [f[sx, sz, sy] for f in facingBlockIndices],
                    areaBlockLights[asx, asz, asy],
                    chunkRenderer,
                    getattr(chunk, "mod_materials", {})):
                yield

    def computeCubeGeometry(self, y, blockRenderers, blocks, blockData, materials, blockMaterials, facingBlockIndices,
                            areaBlockLights, chunkRenderer, mod_materials={}):
        materialCounts = numpy.bincount(blockMaterials.ravel())
        
        append = blockRenderers.append
        
        def texMap(blocks, blockData=0, direction=slice(None)):
            r = []
            for mod_mats in mod_materials.values():
                try:
                    r = mod_mats.blockTextures[blocks, blockData, direction]
                except:
                    pass
            return + materials.blockTextures[blocks, blockData, direction]  # xxx slow

        for blockRendererClass in self.blockRendererClasses:
            mi = blockRendererClass.materialIndex
            if mi >= len(materialCounts) or materialCounts[mi] == 0:
                continue

            blockRenderer = blockRendererClass(self)
            blockRenderer.y = y
            blockRenderer.materials = materials
            blockRenderer.mod_materials = mod_materials
            for _ in blockRenderer.makeVertices(facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights,
                                                texMap):
                yield
            append(blockRenderer)

            yield

    def makeTemplate(self, direction, blockIndices):
        return self.precomputedVertices[direction][numpy.where(blockIndices)]

class Layer:
    Blocks = "Blocks"
    Entities = "Entities"
    Monsters = "Monsters"
    Items = "Items"
    TileEntities = "TileEntities"
    TileTicks = "TileTicks"
    TerrainPopulated = "TerrainPopulated"
    ChunkBorder = "ChunkBorder"
    AllLayers = (Blocks, Entities, Monsters, Items, TileEntities, TileTicks, TerrainPopulated, ChunkBorder)


def getBlocktypesIdStrID(idStr, mats, mod_materials={}):
    """Returns a list of IDs of a block from the idStr.
    :idStr: string: The string ID to be searched.
    Other arguments are the same as in BlockRenderer.getBlocktypes instances."""
    r = []
    for mod_mats in mod_materials.values():
        for namespace in mod_mats.namespaces:
            try:
                r += [mod_mats[":".join((namespace, idStr))].ID]
            except:
                pass
    return r + [mats[":".join(("minecraft", idStr))].ID]


def getBlocktypeIDblocksByType(b_type, mats, mod_materials={}):
    """Returns a list of IDs of blocks using the 'blockBtYpe' interface.
    :b_type: string: The block type to get.
    Other arguments are the same as in BlockRenderer.getBlocktypes instances."""
    r = []
    for mod_mats in mod_materials.values():
        try:
            r += [block.ID for block in mod_mats.blocksByType[b_type]]
        except:
            pass
    return r + [block.ID for block in mats.blocksByType[b_type]]


def getBlocktypeIDblocksByTypes(b_types, mats, mod_materials={}):
    """Returns a list of IDs of blocks using the 'blockBtYpe' interface.
    :b_types: list or tuple of string: The block types to get.
    Other arguments are the same as in BlockRenderer.getBlocktypes instances."""
    r = []
    for mod_mats in mod_materials.values():
        r += [b.ID for b in mod_mats if b.type in b_types]
    return r + [b.ID for b in mats if b.type in b_types]


def getBlocktypesAttribute(attr, mats, mod_materials={}, filter="", filter_status=True):
    """Returns a list of IDs of blocks by getting 'attr' from materials.
    :attr: string: The attribute to be used.
    :filter: string: Used to filter results.
    :filter_status: bool: Wheter to return block IDs containing 'filter'.
        Default to an empty string.
        or the ones which does not contain 'filter'.
        Default to 'True'.
    Other arguments are the same as in BlockRenderer.getBlocktypes instances."""
    r = []
    filter = filter.lower()
    for mod_mats in mod_materials.values():
        try:
            r += [a.ID for a in getattr(mod_mats, attr) if (filter in a.name.lower()) == filter_status]
        except:
            pass
    return r + [a.ID for a in getattr(mats, attr) if (filter in a.name.lower()) == filter_status]


class BlockRenderer(object):
    detailLevels = (0,)
    layer = Layer.Blocks
    directionOffsets = {
        pymclevel.faces.FaceXDecreasing: numpy.s_[:-2, 1:-1, 1:-1],
        pymclevel.faces.FaceXIncreasing: numpy.s_[2:, 1:-1, 1:-1],
        pymclevel.faces.FaceYDecreasing: numpy.s_[1:-1, 1:-1, :-2],
        pymclevel.faces.FaceYIncreasing: numpy.s_[1:-1, 1:-1, 2:],
        pymclevel.faces.FaceZDecreasing: numpy.s_[1:-1, :-2, 1:-1],
        pymclevel.faces.FaceZIncreasing: numpy.s_[1:-1, 2:, 1:-1],
    }
    renderstate = ChunkCalculator.renderstateAlphaTest
    used = False

    def __init__(self, cc):
        self.makeTemplate = cc.makeTemplate
        self.chunkCalculator = cc
        self.vertexArrays = []
        self.materials = cc.level.materials
        self.mod_materials = getattr(cc.level, "mod_materials", {})
        pass

    def getBlocktypes(self, mats, mod_materials={}):
        return self.blocktypes

    def setAlpha(self, alpha):
        "alpha is an unsigned byte value"
        for a in self.vertexArrays:
            a.view('uint8')[_RGBA][..., 3] = alpha

    def bufferSize(self):
        return sum(a.size for a in self.vertexArrays) * 4

    def getMaterialIndices(self, blockMaterials):
        return blockMaterials == self.materialIndex

    def makeVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        append = arrays.append
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]

        for (direction, exposedFaceIndices) in enumerate(facingBlockIndices):
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            vertexArray = self.makeFaceVertices(direction, materialIndices, exposedFaceIndices, blocks, blockData,
                                                blockLight, facingBlockLight, texMap)
            yield
            if len(vertexArray):
                append(vertexArray)
        self.vertexArrays = arrays

    def makeArrayList(self, chunkPosition, showRedraw):
        l = gl.glGenLists(1)
        GL.glNewList(l, GL.GL_COMPILE)
        self.drawArrays(chunkPosition, showRedraw)
        GL.glEndList()
        return l

    def drawArrays(self, chunkPosition, showRedraw):
        cx, cz = chunkPosition
        y = 0
        if hasattr(self, 'y'):
            y = self.y
        with gl.glPushMatrix(GL.GL_MODELVIEW):
            GL.glTranslate(cx << 4, y, cz << 4)

            if showRedraw:
                GL.glColor(1.0, 0.25, 0.25, 1.0)

            self.drawVertices()

    def drawVertices(self):
        if self.vertexArrays:
            for buf in self.vertexArrays:
                self.drawFaceVertices(buf)

    def drawFaceVertices(self, buf):
        if not len(buf):
            return
        stride = elementByteLength
        
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, (buf.ravel()))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, stride, (buf.ravel()[3:]))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype=numpy.uint8).ravel()[20:]))

        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)


class EntityRendererGeneric(BlockRenderer):
    renderstate = ChunkCalculator.renderstateEntity
    detailLevels = (0, 1, 2)

    def drawFaceVertices(self, buf):
        if not len(buf):
            return
        stride = elementByteLength

        GL.glVertexPointer(3, GL.GL_FLOAT, stride, (buf.ravel()))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, stride, (buf.ravel()[3:]))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype=numpy.uint8).ravel()[20:]))

        GL.glDepthMask(False)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)

        GL.glLineWidth(2.0)
        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

        GL.glPolygonOffset(DepthOffset.TerrainWire, DepthOffset.TerrainWire)
        with gl.glEnable(GL.GL_POLYGON_OFFSET_FILL, GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glDepthMask(True)

    @staticmethod
    def _computeVertices(positions, colors, offset=False, chunkPosition=(0, 0)):
        cx, cz = chunkPosition
        x = cx << 4
        z = cz << 4

        vertexArray = numpy.zeros(shape=(len(positions), 6, 4, 6), dtype='float32')
        if positions:
            positions = numpy.array(positions)
            positions[:, (0, 2)] -= (x, z)
            if offset:
                positions -= 0.5

            vertexArray.view('uint8')[_RGBA] = colors
            vertexArray[_XYZ] = positions[:, numpy.newaxis, numpy.newaxis, :]
            vertexArray[_XYZ] += faceVertexTemplates[_XYZ]
            vertexArray.shape = (len(positions) * 6, 4, 6)
        return vertexArray


class TileEntityRenderer(EntityRendererGeneric):
    layer = Layer.TileEntities

    def makeChunkVertices(self, chunk):
        tilePositions = []
        append = tilePositions.append
        for i, ent in enumerate(chunk.TileEntities):
            if i % 10 == 0:
                yield
            if 'x' not in ent:
                continue
            append(pymclevel.TileEntity.pos(ent))
        tiles = self._computeVertices(tilePositions, (0xff, 0xff, 0x33, 0x44), chunkPosition=chunk.chunkPosition)
        yield
        self.vertexArrays = [tiles]


class BaseEntityRenderer(EntityRendererGeneric):
    pass


class MonsterRenderer(BaseEntityRenderer):
    layer = Layer.Entities  # xxx Monsters
    notMonsters = {"Item", "XPOrb", "Painting", "ItemFrame", "ArmorStand"}

    def makeChunkVertices(self, chunk):
        monsterPositions = []
        append = monsterPositions.append
        notMonsters = self.chunkCalculator.level.defsIds.mcedit_defs.get('notMonsters', self.notMonsters)
        for i, ent in enumerate(chunk.Entities):
            if i % 10 == 0:
                yield
            id = ent["id"].value
            if id in notMonsters:
                continue
            pos = pymclevel.Entity.pos(ent)
            pos[1] += 0.5
            append(pos)

        monsters = self._computeVertices(monsterPositions,
                                         (0xff, 0x22, 0x22, 0x44),
                                         offset=True,
                                         chunkPosition=chunk.chunkPosition)
        yield
        self.vertexArrays = [monsters]


class EntityRenderer(BaseEntityRenderer):
    @staticmethod
    def makeChunkVertices(chunk):
        yield


class ItemRenderer(BaseEntityRenderer):
    layer = Layer.Items

    def makeChunkVertices(self, chunk):
        entityPositions = []
        entityColors = []
        colorMap = {
            "Item": (0x22, 0xff, 0x22, 0x5f),
            "XPOrb": (0x88, 0xff, 0x88, 0x5f),
            "Painting": (134, 96, 67, 0x5f),
            "ItemFrame": (134, 96, 67, 0x5f),
            "ArmorStand": (0x22, 0xff, 0x22, 0x5f),
        }
        pos_append = entityPositions.append
        color_append = entityColors.append
        defsIds = self.chunkCalculator.level.defsIds
        mcedit_defs = defsIds.mcedit_defs
        mcedit_ids = defsIds.mcedit_ids
        for i, ent in enumerate(chunk.Entities):
            if i % 10 == 0:
                yield
            # Let get the color from the versionned data, and use the 'old' way as fallback
            color = mcedit_defs.get(mcedit_ids.get(ent["id"].value), {}).get("mapcolor")
            if color is None:
                color = colorMap.get(ent["id"].value)

            if color is None:
                continue
            pos = pymclevel.Entity.pos(ent)
            noRenderDelta = mcedit_defs.get('noRenderDelta', ("Painting", "ItemFrame"))
            if ent["id"].value not in noRenderDelta:
                pos[1] += 0.5
            pos_append(pos)
            color_append(color)

        entities = self._computeVertices(entityPositions,
                                         numpy.array(entityColors, dtype='uint8')[:, numpy.newaxis, numpy.newaxis],
                                         offset=True, chunkPosition=chunk.chunkPosition)
        yield
        self.vertexArrays = [entities]


class TileTicksRenderer(EntityRendererGeneric):
    layer = Layer.TileTicks

    def makeChunkVertices(self, chunk):
        if hasattr(chunk, "TileTicks"):
            self.vertexArrays.append(self._computeVertices([[tick[j].value for j in "xyz"] for i, tick in enumerate(chunk.TileTicks)],
                                                           (0xff, 0xff, 0xff, 0x44),
                                                           chunkPosition=chunk.chunkPosition))
        yield
        

class TerrainPopulatedRenderer(EntityRendererGeneric):
    layer = Layer.TerrainPopulated
    vertexTemplate = numpy.zeros((6, 4, 6), 'float32')
    vertexTemplate[_XYZ] = faceVertexTemplates[_XYZ]
    vertexTemplate[_XYZ] *= (16, 256, 16)
    color = (255, 200, 155)
    vertexTemplate.view('uint8')[_RGBA] = color + (72,)

    def drawFaceVertices(self, buf):
        if not len(buf):
            return
        stride = elementByteLength

        GL.glVertexPointer(3, GL.GL_FLOAT, stride, (buf.ravel()))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, stride, (buf.ravel()[3:]))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype=numpy.uint8).ravel()[20:]))

        GL.glDepthMask(False)

        GL.glDisable(GL.GL_CULL_FACE)

        with gl.glEnable(GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)

        GL.glEnable(GL.GL_CULL_FACE)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)

        GL.glLineWidth(1.0)
        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glLineWidth(2.0)
        with gl.glEnable(GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glLineWidth(1.0)

        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glDepthMask(True)

    def makeChunkVertices(self, chunk):   
        neighbors = self.chunkCalculator.getNeighboringChunks(chunk)
        
        def getpop(ch):
            return getattr(ch, "TerrainPopulated", True)
        
        pop = getpop(chunk)
        yield
        if pop:
            return
        
        visibleFaces = [
            getpop(neighbors[pymclevel.faces.FaceXIncreasing]),
            getpop(neighbors[pymclevel.faces.FaceXDecreasing]),
            True,
            True,
            getpop(neighbors[pymclevel.faces.FaceZIncreasing]),
            getpop(neighbors[pymclevel.faces.FaceZDecreasing]),
        ]

        visibleFaces = numpy.array(visibleFaces, dtype='bool')
        verts = self.vertexTemplate[visibleFaces]
        self.vertexArrays.append(verts)

        yield


class ChunkBorderRenderer(EntityRendererGeneric):
    layer = Layer.ChunkBorder
    color = (0, 210, 225)
    vertexTemplate = numpy.zeros((6, 4, 6), 'float32')
    vertexTemplate[_XYZ] = faceVertexTemplates[_XYZ]
    vertexTemplate[_XYZ] *= (16, 256, 16)
    vertexTemplate.view('uint8')[_RGBA] = color + (150,)
   
    def makeChunkVertices(self, chunk):
        visibleFaces = [
            True,
            True,
            True,
            True,
            True,
            True,
        ]
        yield
        visibleFaces = numpy.array(visibleFaces, dtype='bool')
        verts = self.vertexTemplate[visibleFaces]
        self.vertexArrays.append(verts)
        yield

    def drawFaceVertices(self, buf):
        if not len(buf):
            return
        stride = elementByteLength
  
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, (buf.ravel()))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, stride, (buf.ravel()[3:]))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype=numpy.uint8).ravel()[20:]))
  
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
  
        GL.glLineWidth(1)
        with gl.glEnable(GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glLineWidth(2.0)
        with gl.glEnable(GL.GL_DEPTH_TEST):
            GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glLineWidth(1.0)
  
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)


class LowDetailBlockRenderer(BlockRenderer):
    renderstate = ChunkCalculator.renderstateLowDetail
    detailLevels = (1,)

    def drawFaceVertices(self, buf):
        if not len(buf):
            return
        stride = 16

        GL.glVertexPointer(3, GL.GL_FLOAT, stride, numpy.ravel(buf.ravel()))
        GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, stride, (buf.view(dtype='uint8').ravel()[12:]))

        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDrawArrays(GL.GL_QUADS, 0, len(buf) * 4)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

    def setAlpha(self, alpha):
        for va in self.vertexArrays:
            va.view('uint8')[..., -1] = alpha

    def makeChunkVertices(self, ch):
        step = 1
        level = ch.world
        vertexArrays = []
        blocks = ch.Blocks
        heightMap = ch.HeightMap

        heightMap = heightMap[::step, ::step]
        blocks = blocks[::step, ::step]

        if 0 in blocks.shape:
            return

        chunkWidth, chunkLength, chunkHeight = blocks.shape
        blockIndices = numpy.zeros((chunkWidth, chunkLength, chunkHeight), bool)

        gridaxes = list(numpy.indices((chunkWidth, chunkLength)))
        h = numpy.swapaxes(heightMap - 1, 0, 1)[:chunkWidth, :chunkLength]
        numpy.clip(h, 0, chunkHeight - 1, out=h)

        gridaxes = [gridaxes[0], gridaxes[1], h]

        depths = numpy.zeros((chunkWidth, chunkLength), dtype='uint16')
        depths[1:-1, 1:-1] = reduce(numpy.minimum, (h[1:-1, :-2], h[1:-1, 2:], h[:-2, 1:-1]), h[2:, 1:-1])
        yield

        try:
            topBlocks = blocks[gridaxes]
            nonAirBlocks = (topBlocks != 0)
            blockIndices[gridaxes] = nonAirBlocks
            h += 1
            numpy.clip(h, 0, chunkHeight - 1, out=h)
            overblocks = blocks[gridaxes][nonAirBlocks].ravel()

        except ValueError as e:
            raise ValueError(str(e.args) + "Chunk shape: {0}".format(blockIndices.shape), sys.exc_info()[-1])

        if nonAirBlocks.any():
            blockTypes = blocks[blockIndices]

            mod_materials = getattr(level, "mod_materials", {}).values()

            flatcolors = level.materials.flatColors[blockTypes, ch.Data[blockIndices] & 0xf][:, numpy.newaxis, :]
            for mod_mats in mod_materials:
                flatcolors += mod_mats.flatColors[blockTypes, ch.Data[blockIndices] & 0xf][:, numpy.newaxis, :]
            x, z, y = blockIndices.nonzero()

            yield
            vertexArray = numpy.zeros((len(x), 4, 4), dtype='float32')
            vertexArray[_XYZ][..., 0] = x[:, numpy.newaxis]
            vertexArray[_XYZ][..., 1] = y[:, numpy.newaxis]
            vertexArray[_XYZ][..., 2] = z[:, numpy.newaxis]

            va0 = numpy.array(vertexArray)

            va0[..., :3] += faceVertexTemplates[pymclevel.faces.FaceYIncreasing, ..., :3]

            overmask = overblocks > 0
            flatcolors[overmask] = level.materials.flatColors[:, 0][overblocks[overmask]][:, numpy.newaxis]
            for mod_mats in mod_materials:
                flatcolors[overmask] += mod_mats.flatColors[:, 0][overblocks[overmask]][:, numpy.newaxis]

            if self.detailLevel == 2:
                heightfactor = (y / float(2.0 * ch.world.Height)) + 0.5
                flatcolors[..., :3] = flatcolors[..., :3].astype(float) * heightfactor[:, numpy.newaxis, numpy.newaxis]

            _RGBA = numpy.s_[..., 12:16]
            va0.view('uint8')[_RGBA] = flatcolors

            va0[_XYZ][:, :, 0] *= step
            va0[_XYZ][:, :, 2] *= step

            yield
            if self.detailLevel == 2:
                self.vertexArrays = [va0]
                return

            va1 = numpy.array(vertexArray)
            va1[..., :3] += faceVertexTemplates[pymclevel.faces.FaceXIncreasing, ..., :3]

            va1[_XYZ][:, (0, 1), 1] = depths[nonAirBlocks].ravel()[:, numpy.newaxis]  # stretch to floor
            va1[_XYZ][:, (1, 2), 0] -= 1.0  # turn diagonally
            va1[_XYZ][:, (2, 3), 1] -= 0.5  # drop down to prevent intersection pixels

            va1[_XYZ][:, :, 0] *= step
            va1[_XYZ][:, :, 2] *= step

            flatcolors = flatcolors.astype(float) * 0.8

            va1.view('uint8')[_RGBA] = flatcolors
            grassmask = topBlocks[nonAirBlocks] == 2
            # color grass sides with dirt's color
            va1.view('uint8')[_RGBA][grassmask] = level.materials.flatColors[:, 0][[3]][:, numpy.newaxis]
            for mod_mats in mod_materials:
                va1.view('uint8')[_RGBA][grassmask] += mod_mats.flatColors[:, 0][[3]][:, numpy.newaxis]

            va2 = numpy.array(va1)
            va2[_XYZ][:, (1, 2), 0] += step
            va2[_XYZ][:, (0, 3), 0] -= step

            vertexArrays = [va1, va2, va0]

        self.vertexArrays = vertexArrays


class OverheadBlockRenderer(LowDetailBlockRenderer):
    detailLevels = (2,)


class GenericBlockRenderer(BlockRenderer):
    renderstate = ChunkCalculator.renderstateAlphaTest

    materialIndex = 1

    def makeGenericVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        vertexArrays = []
        append = vertexArrays.append
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield

        for (direction, exposedFaceIndices) in enumerate(facingBlockIndices):
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            blockIndices = materialIndices & exposedFaceIndices

            theseBlocks = blocks[blockIndices]
            bdata = blockData[blockIndices]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(theseBlocks, bdata, direction)[:, numpy.newaxis, 0:2]

            vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            if self.materials.name in ("Alpha", "Pocket"):
                if direction == pymclevel.faces.FaceYIncreasing:
                    grass = theseBlocks == alphaMaterials['minecraft:grass'].ID
                    vertexArray.view('uint8')[_RGB][grass] = vertexArray.view('uint8')[_RGB][grass].astype(float) * self.grassColor
            yield

            append(vertexArray)

        self.vertexArrays = vertexArrays

    grassColor = grassColorDefault = [0.39, 0.71, 0.23]  # 62C743

    makeVertices = makeGenericVertices

class ModRenderer(GenericBlockRenderer):

    textures = {}
    printed = False
    mod_blocks = []
    mods = []

#     @classmethod
#     def getBlocktypes(cls, mats):
#         if not cls.mod_blocks:
#             blocks = []
#             extend = blocks.extend
#             for mod in cls.mods:
#                 extend(mod.blocks)
#             cls.mod_blocks = blocks
#             return blocks
#         return cls.mod_blocks

    def getBlocktypes(self, mats, mod_materials={}):
        if not self.mod_blocks:
            blocks = []
            extend = blocks.extend
            for mod in self.mods:
                extend(mod.block_ids_names.keys())
            self.mod_blocks = blocks
            return blocks
        return self.mod_blocks

    def build(self):
#         from mceutils import loadPNGTexture
        #import os
        #cls._t_mods = [
        #    {
        #        "name": "Test Mod",
        #        "blocks": [404, 406],
        #        "texture": loadPNGTexture(os.path.join(".", "mods", "test_mod", "texture.png")),
        #    }, {
        #        "name": "Test Mod #2",
        #        "blocks": [500, 501],
        #        "texture": loadPNGTexture(os.path.join(".", "mods", "test_mod_2", "texture.png"))
        #    }
        #]
#         if hasattr(self.materials, 'mods'):
#             for mod in self.materials.mods:
#                 if mod.texture_path is None:
#                     setattr(mod, 'texture', self.materials.terrainTexture)
#                     continue
#                 setattr(mod, 'texture', loadPNGTexture(mod.texture_path))
#                 self.mods.append(mod)
        
        
#         print "ModRenderer.build"
        if hasattr(self.chunkCalculator.level, "mods"):
            for modid, mod_obj in self.chunkCalculator.level.mods.items():
#                 print "modid", modid, "mod_obj.texture", mod_obj.texture
                if not mod_obj.texture:
                    setattr(mod_obj, 'texture', self.materials.terrainTexture)
                self.mods.append(mod_obj)
                self.textures[modid] = mod_obj.texture

    def __init__(self, cc):
        super(GenericBlockRenderer, self).__init__(cc)
        self.vertexMap = {}
        
        
        
        # Return a MCMaterial object list containing all the loaded mods defs.
#         self.mod_materials = getattr(cc.level, "mod_materials", None)
#         print "ModRenderer.mod_materials", self.mod_materials

        #from mceutils import loadPNGTexture
        #self.mats = cc.level.materials
        #if self.textures == {}:
        #    for mod in self.mats.mods:
        #        self.textures[mod.name] = loadPNGTexture(mod.texture)
        #cc.level.materials.addBlock(404, texture=[0,0])
        #cc.level.materials.addBlock(500, texture=[0,2])
        #import os
        #filename = os.path.join(".", "mods", "test_mod", "texture.png")
        #from mceutils import loadPNGTexture
        #self.texture = loadPNGTexture(filename)

#         if not self.__class__.mods:
#             self.build()
        #t_mod1 = object()
        #setattr(t_mod1, 'name', "Test Mod")
        #setattr(t_mod1, 'blocks', [404, 406])
        #setattr(t_mod1, 'texture', self.texture)
        #self._t_mods.append(t_mod1)
        
        
        
        self.build()

    def makeVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
#         for mod in self.mods:
#             old_shape = blocks.shape
#             _blocks = blocks.copy()
#             _blocks = _blocks.ravel()
#             _blocks[numpy.in1d(_blocks, mod.blocks, invert=True)] = 0
#             _blocks = numpy.reshape(_blocks, old_shape)
# 
#             self.vertexArrays = []
#             for _ in super(ModRenderer, self).makeVertices(facingBlockIndices, _blocks, blockMaterials, blockData, areaBlockLights, texMap):
#                 yield
#             self.vertexMap[mod.name] = self.vertexArrays
#             self.vertexArrays = []

        for mod in self.mods:
            old_shape = blocks.shape
            _blocks = blocks.copy()
            _blocks = _blocks.ravel()
            _blocks[numpy.in1d(_blocks, mod.block_ids_modid.keys(), invert=True)] = 0
            _blocks = numpy.reshape(_blocks, old_shape)

            self.vertexArrays = []
            for _ in super(ModRenderer, self).makeVertices(facingBlockIndices, _blocks, blockMaterials, blockData, areaBlockLights, texMap):
                yield
            self.vertexMap[mod.modid] = self.vertexArrays
            self.vertexArrays = []



    def drawVertices(self):
        GL.glPushAttrib(GL.GL_TEXTURE_BIT)
        for mod in self.mods:
            #GL.glPushAttrib(GL.GL_TEXTURE_BIT)
            mod.texture.bind()
#             self.vertexArrays = self.vertexMap[mod.name]
            self.vertexArrays = self.vertexMap[mod.modid]
            super(ModRenderer, self).drawVertices()
            self.vertexArrays = []
            #GL.glPopAttrib()
        GL.glPopAttrib()
        #for mod in self.mats.mods:
        #GL.glPushAttrib(GL.GL_TEXTURE_BIT)
            #self.textures[mod.name].bind()
        #self.texture.bind()
        #if not self.printed:
        #    print len(self.vertexArrays)
        #    print self.vertexArrays
        #    self.printed = True
        #super(GenericBlockRenderer, self).drawVertices()
        #GL.glPopAttrib()
        
        
        


class LeafBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [block.ID for block in mats.blocksByType["LEAVES"]]
        return getBlocktypeIDblocksByType("LEAVES", mats, mod_materials)

    @property
    def renderstate(self):
        if self.chunkCalculator.fastLeaves:
            return ChunkCalculator.renderstatePlain
        else:
            return ChunkCalculator.renderstateAlphaTest

    def makeLeafVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        append = arrays.append
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield

        if self.materials.name in ("Alpha", "Pocket"):
            if not self.chunkCalculator.fastLeaves:
                blockIndices = materialIndices
                data = blockData[blockIndices]
                data &= 0x3  # ignore decay states
                leaves = (data == alphaMaterials.Leaves.blockData)
                pines = (data == alphaMaterials.PineLeaves.blockData)
                birches = (data == alphaMaterials.BirchLeaves.blockData)
                jungle = (data == alphaMaterials.JungleLeaves.blockData)
                acacia = (data == alphaMaterials.AcaciaLeaves.blockData)
                darkoak = (data == alphaMaterials.DarkOakLeaves.blockData)
                texes = texMap(blocks[blockIndices], [0], 0)
        else:
            blockIndices = materialIndices
            texes = texMap(blocks[blockIndices], [0], 0)

        for (direction, exposedFaceIndices) in enumerate(facingBlockIndices):
            if self.materials.name in ("Alpha", "Pocket"):
                if self.chunkCalculator.fastLeaves:
                    blockIndices = materialIndices & exposedFaceIndices
                    data = blockData[blockIndices]
                    data &= 0x3  # ignore decay states
                    leaves = (data == alphaMaterials.Leaves.blockData)
                    pines = (data == alphaMaterials.PineLeaves.blockData)
                    birches = (data == alphaMaterials.BirchLeaves.blockData)
                    jungle = (data == alphaMaterials.JungleLeaves.blockData)
                    acacia = (data == alphaMaterials.AcaciaLeaves.blockData)
                    darkoak = (data == alphaMaterials.DarkOakLeaves.blockData)

                    texes = texMap(blocks[blockIndices], data, 0)

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texes[:, numpy.newaxis]

            if not self.chunkCalculator.fastLeaves:
                vertexArray[_ST] -= (0x10, 0x0)

            vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            if self.materials.name in ("Alpha", "Pocket"):
                vertexArray.view('uint8')[_RGB][leaves] = vertexArray.view('uint8')[_RGB][leaves].astype(float) * self.leafColor
                vertexArray.view('uint8')[_RGB][pines] = vertexArray.view('uint8')[_RGB][pines].astype(float) * self.pineLeafColor
                vertexArray.view('uint8')[_RGB][birches] = vertexArray.view('uint8')[_RGB][birches].astype(float) * self.birchLeafColor
                vertexArray.view('uint8')[_RGB][jungle] = vertexArray.view('uint8')[_RGB][jungle].astype(float) * self.jungleLeafColor
                vertexArray.view('uint8')[_RGB][acacia] = vertexArray.view('uint8')[_RGB][acacia].astype(float) * self.acaciaLeafColor
                vertexArray.view('uint8')[_RGB][darkoak] = vertexArray.view('uint8')[_RGB][darkoak].astype(float) * self.darkoakLeafColor

            yield
            append(vertexArray)

        self.vertexArrays = arrays

    leafColor = leafColorDefault = [0x48 / 255., 0xb5 / 255., 0x18 / 255.]  # 48b518
    pineLeafColor = pineLeafColorDefault = [0x61 / 255., 0x99 / 255., 0x61 / 255.]  # 0x619961
    birchLeafColor = birchLeafColorDefault = [0x80 / 255., 0xa7 / 255., 0x55 / 255.]  # 0x80a755
    jungleLeafColor = jungleLeafColorDefault = [0x48 / 255., 0xb5 / 255., 0x18 / 255.]  # 48b518
    acaciaLeafColor = acaciaLeafColorDefault = [0x48 / 255., 0xb5 / 255., 0x18 / 255.]  # 48b518
    darkoakLeafColor = darkoakLeafColorDefault = [0x48 / 255., 0xb5 / 255., 0x18 / 255.]  # 48b518

    makeVertices = makeLeafVertices

class PlantBlockRenderer(BlockRenderer):
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
        # blocktypes = [6, 37, 38, 39, 40, 59, 83]
        # if mats.name != "Classic": blocktypes += [31, 32]  # shrubs, tall grass
        # if mats.name == "Alpha": blocktypes += [115]  # nether wart
#         blocktypes = []
#         types = ("DECORATION_CROSS", "NETHER_WART", "CROPS", "STEM")
#         for mod_mats in mod_materials.values():
#             blocktypes += [b.ID for b in mod_mats if b.type in types]
#         blocktypes += [b.ID for b in mats if b.type in types]
# 
#         return blocktypes
        return getBlocktypeIDblocksByTypes(("DECORATION_CROSS", "NETHER_WART", "CROPS", "STEM"), mats, mod_materials)

    renderstate = ChunkCalculator.renderstateAlphaTest

    def makePlantVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        append = arrays.append
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield

        theseBlocks = blocks[blockIndices]

        bdata = blockData[blockIndices]
        texes = texMap(blocks[blockIndices], bdata, 0)

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]
        lights = blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

        colorize = None
        if self.materials.name != "Classic":  #so hacky, someone more competent fix this
            colorize = (theseBlocks == self.materials.TallGrass.ID) & (bdata != 0)
            colorize2 = (theseBlocks == self.materials.TallFlowers.ID) & (bdata != 0) & (
            bdata != 1) & (bdata != 4) & (bdata != 5)

        for direction in (
        pymclevel.faces.FaceXIncreasing, pymclevel.faces.FaceXDecreasing, pymclevel.faces.FaceZIncreasing,
        pymclevel.faces.FaceZDecreasing):
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                return

            if direction == pymclevel.faces.FaceXIncreasing:
                vertexArray[_XYZ][..., 1:3, 0] -= 1
            if direction == pymclevel.faces.FaceXDecreasing:
                vertexArray[_XYZ][..., 1:3, 0] += 1
            if direction == pymclevel.faces.FaceZIncreasing:
                vertexArray[_XYZ][..., 1:3, 2] -= 1
            if direction == pymclevel.faces.FaceZDecreasing:
                vertexArray[_XYZ][..., 1:3, 2] += 1

            vertexArray[_ST] += texes[:, numpy.newaxis, 0:2]

            vertexArray.view('uint8')[_RGB] = 0xf  # ignore precomputed directional light
            vertexArray.view('uint8')[_RGB] *= lights
            if colorize is not None:
                vertexArray.view('uint8')[_RGB][colorize] = vertexArray.view('uint8')[_RGB][colorize].astype(float) * LeafBlockRenderer.leafColor
                vertexArray.view('uint8')[_RGB][colorize2] = vertexArray.view('uint8')[_RGB][colorize2].astype(float) * LeafBlockRenderer.leafColor
            append(vertexArray)
            yield

        self.vertexArrays = arrays

    makeVertices = makePlantVertices


class TorchBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         r = []
#         for mod_mats in mod_materials.values():
#             try:
#                 r += [block.ID for block in mats.blocksByType["TORCH"]]
#             except:
#                 pass
#         return r + [block.ID for block in mats.blocksByType["TORCH"]]
        return getBlocktypeIDblocksByType("TORCH", mats, mod_materials)
    
    renderstate = ChunkCalculator.renderstateAlphaTest
    torchOffsetsStraight = [
        [  # FaceXIncreasing
           (-7 / 16., 0, 0),
           (-7 / 16., 0, 0),
           (-7 / 16., 0, 0),
           (-7 / 16., 0, 0),
        ],
        [  # FaceXDecreasing
           (7 / 16., 0, 0),
           (7 / 16., 0, 0),
           (7 / 16., 0, 0),
           (7 / 16., 0, 0),
        ],
        [  # FaceYIncreasing
           (7 / 16., -6 / 16., 7 / 16.),
           (7 / 16., -6 / 16., -7 / 16.),
           (-7 / 16., -6 / 16., -7 / 16.),
           (-7 / 16., -6 / 16., 7 / 16.),
        ],
        [  # FaceYDecreasing
           (7 / 16., 0., 7 / 16.),
           (-7 / 16., 0., 7 / 16.),
           (-7 / 16., 0., -7 / 16.),
           (7 / 16., 0., -7 / 16.),
        ],

        [  # FaceZIncreasing
           (0, 0, -7 / 16.),
           (0, 0, -7 / 16.),
           (0, 0, -7 / 16.),
           (0, 0, -7 / 16.)
        ],
        [  # FaceZDecreasing
           (0, 0, 7 / 16.),
           (0, 0, 7 / 16.),
           (0, 0, 7 / 16.),
           (0, 0, 7 / 16.)
        ],

    ]

    torchOffsetsSouth = [
        [  # FaceXIncreasing
           (-7 / 16., 3 / 16., 0),
           (-7 / 16., 3 / 16., 0),
           (-7 / 16., 3 / 16., 0),
           (-7 / 16., 3 / 16., 0),
        ],
        [  # FaceXDecreasing
           (7 / 16., 3 / 16., 0),
           (7 / 16., 3 / 16., 0),
           (7 / 16., 3 / 16., 0),
           (7 / 16., 3 / 16., 0),
        ],
        [  # FaceYIncreasing
           (7 / 16., -3 / 16., 7 / 16.),
           (7 / 16., -3 / 16., -7 / 16.),
           (-7 / 16., -3 / 16., -7 / 16.),
           (-7 / 16., -3 / 16., 7 / 16.),
        ],
        [  # FaceYDecreasing
           (7 / 16., 3 / 16., 7 / 16.),
           (-7 / 16., 3 / 16., 7 / 16.),
           (-7 / 16., 3 / 16., -7 / 16.),
           (7 / 16., 3 / 16., -7 / 16.),
        ],

        [  # FaceZIncreasing
           (0, 3 / 16., -7 / 16.),
           (0, 3 / 16., -7 / 16.),
           (0, 3 / 16., -7 / 16.),
           (0, 3 / 16., -7 / 16.)
        ],
        [  # FaceZDecreasing
           (0, 3 / 16., 7 / 16.),
           (0, 3 / 16., 7 / 16.),
           (0, 3 / 16., 7 / 16.),
           (0, 3 / 16., 7 / 16.),
        ],

    ]
    torchOffsetsNorth = torchOffsetsWest = torchOffsetsEast = torchOffsetsSouth

    torchOffsets = [
                       torchOffsetsStraight,
                       torchOffsetsSouth,
                       torchOffsetsNorth,
                       torchOffsetsWest,
                       torchOffsetsEast,
                       torchOffsetsStraight,
                   ] + [torchOffsetsStraight] * 10

    torchOffsets = numpy.array(torchOffsets, dtype='float32')

    torchOffsets[1][..., 3, :, 0] -= 0.5

    torchOffsets[1][..., 0:2, 0:2, 0] -= 0.5
    torchOffsets[1][..., 4:6, 0:2, 0] -= 0.5
    torchOffsets[1][..., 0:2, 2:4, 0] -= 0.1
    torchOffsets[1][..., 4:6, 2:4, 0] -= 0.1

    torchOffsets[1][..., 2, :, 0] -= 0.25

    torchOffsets[2][..., 3, :, 0] += 0.5
    torchOffsets[2][..., 0:2, 0:2, 0] += 0.5
    torchOffsets[2][..., 4:6, 0:2, 0] += 0.5
    torchOffsets[2][..., 0:2, 2:4, 0] += 0.1
    torchOffsets[2][..., 4:6, 2:4, 0] += 0.1
    torchOffsets[2][..., 2, :, 0] += 0.25

    torchOffsets[3][..., 3, :, 2] -= 0.5
    torchOffsets[3][..., 0:2, 0:2, 2] -= 0.5
    torchOffsets[3][..., 4:6, 0:2, 2] -= 0.5
    torchOffsets[3][..., 0:2, 2:4, 2] -= 0.1
    torchOffsets[3][..., 4:6, 2:4, 2] -= 0.1
    torchOffsets[3][..., 2, :, 2] -= 0.25

    torchOffsets[4][..., 3, :, 2] += 0.5
    torchOffsets[4][..., 0:2, 0:2, 2] += 0.5
    torchOffsets[4][..., 4:6, 0:2, 2] += 0.5
    torchOffsets[4][..., 0:2, 2:4, 2] += 0.1
    torchOffsets[4][..., 4:6, 2:4, 2] += 0.1
    torchOffsets[4][..., 2, :, 2] += 0.25

    upCoords = ((7, 6), (7, 8), (9, 8), (9, 6))
    downCoords = ((7, 14), (7, 16), (9, 16), (9, 14))

    def makeTorchVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = self.getMaterialIndices(blockMaterials)
        torchOffsets = self.torchOffsets[blockData[blockIndices]]
        texes = texMap(blocks[blockIndices], blockData[blockIndices])
        yield
        arrays = []
        append = arrays.append
        for direction in xrange(6):
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                return

            vertexArray.view('uint8')[_RGBA] = 0xff
            vertexArray[_XYZ] += torchOffsets[:, direction]
            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_ST] = self.upCoords
            if direction == pymclevel.faces.FaceYDecreasing:
                vertexArray[_ST] = self.downCoords
            vertexArray[_ST] += texes[:, numpy.newaxis, direction]
            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeTorchVertices


class LeverBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         r = []
#         for mod_mats in mod_materials.values():
#             for namespace in mod_mats.namespaces:
#                 try:
#                     r += mod_mats[":".join((namespace, "lever"))].ID
#                 except:
#                     pass
#         return r + [mats["minecraft:lever"].ID]
        return getBlocktypesIdStrID("lever", mats, mod_materials)
    
    leverBaseTemplate = makeVertexTemplatesFromJsonModel((5, 0, 4), (11, 3, 12), {
        "down": (10, 0, 16, 8),
        "up": (10, 0, 16, 8),
        "north": (10, 8, 16, 11),
        "south": (10, 8, 16, 11),
        "west": (2, 0, 10, 3),
        "east": (2, 0, 10, 3)
    })
    
    leverBaseTemplates = numpy.array([
        rotateTemplate(leverBaseTemplate, x=180, y=90),
        rotateTemplate(leverBaseTemplate, x=90, y=90),
        rotateTemplate(leverBaseTemplate, x=90, y=270),
        rotateTemplate(leverBaseTemplate, x=90, y=180),
        rotateTemplate(leverBaseTemplate, x=270, y=180),
        leverBaseTemplate,
        rotateTemplate(leverBaseTemplate, y=90),
        rotateTemplate(leverBaseTemplate, x=180),
        rotateTemplate(leverBaseTemplate, x=180, y=90),
        rotateTemplate(leverBaseTemplate, x=90, y=90),
        rotateTemplate(leverBaseTemplate, x=270, y=90),
        rotateTemplate(leverBaseTemplate, x=270),
        rotateTemplate(leverBaseTemplate, x=270, y=180),
        leverBaseTemplate,
        rotateTemplate(leverBaseTemplate, y=90),
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6))
    ])
    
    leverTemplate = makeVertexTemplatesFromJsonModel((7, 1, 7), (9, 11, 9), {
        "down": (7, 6, 9, 8),
        "up": (7, 6, 9, 8),
        "north": (7, 6, 9, 16),
        "south": (7, 6, 9, 16),
        "west": (7, 6, 9, 16),
        "east": (7, 6, 9, 16)
    })
    
    leverTemplates = numpy.array([
        rotateTemplate(leverTemplate, x=180),
        rotateTemplate(leverTemplate, x=90, y=90),
        rotateTemplate(leverTemplate, x=90, y=270), 
        rotateTemplate(leverTemplate, x=90, y=180),
        rotateTemplate(leverTemplate, x=270, y=180),
        leverTemplate,
        rotateTemplate(leverTemplate, y=90),
        rotateTemplate(leverTemplate, x=180),
        rotateTemplate(leverTemplate, x=180),
        rotateTemplate(leverTemplate, x=90, y=90),
        rotateTemplate(leverTemplate, x=270, y=90),
        rotateTemplate(leverTemplate, x=270),
        rotateTemplate(leverTemplate, x=270, y=180),
        leverTemplate,
        leverTemplate,
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6))
    ])
    
    makeVertices = makeVerticesFromModel([leverBaseTemplates, leverTemplates], 15)
    

class RailBlockRenderer(BlockRenderer):
    renderstate = ChunkCalculator.renderstateAlphaTest

    def __init__(self, *args, **kwargs):
        BlockRenderer.__init__(self, *args, **kwargs)
        self.railTextures = numpy.array([
                                       [(0, 128), (0, 144), (16, 144), (16, 128)],  # east-west
                                       [(0, 128), (16, 128), (16, 144), (0, 144)],  # north-south
                                       [(0, 128), (16, 128), (16, 144), (0, 144)],  # south-ascending
                                       [(0, 128), (16, 128), (16, 144), (0, 144)],  # north-ascending
                                       [(0, 128), (0, 144), (16, 144), (16, 128)],  # east-ascending
                                       [(0, 128), (0, 144), (16, 144), (16, 128)],  # west-ascending

                                       [(0, 112), (0, 128), (16, 128), (16, 112)],  # northeast corner
                                       [(0, 128), (16, 128), (16, 112), (0, 112)],  # southeast corner
                                       [(16, 128), (16, 112), (0, 112), (0, 128)],  # southwest corner
                                       [(16, 112), (0, 112), (0, 128), (16, 128)],  # northwest corner

                                       [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
                                       [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
                                       [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
                                       [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
                                       [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
                                       [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown

                                   ], dtype='float32')

        self.railTextures -= self.materials.blockTextures[self.materials.Rail.ID, 0, 0]
        for mod_mats in self.mod_materials.values():
            self.railTextures -= mod_mats.blockTextures[self.materials.Rail.ID, 0, 0]

    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         r = []
#         for mod_mats in mod_materials.values():
#             r += [block.ID for block in mod_mats.blocksByType["SIMPLE_RAIL"]]
#         return r + [block.ID for block in mats.blocksByType["SIMPLE_RAIL"]]
        return getBlocktypeIDblocksByType("SIMPLE_RAIL", mats, mod_materials)

    railOffsets = numpy.array([
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],

                                  [0, 0, 1, 1],  # south-ascending
                                  [1, 1, 0, 0],  # north-ascending
                                  [1, 0, 0, 1],  # east-ascending
                                  [0, 1, 1, 0],  # west-ascending

                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],

                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 0],

                              ], dtype='float32')

    def makeRailVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        direction = pymclevel.faces.FaceYIncreasing
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield

        bdata = blockData[blockIndices]
        railBlocks = blocks[blockIndices]
        tex = texMap(railBlocks, bdata, pymclevel.faces.FaceYIncreasing)[:, numpy.newaxis, :]

        # disable 'powered' or 'pressed' bit for powered and detector rails
        for mod_mats in self.mod_materials.values():
            bdata[railBlocks != mod_mats.Rail.ID] = bdata[railBlocks != mod_mats.Rail.ID].astype(int) & ~0x8
        bdata[railBlocks != self.materials.Rail.ID] = bdata[railBlocks != self.materials.Rail.ID].astype(int) & ~0x8

        vertexArray = self.makeTemplate(direction, blockIndices)
        if not len(vertexArray):
            return

        vertexArray[_ST] = self.railTextures[bdata]
        vertexArray[_ST] += tex

        vertexArray[_XYZ][..., 1] -= 0.9
        vertexArray[_XYZ][..., 1] += self.railOffsets[bdata]

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]

        vertexArray.view('uint8')[_RGB] *= blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        yield
        self.vertexArrays = [vertexArray]

    makeVertices = makeRailVertices


class LadderBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         r = []
#         for mod_mats in mod_materials.values():
#             for namespace in mod_mats.namespaces:
#                 try:
#                     r += mod_mats[":".join((namespace, "ladder"))].ID
#                 except:
#                     pass
#         return r + [mats["minecraft:ladder"].ID]
        return getBlocktypesIdStrID("ladder", mats, mod_materials)

    ladderOffsets = numpy.array([
                                    [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],
                                    [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],

                                    [(0, -1, 0.9), (0, 0, -0.1), (0, 0, -0.1), (0, -1, 0.9)],  # facing east
                                    [(0, 0, 0.1), (0, -1, -.9), (0, -1, -.9), (0, 0, 0.1)],  # facing west
                                    [(.9, -1, 0), (.9, -1, 0), (-.1, 0, 0), (-.1, 0, 0)],  # north
                                    [(0.1, 0, 0), (0.1, 0, 0), (-.9, -1, 0), (-.9, -1, 0)],  # south

                                ] + [[(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]] * 10, dtype='float32')

    ladderTextures = numpy.array([
                                     [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown
                                     [(0, 192), (0, 208), (16, 208), (16, 192)],  # unknown

                                     [(64, 96), (64, 80), (48, 80), (48, 96), ],  # e
                                     [(48, 80), (48, 96), (64, 96), (64, 80), ],  # w
                                     [(48, 96), (64, 96), (64, 80), (48, 80), ],  # n
                                     [(64, 80), (48, 80), (48, 96), (64, 96), ],  # s

                                 ] + [[(0, 192), (0, 208), (16, 208), (16, 192)]] * 10, dtype='float32')

    def ladderVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = self.getMaterialIndices(blockMaterials)
        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]
        yield
        bdata = blockData[blockIndices]

        vertexArray = self.makeTemplate(pymclevel.faces.FaceYIncreasing, blockIndices)
        if not len(vertexArray):
            return

        vertexArray[_ST] = self.ladderTextures[bdata]
        vertexArray[_XYZ] += self.ladderOffsets[bdata]
        vertexArray.view('uint8')[_RGB] *= blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

        yield
        self.vertexArrays = [vertexArray]

    makeVertices = ladderVertices


class WallSignBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:wall_sign"].ID]
        return getBlocktypesIdStrID("wall_sign", mats, mod_materials)
    
    wallSignTemplate = makeVertexTemplatesFromJsonModel((0, 4.5, 0), (16, 13.5, 2), {
        "down": (0, 11, 18, 13),
        "up": (0, 6, 16, 8),
        "north": (0, 4, 16, 13),
        "south": (0, 4, 16, 13),
        "west": (0, 4, 2, 13),
        "east": (10, 4, 12, 13)
    })
    
    # I don't know how this sytem works and how it should be structured, but this seem to do the job
    wallSignTemplates = numpy.array([
        wallSignTemplate,
        wallSignTemplate,
        rotateTemplate(wallSignTemplate, y=180),
        wallSignTemplate,
        rotateTemplate(wallSignTemplate, y=90),
        rotateTemplate(wallSignTemplate, y=270),
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6))
    ])
    
    makeVertices = makeVerticesFromModel(wallSignTemplates, 7)
    
class StandingSignRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:standing_sign"].ID]
        return getBlocktypesIdStrID("standing_sign", mats, mod_materials)

    signTemplate = makeVertexTemplatesFromJsonModel((0, 7, 7), (16, 16, 9), {
        "down": (0, 14, 16, 16),
        "up": (0, 12, 16, 14),
        "north": (0, 7, 16, 16),
        "south": (0, 7, 16, 16),
        "west": (0, 7, 2, 16),
        "east": (14, 7, 16, 16)
    })
    
    signTemplates = numpy.array([
        signTemplate,
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6))
    ])
    
    postTemplate = makeVertexTemplatesFromJsonModel((7, 0, 7), (9, 7, 9), {
        "down": (7, 0, 9, 6),
        "up": (7, 0, 9, 6),
        "north": (7, 0, 9, 6),
        "south": (7, 0, 9, 6),
        "west": (7, 0, 9, 6),
        "east": (7, 0, 9, 6),
    })
    
    postTemplates = numpy.array([
        postTemplate,
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6))
    ])
    
    makeVertices = makeVerticesFromModel([signTemplates, postTemplates])


class SnowBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:snow_layer"].ID]
        return getBlocktypesIdStrID("snow_layer", mats, mod_materials)

    def makeSnowVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        #snowIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):

            if direction != pymclevel.faces.FaceYIncreasing:
                blockIndices = materialIndices & exposedFaceIndices
            else:
                blockIndices = materialIndices

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], 0)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights

            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.875

            if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
                vertexArray[_XYZ][..., 2:4, 1] -= 0.875
                vertexArray[_ST][..., 2:4, 1] += 14

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeSnowVertices


class CarpetBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:carpet"].ID, mats["minecraft:waterlily"].ID] #Separate before implementing layers
        return getBlocktypesIdStrID("carpet", mats, mod_materials) + getBlocktypesIdStrID("waterlily", mats, mod_materials)

    def makeCarpetVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        #snowIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):

            if direction != pymclevel.faces.FaceYIncreasing:
                blockIndices = materialIndices & exposedFaceIndices
            else:
                blockIndices = materialIndices

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], 0)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights

            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.937

            if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
                vertexArray[_XYZ][..., 2:4, 1] -= 0.937
                vertexArray[_ST][..., 2:4, 1] += 15

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeCarpetVertices


class CactusBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:cactus"].ID]
        return getBlocktypesIdStrID("cactus", mats, mod_materials)

    def makeCactusVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):

            blockIndices = materialIndices
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], direction)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights

            if direction == pymclevel.faces.FaceXIncreasing:
                vertexArray[_XYZ][..., 0] -= 0.063
            if direction == pymclevel.faces.FaceXDecreasing:
                vertexArray[_XYZ][..., 0] += 0.063
            if direction == pymclevel.faces.FaceZIncreasing:
                vertexArray[_XYZ][..., 2] -= 0.063
            if direction == pymclevel.faces.FaceZDecreasing:
                vertexArray[_XYZ][..., 2] += 0.063

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeCactusVertices


class PaneBlockRenderer(BlockRenderer):  #Basic no thickness panes, add more faces to widen.
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [block.ID for block in mats.blocksByType["SOLID_PANE"]]
        return getBlocktypeIDblocksByType("SOLID_PANE", mats, mod_materials)

    def makePaneVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):

            blockIndices = materialIndices
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue
            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], direction)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights

            if direction == pymclevel.faces.FaceXIncreasing:
                vertexArray[_XYZ][..., 0] -= 0.5
            if direction == pymclevel.faces.FaceXDecreasing:
                vertexArray[_XYZ][..., 0] += 0.5
            if direction == pymclevel.faces.FaceZIncreasing:
                vertexArray[_XYZ][..., 2] -= 0.5
            if direction == pymclevel.faces.FaceZDecreasing:
                vertexArray[_XYZ][..., 2] += 0.5

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makePaneVertices


class PlateBlockRenderer(BlockRenderer):  #suggestions to make this the proper shape is appreciated.
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [block.ID for block in mats.blocksByType["PRESSURE_PLATE"]]
        return getBlocktypeIDblocksByType("PRESSURE_PLATE", mats, mod_materials)

    def makePlateVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):

            blockIndices = materialIndices
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], 0)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights
            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.937
            if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
                vertexArray[_XYZ][..., 2:4, 1] -= 0.937
                vertexArray[_ST][..., 2:4, 1] += 15

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makePlateVertices


class EnchantingBlockRenderer(
    BlockRenderer):  #Note: Enderportal frame side sprite has been lowered 1 pixel to use this renderer, will need separate renderer for eye.
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:enchanting_table"].ID, mats["minecraft:end_portal_frame"].ID]
        return getBlocktypesIdStrID("enchanting_table", mats, mod_materials) + getBlocktypesIdStrID("end_portal_frame", mats, mod_materials)

    def makeEnchantingVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):
            if direction != pymclevel.faces.FaceYIncreasing:
                blockIndices = materialIndices & exposedFaceIndices
            else:
                blockIndices = materialIndices

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], direction)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights
            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.25

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeEnchantingVertices


class DaylightBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:daylight_detector"].ID, mats.DaylightSensorOn.ID]
        return getBlocktypesIdStrID("daylight_detector", mats, mod_materials) + [mats.DaylightSensorOn.ID]

    def makeDaylightVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):
            if direction != pymclevel.faces.FaceYIncreasing:
                blockIndices = materialIndices & exposedFaceIndices
            else:
                blockIndices = materialIndices

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], direction)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights
            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.625
            if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
                vertexArray[_XYZ][..., 2:4, 1] -= 0.625
                vertexArray[_ST][..., 2:4, 1] += 10

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeDaylightVertices


class BedBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         for modid, mod_mats in mod_materials.items():
#             # Try to find the block in the materials 'namespaces'.
#             r = None
#             for namespace in mod_mats.namespaces:
#                 try:
#                     r = mod_mats[":".join((namespace, "bed"))]
#                 except KeyError:
#                     pass
#                 if r:
#                     break
#             return r.ID
#         return [mats["minecraft:bed"].ID]
        return getBlocktypesIdStrID("bed", mats, mod_materials)

    def makeBedVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):
            if direction != pymclevel.faces.FaceYIncreasing:
                blockIndices = materialIndices & exposedFaceIndices
            else:
                blockIndices = materialIndices

            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], direction)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights
            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.438

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeBedVertices


class CakeBlockRenderer(BlockRenderer):  #Only shows whole cakes
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:cake"].ID]
        return getBlocktypesIdStrID("cake", mats, mod_materials)

    def makeCakeVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):

            blockIndices = materialIndices
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], direction)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights

            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.5
            if direction == pymclevel.faces.FaceXIncreasing:
                vertexArray[_XYZ][..., 0] -= 0.063
            if direction == pymclevel.faces.FaceXDecreasing:
                vertexArray[_XYZ][..., 0] += 0.063
            if direction == pymclevel.faces.FaceZIncreasing:
                vertexArray[_XYZ][..., 2] -= 0.063
            if direction == pymclevel.faces.FaceZDecreasing:
                vertexArray[_XYZ][..., 2] += 0.063

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeCakeVertices


class RepeaterBlockRenderer(BlockRenderer):  #Sticks would be nice
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [block.ID for block in mats.blocksByType["THINSLICE"]]
        return getBlocktypeIDblocksByType("THINSLICE", mats, mod_materials)

    def makeRepeaterVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
        append = arrays.append
        yield
        for direction, exposedFaceIndices in enumerate(facingBlockIndices):

            blockIndices = materialIndices
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            lights = facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
            vertexArray = self.makeTemplate(direction, blockIndices)
            if not len(vertexArray):
                continue

            vertexArray[_ST] += texMap(blocks[blockIndices], blockData[blockIndices], direction)[:, numpy.newaxis, 0:2]
            vertexArray.view('uint8')[_RGB] *= lights
            if direction == pymclevel.faces.FaceYIncreasing:
                vertexArray[_XYZ][..., 1] -= 0.875

            if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
                vertexArray[_XYZ][..., 2:4, 1] -= 0.875
                vertexArray[_ST][..., 2:4, 1] += 14

            append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeRepeaterVertices


class RedstoneBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [mats["minecraft:redstone_wire"].ID]
        return getBlocktypesIdStrID("redstone_wire", mats, mod_materials)

    def redstoneVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield
        vertexArray = self.makeTemplate(pymclevel.faces.FaceYIncreasing, blockIndices)
        if not len(vertexArray):
            return

        vertexArray[_ST] += self.materials.blockTextures[55, 0, 0]
        vertexArray[_XYZ][..., 1] -= 0.9

        bdata = blockData[blockIndices]

        bdata <<= 3
        # bdata &= 0xe0
        bdata[bdata > 0] |= 0x80

        vertexArray.view('uint8')[_RGBA][..., 0] = bdata[..., numpy.newaxis]
        vertexArray.view('uint8')[_RGBA][..., 0:3] = vertexArray.view('uint8')[_RGBA][..., 0:3] * [1, 0, 0]

        yield
        self.vertexArrays = [vertexArray]

    makeVertices = redstoneVertices


# button, floor plate, door -> 1-cube features

class DoorRenderer(BlockRenderer):

    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         cls.blocktypes = [block.ID for block in mats.blocksByType["DOOR"]]
#         return cls.blocktypes
        cls.blocktypes =  getBlocktypeIDblocksByType("DOOR", mats, mod_materials)
        return cls.blocktypes

    doorTemplate = makeVertexTemplatesFromJsonModel(
        (0, 0, 0), (3, 16, 16),
        {
            "down": (13, 0, 16, 16),
            # TODO handle faces that should not appear
            "up": (13, 0, 16, 16),
            "north": (3, 0, 0, 16),
            "south": (0, 0, 3, 16),
            "west": (0, 0, 16, 16),
            "east": (16, 0, 0, 16)
        }
    )

    doorRHTemplate = makeVertexTemplatesFromJsonModel(
        (0, 0, 0), (3, 16, 16),
        {
            "down": (13, 0, 16, 16),
            # TODO handle faces that should not appear
            "up": (13, 0, 16, 16),
            "north": (3, 0, 0, 16),
            "south": (0, 0, 3, 16),
            "west": (16, 0, 0, 16),
            "east": (0, 0, 16, 16)
        }
    )

    doorTemplates = numpy.array([
        # lower hinge left
        doorTemplate,
        rotateTemplate(doorTemplate, y=90),
        rotateTemplate(doorTemplate, y=180),
        rotateTemplate(doorTemplate, y=270),
        rotateTemplate(doorRHTemplate, y=90),
        rotateTemplate(doorRHTemplate, y=180),
        rotateTemplate(doorRHTemplate, y=270),
        doorRHTemplate,
        # upper hinge left
        doorTemplate,
        rotateTemplate(doorTemplate, y=90),
        rotateTemplate(doorTemplate, y=180),
        rotateTemplate(doorTemplate, y=270),
        rotateTemplate(doorRHTemplate, y=90),
        rotateTemplate(doorRHTemplate, y=180),
        rotateTemplate(doorRHTemplate, y=270),
        doorRHTemplate,
        # lower hinge right
        doorRHTemplate,
        rotateTemplate(doorRHTemplate, y=90),
        rotateTemplate(doorRHTemplate, y=180),
        rotateTemplate(doorRHTemplate, y=270),
        rotateTemplate(doorTemplate, y=270),
        doorTemplate,
        rotateTemplate(doorTemplate, y=90),
        rotateTemplate(doorTemplate, y=180),
        # upper hinge right
        doorRHTemplate,
        rotateTemplate(doorRHTemplate, y=90),
        rotateTemplate(doorRHTemplate, y=180),
        rotateTemplate(doorRHTemplate, y=270),
        rotateTemplate(doorTemplate, y=270),
        doorTemplate,
        rotateTemplate(doorTemplate, y=90),
        rotateTemplate(doorTemplate, y=180),
    ])

    makeVertices = makeVerticesFromModel(doorTemplates, 31)

class ButtonRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [a.ID for a in mats.blocksByType["BUTTON"]]
        return getBlocktypeIDblocksByType("BUTTON", mats, mod_materials)

    buttonTemplate = makeVertexTemplatesFromJsonModel((5, 0, 6), (11, 2, 10), {
        "down": (5, 6, 11, 10),
        "up": (5, 10, 11, 6),
        "north": (5, 14, 11, 16),
        "south": (5, 14, 11, 16),
        "west": (6, 14, 10, 16),
        "east": (6, 14, 10, 16)
    })

    buttonTemplatePressed = makeVertexTemplatesFromJsonModel((5, 0, 6), (11, 1, 10), {
        "down": (5, 6, 11, 10),
        "up": (5, 10, 11, 6),
        "north": (5, 15, 11, 16),
        "south": (5, 15, 11, 16),
        "west": (6, 15, 10, 16),
        "east": (6, 15, 10, 16)
    })

    buttonTemplates = numpy.array([
        rotateTemplate(buttonTemplate, 180, 0),
        rotateTemplate(buttonTemplate, 90, 90),
        rotateTemplate(buttonTemplate, 90, 270),
        rotateTemplate(buttonTemplate, 90, 180),
        rotateTemplate(buttonTemplate, 90, 0),
        buttonTemplate,
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6)),
        rotateTemplate(buttonTemplatePressed, 180, 0),
        rotateTemplate(buttonTemplatePressed, 90, 90),
        rotateTemplate(buttonTemplatePressed, 90, 270),
        rotateTemplate(buttonTemplatePressed, 90, 180),
        rotateTemplate(buttonTemplatePressed, 90, 0),
        buttonTemplatePressed,
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6)),
    ])

    makeVertices = makeVerticesFromModel(buttonTemplates, 15)

class TrapDoorRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [a.ID for a in mats.blocksByType["TRAPDOOR"]]
        return getBlocktypeIDblocksByType("TRAPDOOR", mats, mod_materials)

    openTemplate = makeVertexTemplatesFromJsonModel((0, 0, 13), (16, 16, 16), {
        "down": (0, 13, 16, 16),
        "up": (0, 16, 16, 13),
        "north": (0, 0, 16, 16),
        "south": (0, 0, 16, 16),
        "west": (16, 0, 13, 16),
        "east": (13, 0, 16, 16)
    })

    topTemplate = makeVertexTemplatesFromJsonModel((0, 13, 0), (16, 16, 16), {
        "down": (0, 0, 16, 16),
        "up": (0, 0, 16, 16),
        "north": (0, 16, 16, 13),
        "south": (0, 16, 16, 13),
        "west": (0, 16, 16, 13),
        "east": (0, 16, 16, 13)
    })

    bottomTemplate = makeVertexTemplatesFromJsonModel((0, 0, 0), (16, 3, 16), {
        "down": (0, 0, 16, 16),
        "up": (0, 0, 16, 16),
        "north": (0, 16, 16, 13),
        "south": (0, 16, 16, 13),
        "west": (0, 16, 16, 13),
        "east": (0, 16, 16, 13)
    })

    trapDoorTemplates = numpy.array([
        bottomTemplate,
        bottomTemplate,
        bottomTemplate,
        bottomTemplate,
        openTemplate,
        rotateTemplate(openTemplate, y=180),
        rotateTemplate(openTemplate, y=270),
        rotateTemplate(openTemplate, y=90),
        topTemplate,
        topTemplate,
        topTemplate,
        topTemplate,
        openTemplate,
        rotateTemplate(openTemplate, y=180),
        rotateTemplate(openTemplate, y=270),
        rotateTemplate(openTemplate, y=90),
    ])

    makeVertices = makeVerticesFromModel(trapDoorTemplates, 15)


class FenceBlockRenderer(BlockRenderer):
#     def __init__(self, *args, **kwargs):
#         BlockRenderer.__init__(self, *args, **kwargs)
#         self.blocktypes = [block.ID for block in self.materials.blocksByType["FENCE"]]

    fenceTemplates = makeVertexTemplates(3 / 8., 0, 3 / 8., 5 / 8., 1, 5 / 8.)

    makeVertices = makeVerticesFromModel(fenceTemplates)

    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         if mats.name == "Pocket":
#             cls.blocktypes = cls.blocktypes_pocket
#         else:
#             cls.blocktypes = cls.blocktypes_alpha
#         return cls.blocktypes
#         return [block.ID for block in mats.blocksByType["FENCE"]]
        return getBlocktypeIDblocksByType("FENCE", mats, mod_materials)


class FenceGateBlockRenderer(BlockRenderer):
    
    closedFenceTemplates = numpy.array([
        makeVertexTemplates(0, 0, 3 / 8., 1, .8, 5 / 8.),
        makeVertexTemplates(3 / 8., 0, 0, 5 / 8., .8, 1)])

    openFenceTemplates = numpy.array([
        [makeVertexTemplates(0, 0, 3 / 8., 1 / 8., .8, 1),
         makeVertexTemplates(7 / 8., 0, 3 / 8., 1, .8, 1)],
        [makeVertexTemplates(0, 0, 0, 5 / 8., .8, 1 / 8.),
         makeVertexTemplates(0, 0, 7 / 8., 5 / 8., .8, 1)],
        [makeVertexTemplates(0, 0, 0, 1 / 8., .8, 5 / 8.),
         makeVertexTemplates(7 / 8., 0, 0, 1, .8, 5 / 8.)],
        [makeVertexTemplates(3 / 8., 0, 0, 1, .8, 1 / 8.),
         makeVertexTemplates(3 / 8., 0, 7 / 8., 1, .8, 1)]])
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [a.ID for a in mats.AllStairs]
        # Stair types renderer ?
        return getBlocktypesAttribute("AllStairs", mats, mod_materials)

    def fenceGateVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        fenceMask = self.getMaterialIndices(blockMaterials)
        closedGateMask = fenceMask.copy()
        closedGateMask[blockData & 4 == 4] = 0
        openGateMask = fenceMask.copy()
        openGateMask[blockData & 4 == 0] = 0
        closedGateIndices = closedGateMask.nonzero()
        openGateIndices = openGateMask.nonzero()

        closedGateData = blockData[closedGateMask]
        closedGateData &= 1

        openGateData = blockData[openGateMask]
        openGateData &= 3

        yield

        # closed gate
        vertexArray = numpy.zeros((len(closedGateIndices[0]), 6, 4, 6), dtype='float32')
        for indicies in xrange(3):
            dimension = (0, 2, 1)[indicies]

            vertexArray[..., indicies] = closedGateIndices[dimension][:, numpy.newaxis,
                                         numpy.newaxis]  # xxx swap z with y using ^

        vertexArray[..., 0:5] += self.closedFenceTemplates[closedGateData][..., 0:5]

        vertexArray[_ST] += texMap(blocks[closedGateIndices], 0)[..., numpy.newaxis, :]

        vertexArray.view('uint8')[_RGB] = self.closedFenceTemplates[closedGateData][..., 5][..., numpy.newaxis]
        vertexArray.view('uint8')[_A] = 0xFF
        vertexArray.view('uint8')[_RGB] *= areaBlockLights[1:-1, 1:-1, 1:-1][closedGateIndices][
            ..., numpy.newaxis, numpy.newaxis, numpy.newaxis]
        vertexArray.shape = (vertexArray.shape[0] * 6, 4, 6)
        yield
        self.vertexArrays = [vertexArray]
        
        append = self.vertexArrays.append
        # open gate
        for i in xrange(2):
            vertexArray = numpy.zeros((len(openGateIndices[0]), 6, 4, 6), dtype='float32')
            for indicies in xrange(3):
                dimension = (0, 2, 1)[indicies]

                vertexArray[..., indicies] = openGateIndices[dimension][:, numpy.newaxis,
                                             numpy.newaxis]  # xxx swap z with y using ^

            vertexArray[..., 0:5] += self.openFenceTemplates[openGateData, i][..., 0:5]

            vertexArray[_ST] += texMap(blocks[openGateIndices], 0)[..., numpy.newaxis, :]

            vertexArray.view('uint8')[_RGB] = self.openFenceTemplates[openGateData, i] \
                [..., 5][..., numpy.newaxis]
            vertexArray.view('uint8')[_A] = 0xFF
            vertexArray.view('uint8')[_RGB] *= areaBlockLights[1:-1, 1:-1, 1:-1][openGateIndices][
                ..., numpy.newaxis, numpy.newaxis, numpy.newaxis]
            vertexArray.shape = (vertexArray.shape[0] * 6, 4, 6)
            yield
            append(vertexArray)

    makeVertices = fenceGateVertices


class StairBlockRenderer(BlockRenderer):
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
#         return [a.ID for a in mats.AllStairs]
        return getBlocktypesAttribute("AllStairs", mats, mod_materials)

    # South - FaceXIncreasing
    # North - FaceXDecreasing
    # West - FaceZIncreasing
    # East - FaceZDecreasing
    stairTemplates = numpy.array([makeVertexTemplates(**kw) for kw in [
        # South - FaceXIncreasing
        {"xmin": 0.5},
        # North - FaceXDecreasing
        {"xmax": 0.5},
        # West - FaceZIncreasing
        {"zmin": 0.5},
        # East - FaceZDecreasing
        {"zmax": 0.5},
        # Slabtype
        {"ymax": 0.5},
    ]
    ])

    def stairVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        append = arrays.append
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield
        stairBlocks = blocks[materialIndices]
        stairData = blockData[materialIndices]
        stairTop = (stairData >> 2).astype(bool)
        stairData &= 3

        x, z, y = materialIndices.nonzero()

        for _ in ("slab", "step"):
            vertexArray = numpy.zeros((len(x), 6, 4, 6), dtype='float32')
            for i in xrange(3):
                vertexArray[_XYZ][..., i] = (x, y, z)[i][:, numpy.newaxis, numpy.newaxis]

            if _ == "step":
                vertexArray[_XYZST] += self.stairTemplates[4][..., :5]
                vertexArray[_XYZ][..., 1][stairTop] += 0.5
            else:
                vertexArray[_XYZST] += self.stairTemplates[stairData][..., :5]

            vertexArray[_ST] += texMap(stairBlocks, 0)[..., numpy.newaxis, :]

            vertexArray.view('uint8')[_RGB] = self.stairTemplates[4][numpy.newaxis, ..., 5, numpy.newaxis]
            vertexArray.view('uint8')[_RGB] *= 0xf
            vertexArray.view('uint8')[_A] = 0xff

            vertexArray.shape = (len(x) * 6, 4, 6)
            yield
            append(vertexArray)
        self.vertexArrays = arrays

    makeVertices = stairVertices


class VineBlockRenderer(BlockRenderer):
    SouthBit = 1  #FaceZIncreasing
    WestBit = 2  #FaceXDecreasing
    NorthBit = 4  #FaceZDecreasing
    EastBit = 8  #FaceXIncreasing

    renderstate = ChunkCalculator.renderstateVines

    def __init__(self, *args, **kwargs):
        BlockRenderer.__init__(self, *args, **kwargs)
#         self.blocktypes = [self.materials["minecraft:vine"].ID]
        self.blocktypes = getBlocktypesIdStrID("vine", self.materials, self.mod_materials)

    def vineFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight,
                         facingBlockLight, texMap):

        bdata = blockData[blockIndices]
        blockIndices = numpy.array(blockIndices)
        if direction == pymclevel.faces.FaceZIncreasing:
            blockIndices[blockIndices] = (bdata & 1).astype(bool)
        elif direction == pymclevel.faces.FaceXDecreasing:
            blockIndices[blockIndices] = (bdata & 2).astype(bool)
        elif direction == pymclevel.faces.FaceZDecreasing:
            blockIndices[blockIndices] = (bdata & 4).astype(bool)
        elif direction == pymclevel.faces.FaceXIncreasing:
            blockIndices[blockIndices] = (bdata & 8).astype(bool)
        else:
            return []
        vertexArray = self.makeTemplate(direction, blockIndices)
        if not len(vertexArray):
            return vertexArray

        vertexArray[_ST] += texMap(self.blocktypes[0], [0], direction)[:, numpy.newaxis, 0:2]

        lights = blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        vertexArray.view('uint8')[_RGB] *= lights

        vertexArray.view('uint8')[_RGB] = vertexArray.view('uint8')[_RGB].astype(float) * LeafBlockRenderer.leafColor

        if direction == pymclevel.faces.FaceZIncreasing:
            vertexArray[_XYZ][..., 2] -= 0.0625
        if direction == pymclevel.faces.FaceXDecreasing:
            vertexArray[_XYZ][..., 0] += 0.0625
        if direction == pymclevel.faces.FaceZDecreasing:
            vertexArray[_XYZ][..., 2] += 0.0625
        if direction == pymclevel.faces.FaceXIncreasing:
            vertexArray[_XYZ][..., 0] -= 0.0625

        return vertexArray

    makeFaceVertices = vineFaceVertices


class SlabBlockRenderer(BlockRenderer):
    def __init__(self, *args, **kwargs):
        BlockRenderer.__init__(self, *args, **kwargs)
#         materials = self.materials
# #         self.blocktypes = [materials["minecraft:wooden_slab"].ID,
# #                   materials["minecraft:stone_slab"].ID,
# #                   materials["minecraft:stone_slab2"].ID,
# #                   materials["minecraft:purpur_slab"].ID]
# #         print "self.blocktypes", self.blocktypes
# #         print "self.materials.AllSlabs", list(set(a.ID for a in self.materials.AllSlabs if "double" not in a.name.lower()))
# #         print list(set(a for a in self.materials.AllSlabs if "double" not in a.name.lower()))
#         self.blocktypes = blocktypes = []
#         for mats in getattr(self.chunkCalculator, "mod_materials", {}).values():
#             print "****** mats", mats
#             blocktypes += list(set(a.ID for a in mats.AllSlabs if "double" not in a.name.lower()))
#         blocktypes += list(set(a.ID for a in materials.AllSlabs if "double" not in a.name.lower()))

        self.blocktypes = getBlocktypesAttribute("AllSlabs", self.materials, self.mod_materials, "double", False)

    def slabFaceVertices(self, direction, blockIndices, facingBlockLight, blocks, blockData, blockLight,
                         areaBlockLights, texMap):

        lights = areaBlockLights[blockIndices][..., numpy.newaxis, numpy.newaxis]
        bdata = blockData[blockIndices]
        top = (bdata >> 3).astype(bool)
        bdata &= 7

        vertexArray = self.makeTemplate(direction, blockIndices)
        if not len(vertexArray):
            return vertexArray

        vertexArray[_ST] += texMap(blocks[blockIndices], bdata, direction)[:, numpy.newaxis, 0:2]
        vertexArray.view('uint8')[_RGB] *= lights

        if direction == pymclevel.faces.FaceYIncreasing:
            vertexArray[_XYZ][..., 1] -= 0.5

        if direction != pymclevel.faces.FaceYIncreasing and direction != pymclevel.faces.FaceYDecreasing:
            vertexArray[_XYZ][..., 2:4, 1] -= 0.5
            vertexArray[_ST][..., 2:4, 1] += 8

        vertexArray[_XYZ][..., 1][top] += 0.5

        return vertexArray

    makeFaceVertices = slabFaceVertices


# 1.9 renderer's
class EndRodRenderer(BlockRenderer):
    def __init__(self, *args, **kwargs):
        BlockRenderer.__init__(self, *args, **kwargs)
#         self.blocktypes = [self.materials["minecraft:end_rod"].ID]
        self.blocktypes = getBlocktypesIdStrID("end_rod", self.materials, self.mod_materials)

    rodTemplate = makeVertexTemplatesFromJsonModel((7, 1, 7), (9, 16, 9), {
        "down": (4, 2, 2, 0),
        "up": (2, 0, 4, 2),
        "north": (0, 0, 2, 15),
        "south": (0, 0, 2, 15),
        "west": (0, 0, 2, 15),
        "east": (0, 0, 2, 15)
    })

    rodTemplates = numpy.array([
        rotateTemplate(rodTemplate, x=180),
        rodTemplate,
        rotateTemplate(rodTemplate, x=90),
        rotateTemplate(rodTemplate, y=180, x=90),
        rotateTemplate(rodTemplate, y=270, x=90),
        rotateTemplate(rodTemplate, y=90, x=90),
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6))
    ])

    handleTemplate = makeVertexTemplatesFromJsonModel((6, 0, 6), (10, 1, 10), {
        "down": (6, 6, 2, 2),
        "up": (2, 2, 6, 6),
        "north": (2, 6, 6, 7),
        "south": (2, 6, 6, 7),
        "west": (2, 6, 6, 7),
        "east": (2, 6, 6, 7)
    })

    handleTemplates = numpy.array([
        rotateTemplate(handleTemplate, x=180),
        handleTemplate,
        rotateTemplate(handleTemplate, x=90),
        rotateTemplate(handleTemplate, y=180, x=90),
        rotateTemplate(handleTemplate, y=270, x=90),
        rotateTemplate(handleTemplate, y=90, x=90),
        numpy.zeros((6, 4, 6)), numpy.zeros((6, 4, 6))
    ])

    makeVertices = makeVerticesFromModel([rodTemplates, handleTemplates], 7)


# This renderer defines internal ID and initializes blocktypes when instanciated.
# Has to be reworked...
class WaterBlockRenderer(BlockRenderer):
    renderstate = ChunkCalculator.renderstateWater

    def __init__(self, *args, **kwargs):
        BlockRenderer.__init__(self, *args, **kwargs)
        materials = self.materials
        self.waterID = materials["minecraft:water"].ID
        self.blocktypes = [materials["minecraft:flowing_water"].ID, self.waterID]

    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
        cls.waterID = mats["minecraft:water"].ID
#         return [mats["minecraft:flowing_water"].ID, cls.waterID]
        return getBlocktypesIdStrID("flowing_water", mats, mod_materials) + getBlocktypesIdStrID("water", mats, mod_materials)

    def waterFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight,
                          facingBlockLight, texMap):
        blockIndices = blockIndices & exposedFaceIndices
        vertexArray = self.makeTemplate(direction, blockIndices)
        vertexArray[_ST] += texMap(self.waterID, 0, 0)[numpy.newaxis, numpy.newaxis]
        vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        return vertexArray

    makeFaceVertices = waterFaceVertices


# This renderer defines internal ID.
# Has to be reworked...
class IceBlockRenderer(BlockRenderer):
    renderstate = ChunkCalculator.renderstateIce
    
    @classmethod
    def getBlocktypes(cls, mats, mod_materials={}):
        cls.iceID = mats["minecraft:ice"].ID
        return getBlocktypesIdStrID("ice", mats, mod_materials)

    def iceFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight,
                        facingBlockLight, texMap):
        blockIndices = blockIndices & exposedFaceIndices
        vertexArray = self.makeTemplate(direction, blockIndices)
        vertexArray[_ST] += texMap(self.iceID, 0, 0)[numpy.newaxis, numpy.newaxis]
        vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        return vertexArray

    makeFaceVertices = iceFaceVertices

from glutils import DisplayList


class MCRenderer(object):
    isPreviewer = False

    def __init__(self, level=None, alpha=1.0):
        self.render = True
        self.origin = (0, 0, 0)
        self.rotation = 0

        self.bufferUsage = 0

        self.invalidChunkQueue = deque()
        self._chunkWorker = None
        self.chunkRenderers = {}
        self.loadableChunkMarkers = DisplayList()
        self.visibleLayers = set(Layer.AllLayers)

        self.masterLists = None

        alpha *= 255
        self.alpha = (int(alpha) & 0xff)

        self.chunkStartTime = datetime.now()
        self.oldChunkStartTime = self.chunkStartTime

        self.oldPosition = None

        self.chunkSamples = [timedelta(0, 0, 0)] * 15

        self.chunkIterator = None

        config.settings.fastLeaves.addObserver(self)

        config.settings.roughGraphics.addObserver(self)
        config.settings.showHiddenOres.addObserver(self)
        config.settings.vertexBufferLimit.addObserver(self)

        config.settings.drawEntities.addObserver(self)
        config.settings.drawTileEntities.addObserver(self)
        config.settings.drawTileTicks.addObserver(self)
        config.settings.drawUnpopulatedChunks.addObserver(self, "drawTerrainPopulated")
        config.settings.drawChunkBorders.addObserver(self, "drawChunkBorder")
        config.settings.drawMonsters.addObserver(self)
        config.settings.drawItems.addObserver(self)

        config.settings.showChunkRedraw.addObserver(self, "showRedraw")
        config.settings.spaceHeight.addObserver(self)
        config.settings.targetFPS.addObserver(self, "targetFPS")
        config.settings.maxViewDistance.addObserver(self, "maxViewDistance")

        for ore in config.settings.hiddableOres.get():
            config.settings["showOre{}".format(ore)].addObserver(self, callback=lambda x, id=ore: self.showOre(id, x))
            
        self.level = level 
            
        if self.level.__class__.__name__ in ("FakeLevel", "MCSchematic"):
            self.toggleLayer(False, 'ChunkBorder')
            

    chunkClass = ChunkRenderer
    calculatorClass = ChunkCalculator

    minViewDistance = 2
    maxViewDistance = 32
    
    _viewDistance = 8

    needsRedraw = True

    def toggleLayer(self, val, layer):
        if val:
            self.visibleLayers.add(layer)
        else:
            self.visibleLayers.discard(layer)
        for cr in self.chunkRenderers.itervalues():
            cr.invalidLayers.add(layer)

        self.loadNearbyChunks()

    def layerProperty(layer, default=True):  # @NoSelf
        attr = intern("_draw" + layer)

        def _get(self):
            return getattr(self, attr, default)

        def _set(self, val):
            if val != _get(self):
                setattr(self, attr, val)
                self.toggleLayer(val, layer)

        return property(_get, _set)

    drawEntities = layerProperty(Layer.Entities)
    drawTileEntities = layerProperty(Layer.TileEntities)
    drawTileTicks = layerProperty(Layer.TileTicks)
    drawMonsters = layerProperty(Layer.Monsters)
    drawItems = layerProperty(Layer.Items)
    drawTerrainPopulated = layerProperty(Layer.TerrainPopulated)
    drawChunkBorder = layerProperty(Layer.ChunkBorder)
    
    def inSpace(self):
        if self.level is None:
            return True
        h = self.position[1]
        if self.level.dimNo == 1:
            _2478aq_heot(h)
        return ((h > self.level.Height + self.spaceHeight) or
                (h <= -self.spaceHeight))

    def chunkDistance(self, cpos):
        camx, camy, camz = self.position

        # if the renderer is offset into the world somewhere, adjust for that
        ox, oy, oz = self.origin
        camx -= ox
        camz -= oz

        camcx = int(numpy.floor(camx)) >> 4
        camcz = int(numpy.floor(camz)) >> 4

        cx, cz = cpos

        return max(abs(cx - camcx), abs(cz - camcz))

    overheadMode = False

    def detailLevelForChunk(self, cpos):
        if self.overheadMode:
            return 2
        if self.isPreviewer:
            w, l, h = self.level.bounds.size
            if w + l < 256:
                return 0

        distance = self.chunkDistance(cpos) - self.viewDistance
        if distance > 0 or self.inSpace():
            return 1
        return 0

    def getViewDistance(self):
        return self._viewDistance

    def setViewDistance(self, vd):
        vd = int(vd) & 0xfffe
        vd = min(max(vd, self.minViewDistance), self.maxViewDistance)
        if vd != self._viewDistance:
            self._viewDistance = vd
            self.viewDistanceChanged()

    viewDistance = property(getViewDistance, setViewDistance, None, "View Distance")

    @property
    def effectiveViewDistance(self):
        if self.inSpace():
            return self.viewDistance * 4
        else:
            return self.viewDistance * 2

    def viewDistanceChanged(self):
        self.oldPosition = None  # xxx
        self.discardMasterList()
        self.loadNearbyChunks()
        self.discardChunksOutsideViewDistance()

    maxWorkFactor = 64
    minWorkFactor = 1
    workFactor = 2

    chunkCalculator = None

    _level = None

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        """ this probably warrants creating a new renderer """
        self.stopWork()

        self._level = level
        self.oldPosition = None
        self.position = (0, 0, 0)
        self.chunkCalculator = None

        self.invalidChunkQueue = deque()

        self.discardAllChunks()

        self.loadableChunkMarkers.invalidate()

        if level:
            self.chunkCalculator = self.calculatorClass(self.level)

            self.oldPosition = None
            
        self.loadNearbyChunks()

    position = (0, 0, 0)

    def loadChunksStartingFrom(self, wx, wz, distance=None):  # world position
        if None is self.level:
            return
        if self.level.saving:
            return

        if distance is None:
            d = self.effectiveViewDistance
        else:
            d = distance

        self.chunkIterator = self.iterateChunks(wx, wz, d * 2)

    def iterateChunks(self, x, z, d):
        cx = x >> 4
        cz = z >> 4

        yield (cx, cz)

        step = dir = 1

        while True:
            for i in xrange(step):
                cx += dir
                yield (cx, cz)

            for i in xrange(step):
                cz += dir
                yield (cx, cz)

            step += 1
            if step > d and not self.overheadMode:
                raise StopIteration

            dir = -dir

    chunkIterator = None

    @property
    def chunkWorker(self):
        if self._chunkWorker is None:
            self._chunkWorker = self.makeWorkIterator()
        return self._chunkWorker

    def stopWork(self):
        self._chunkWorker = None

    def discardAllChunks(self):
        self.bufferUsage = 0
        self.forgetAllDisplayLists()
        self.chunkRenderers = {}
        self.oldPosition = None  # xxx force reload

    def discardChunksInBox(self, box):
        self.discardChunks(box.chunkPositions)

    def discardChunksOutsideViewDistance(self):
        if self.overheadMode:
            return

        # print "discardChunksOutsideViewDistance"
        d = self.effectiveViewDistance
        cx = (self.position[0] - self.origin[0]) / 16
        cz = (self.position[2] - self.origin[2]) / 16

        origin = (cx - d, cz - d)
        size = d * 2

        if not len(self.chunkRenderers):
            return
        (ox, oz) = origin
        chunks = numpy.fromiter(self.chunkRenderers.iterkeys(), dtype='i,i', count=len(self.chunkRenderers))
        chunks.dtype = 'int32'
        chunks.shape = len(self.chunkRenderers), 2

        if size:
            outsideChunks = chunks[:, 0] < ox - 1
            outsideChunks |= chunks[:, 0] > ox + size
            outsideChunks |= chunks[:, 1] < oz - 1
            outsideChunks |= chunks[:, 1] > oz + size
            chunks = chunks[outsideChunks]

        self.discardChunks(chunks)

    def discardChunks(self, chunks):
        for cx, cz in chunks:
            self.discardChunk(cx, cz)
        self.oldPosition = None  # xxx force reload

    def discardChunk(self, cx, cz):
        " discards the chunk renderer for this chunk and compresses the chunk "
        if (cx, cz) in self.chunkRenderers:
            self.bufferUsage -= self.chunkRenderers[cx, cz].bufferSize
            self.chunkRenderers[cx, cz].forgetDisplayLists()
            del self.chunkRenderers[cx, cz]

    _fastLeaves = False

    @property
    def fastLeaves(self):
        return self._fastLeaves

    @fastLeaves.setter
    def fastLeaves(self, val):
        if self._fastLeaves != bool(val):
            self.discardAllChunks()

        self._fastLeaves = bool(val)

    _roughGraphics = False

    @property
    def roughGraphics(self):
        return self._roughGraphics

    @roughGraphics.setter
    def roughGraphics(self, val):
        if self._roughGraphics != bool(val):
            self.discardAllChunks()

        self._roughGraphics = bool(val)

    _showHiddenOres = False

    @property
    def showHiddenOres(self):
        return self._showHiddenOres

    @showHiddenOres.setter
    def showHiddenOres(self, val):
        if self._showHiddenOres != bool(val):
            self.discardAllChunks()

        self._showHiddenOres = bool(val)

    def showOre(self, ore, show):
        ChunkCalculator.hiddenOreMaterials[ore] = ore if show else 1
        if self.showHiddenOres:
            self.discardAllChunks()

    def invalidateChunk(self, cx, cz, layers=None):
        " marks the chunk for regenerating vertex data and display lists "
        if (cx, cz) in self.chunkRenderers:

            self.chunkRenderers[(cx, cz)].invalidate(layers)

            self.invalidChunkQueue.append((cx, cz))  # xxx encapsulate

    def invalidateChunksInBox(self, box, layers=None):
        # If the box is at the edge of any chunks, expanding by 1 makes sure the neighboring chunk gets redrawn.
        box = box.expand(1)

        self.invalidateChunks(box.chunkPositions, layers)

    def invalidateEntitiesInBox(self, box):
        self.invalidateChunks(box.chunkPositions, [Layer.Entities])

    def invalidateTileTicksInBox(self, box):
        self.invalidateChunks(box.chunkPositions, [Layer.TileTicks])

    def invalidateChunks(self, chunks, layers=None):
        for (cx, cz) in chunks:
            self.invalidateChunk(cx, cz, layers)

        self.stopWork()
        self.discardMasterList()
        self.loadNearbyChunks()

    def invalidateAllChunks(self, layers=None):
        self.invalidateChunks(self.chunkRenderers.iterkeys(), layers)

    def forgetAllDisplayLists(self):
        for cr in self.chunkRenderers.itervalues():
            cr.forgetDisplayLists()

    def invalidateMasterList(self):
        self.discardMasterList()

    shouldRecreateMasterList = True

    def discardMasterList(self):
        self.shouldRecreateMasterList = True

    @property
    def shouldDrawAll(self):
        box = self.level.bounds
        return self.isPreviewer and box.width + box.length < 256

    distanceToChunkReload = 32.0

    def cameraMovedFarEnough(self):
        if self.shouldDrawAll:
            return False
        if self.oldPosition is None:
            return True

        cPos = self.position
        oldPos = self.oldPosition

        cameraDelta = self.distanceToChunkReload

        return any([abs(x - y) > cameraDelta for x, y in zip(cPos, oldPos)])

    def loadVisibleChunks(self):
        """ loads nearby chunks if the camera has moved beyond a certain distance """

        # print "loadVisibleChunks"
        if self.cameraMovedFarEnough():
            if datetime.now() - self.lastVisibleLoad > timedelta(0, 0.5):
                self.discardChunksOutsideViewDistance()
                self.loadNearbyChunks()

                self.oldPosition = self.position
                self.lastVisibleLoad = datetime.now()

    lastVisibleLoad = datetime.now()

    def loadNearbyChunks(self):
        if None is self.level:
            return
        # print "loadNearbyChunks"
        cameraPos = self.position

        if self.shouldDrawAll:
            self.loadAllChunks()
        else:
            # subtract self.origin to load nearby chunks correctly for preview renderers
            self.loadChunksStartingFrom(int(cameraPos[0]) - self.origin[0], int(cameraPos[2]) - self.origin[2])

    def loadAllChunks(self):
        box = self.level.bounds

        self.loadChunksStartingFrom(box.origin[0] + box.width / 2, box.origin[2] + box.length / 2,
                                    max(box.width, box.length))

    _floorTexture = None

    @property
    def floorTexture(self):
        if self._floorTexture is None:
            self._floorTexture = Texture(self.makeFloorTex)
        return self._floorTexture

    @staticmethod
    def makeFloorTex():
        color0 = (0xff, 0xff, 0xff, 0x22)
        color1 = (0xff, 0xff, 0xff, 0x44)

        img = numpy.array([color0, color1, color1, color0], dtype='uint8')

        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameter(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)

        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, 2, 2, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img)

    def invalidateChunkMarkers(self):
        self.loadableChunkMarkers.invalidate()

    def _drawLoadableChunkMarkers(self):
        if self.level.chunkCount:
            chunkSet = set(self.level.allChunks)

            sizedChunks = chunkMarkers(chunkSet)

            GL.glPushAttrib(GL.GL_FOG_BIT)
            GL.glDisable(GL.GL_FOG)

            GL.glEnable(GL.GL_BLEND)
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPolygonOffset(DepthOffset.ChunkMarkers, DepthOffset.ChunkMarkers)
            GL.glEnable(GL.GL_DEPTH_TEST)

            GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glColor(1.0, 1.0, 1.0, 1.0)

            self.floorTexture.bind()
            for size, chunks in sizedChunks.iteritems():
                if not len(chunks):
                    continue
                chunks = numpy.array(chunks, dtype='float32')

                chunkPosition = numpy.zeros(shape=(chunks.shape[0], 4, 3), dtype='float32')
                chunkPosition[:, :, (0, 2)] = numpy.array(((0, 0), (0, 1), (1, 1), (1, 0)), dtype='float32')
                chunkPosition[:, :, (0, 2)] *= size
                chunkPosition[:, :, (0, 2)] += chunks[:, numpy.newaxis, :]
                chunkPosition *= 16
                GL.glVertexPointer(3, GL.GL_FLOAT, 0, chunkPosition.ravel())
                GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, (chunkPosition[..., (0, 2)] * 16).ravel())
                GL.glDrawArrays(GL.GL_QUADS, 0, len(chunkPosition) * 4)

            GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
            GL.glDisable(GL.GL_TEXTURE_2D)
            GL.glDisable(GL.GL_BLEND)
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
            GL.glPopAttrib()

    def drawLoadableChunkMarkers(self):
        if not self.isPreviewer or isinstance(self.level, pymclevel.MCInfdevOldLevel):
            self.loadableChunkMarkers.call(self._drawLoadableChunkMarkers)

    needsImmediateRedraw = False
    viewingFrustum = None
    if "-debuglists" in sys.argv:
        def createMasterLists(self):
            pass

        def callMasterLists(self):
            for cr in self.chunkRenderers.itervalues():
                cr.debugDraw()
    else:
        def createMasterLists(self):
            if self.shouldRecreateMasterList:
                lists = {}
                chunkLists = defaultdict(list)
                chunksPerFrame = 80
                shouldRecreateAgain = False

                for ch in self.chunkRenderers.itervalues():
                    if chunksPerFrame:
                        if ch.needsRedisplay:
                            chunksPerFrame -= 1
                        ch.makeDisplayLists()
                    else:
                        shouldRecreateAgain = True

                    if ch.renderstateLists:
                        for rs in ch.renderstateLists:
                            chunkLists[rs] += ch.renderstateLists[rs]

                for rs in chunkLists:
                    if len(chunkLists[rs]):
                        lists[rs] = numpy.array(chunkLists[rs], dtype='uint32').ravel()

                self.masterLists = lists
                self.shouldRecreateMasterList = shouldRecreateAgain
                self.needsImmediateRedraw = shouldRecreateAgain

        def callMasterLists(self):
            for renderstate in self.chunkCalculator.renderstates:
                if renderstate not in self.masterLists:
                    continue

                if self.alpha != 0xff and renderstate is not ChunkCalculator.renderstateLowDetail:
                    GL.glEnable(GL.GL_BLEND)
                renderstate.bind()

                GL.glCallLists(self.masterLists[renderstate])

                renderstate.release()
                if self.alpha != 0xff and renderstate is not ChunkCalculator.renderstateLowDetail:
                    GL.glDisable(GL.GL_BLEND)

    errorLimit = 10

    def draw(self):
        self.needsRedraw = False
        if not self.level:
            return
        if not self.chunkCalculator:
            return
        if not self.render:
            return

        if self.level.materials.name in ("Pocket", "Alpha"):
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glScalef(1 / 2., 1 / 2., 1 / 2.)

        with gl.glPushMatrix(GL.GL_MODELVIEW):
            dx, dy, dz = self.origin
            GL.glTranslate(dx, dy, dz)

            GL.glEnable(GL.GL_CULL_FACE)
            GL.glEnable(GL.GL_DEPTH_TEST)

#             print self.level.materials
#             print self.level.materials.terrainTexture
            self.level.materials.terrainTexture.bind()

            # For each mod, bind the texture.
#             for mod in getattr(self.level, "mods", []):
#                 (a.texture.bind() for a in )
            (a.texture.bind() for a in getattr(self.level, "mod_materials", {}).values() if getattr(a, "texture"))

            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

            offset = DepthOffset.PreviewRenderer if self.isPreviewer else DepthOffset.Renderer
            GL.glPolygonOffset(offset, offset)
            GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)

            self.createMasterLists()
            try:
                self.callMasterLists()

            except GL.GLError, e:
                if self.errorLimit:
                    self.errorLimit -= 1
                    traceback.print_exc()
                    print e

            GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
                
            GL.glDisable(GL.GL_CULL_FACE)
            GL.glDisable(GL.GL_DEPTH_TEST)

            GL.glDisable(GL.GL_TEXTURE_2D)
            GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
            self.drawLoadableChunkMarkers()

        if self.level.materials.name in ("Pocket", "Alpha"):
            GL.glMatrixMode(GL.GL_TEXTURE)
            GL.glScalef(2., 2., 2.)

    renderErrorHandled = False

    def addDebugInfo(self, addDebugString):
        addDebugString("BU: {0} MB, ".format(
            self.bufferUsage / 1000000,
        ))

        addDebugString("WQ: {0}, ".format(len(self.invalidChunkQueue)))
        if self.chunkIterator:
            addDebugString("[LR], ")

        addDebugString("CR: {0}, ".format(len(self.chunkRenderers), ))

    def next(self):
        self.chunkWorker.next()

    def makeWorkIterator(self):
        ''' does chunk face and vertex calculation work. returns a generator that can be
        iterated over for smaller work units.'''

        try:
            while True:
                if self.level is None:
                    raise StopIteration

                if len(self.invalidChunkQueue) > 1024:
                    self.invalidChunkQueue.clear()

                if len(self.invalidChunkQueue):
                    c = self.invalidChunkQueue[0]
                    for _ in self.workOnChunk(c):
                        yield
                    self.invalidChunkQueue.popleft()

                elif self.chunkIterator is None:
                    raise StopIteration

                else:
                    c = self.chunkIterator.next()
                    if self.vertexBufferLimit:
                        while self.bufferUsage > (0.9 * (self.vertexBufferLimit << 20)):
                            deadChunk = None
                            deadDistance = self.chunkDistance(c)
                            for cr in self.chunkRenderers.itervalues():
                                dist = self.chunkDistance(cr.chunkPosition)
                                if dist > deadDistance:
                                    deadChunk = cr
                                    deadDistance = dist

                            if deadChunk is not None:
                                self.discardChunk(*deadChunk.chunkPosition)

                            else:
                                break

                        else:
                            for _ in self.workOnChunk(c):
                                yield

                    else:
                        for _ in self.workOnChunk(c):
                            yield

                yield

        finally:
            self._chunkWorker = None
            if self.chunkIterator:
                self.chunkIterator = None

    vertexBufferLimit = 384

    def getChunkRenderer(self, c):
        if not (c in self.chunkRenderers):
            cr = self.chunkClass(self, c)
        else:
            cr = self.chunkRenderers[c]

        return cr

    def calcFacesForChunkRenderer(self, cr):
        self.bufferUsage -= cr.bufferSize

        calc = cr.calcFaces()
        work = 0
        for _ in calc:
            yield
            work += 1

        self.chunkDone(cr, work)

    def workOnChunk(self, c):
        work = 0

        if self.level.containsChunk(*c):
            cr = self.getChunkRenderer(c)
            if self.viewingFrustum:
                if not self.viewingFrustum.visible1([c[0] * 16 + 8, self.level.Height / 2, c[1] * 16 + 8, 1.0],
                                                    self.level.Height / 2):
                    raise StopIteration

            faceInfoCalculator = self.calcFacesForChunkRenderer(cr)
            try:
                for _ in faceInfoCalculator:
                    work += 1
                    if (work % MCRenderer.workFactor) == 0:
                        yield

                self.invalidateMasterList()

            except Exception as e:
                traceback.print_exc()
                fn = c

                logging.info(u"Skipped chunk {f}: {e}".format(e=e, f=fn))

    redrawChunks = 0

    def chunkDone(self, chunkRenderer, work):
        self.chunkRenderers[chunkRenderer.chunkPosition] = chunkRenderer
        self.bufferUsage += chunkRenderer.bufferSize
        # print "Chunk {0} used {1} work units".format(chunkRenderer.chunkPosition, work)
        if not self.needsRedraw:
            if self.redrawChunks:
                self.redrawChunks -= 1
                if not self.redrawChunks:
                    self.needsRedraw = True

            else:
                self.redrawChunks = 2

        if work > 0:
            self.oldChunkStartTime = self.chunkStartTime
            self.chunkStartTime = datetime.now()
            self.chunkSamples.pop(0)
            self.chunkSamples.append(self.chunkStartTime - self.oldChunkStartTime)


class PreviewRenderer(MCRenderer):
    isPreviewer = True


def rendermain():
    renderer = MCRenderer()

    renderer.level = pymclevel.mclevel.loadWorld("World1")
    renderer.viewDistance = 6
    renderer.detailLevelForChunk = lambda *x: 0
    start = datetime.now()

    renderer.loadVisibleChunks()

    try:
        while True:
            # for i in range(100):
            renderer.next()
    except StopIteration:
        pass
    except Exception, e:
        traceback.print_exc()
        print repr(e)

    duration = datetime.now() - start
    perchunk = duration / len(renderer.chunkRenderers)
    print "Duration: {0} ({1} chunks per second, {2} per chunk, {3} chunks)".format(duration,
                                                                                    1000000.0 / perchunk.microseconds,
                                                                                    perchunk,
                                                                                    len(renderer.chunkRenderers))

    # display.init( (640, 480), OPENGL | DOUBLEBUF )
    from utilities.gl_display_context import GLDisplayContext
    from OpenGL import GLU

    import pygame

    # distance = 4000
    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glLoadIdentity()
    GLU.gluPerspective(35, 640.0 / 480.0, 0.5, 4000.0)
    h = 366

    pos = (0, h, 0)

    look = (0.0001, h - 1, 0.0001)
    up = (0, 1, 0)
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()

    GLU.gluLookAt(pos[0], pos[1], pos[2],
                  look[0], look[1], look[2],
                  up[0], up[1], up[2])

    GL.glClearColor(0.0, 0.0, 0.0, 1.0)

    framestart = datetime.now()
    frames = 200
    for i in xrange(frames):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        renderer.draw()
        pygame.display.flip()

    delta = datetime.now() - framestart
    seconds = delta.seconds + delta.microseconds / 1000000.0
    print "{0} frames in {1} ({2} per frame, {3} FPS)".format(frames, delta, delta / frames, frames / seconds)

    while True:
        evt = pygame.event.poll()
        if evt.type == pygame.MOUSEBUTTONDOWN:
            break
            # time.sleep(3.0)


import traceback

if __name__ == "__main__":
    import cProfile
    cProfile.run("rendermain()", "mcedit.profile")
