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
from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
from pymclevel.materials import alphaMaterials
import sys
from config import config
# import time


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
                sizedChunks[nextsize].append(o[0])
                for c in others:
                    chunkSet.discard(c)
            else:
                for c in others:
                    sizedChunks[size].append(c)
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
                for br in self.blockRenderers:
                    if br.detailLevels != (0,):
                        blockRenderers.append(br)

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
        return len(self.invalidLayers) == 0


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
    for _ in range(0, x, 90):
        # y -> -z and z -> y
        template[..., (1, 2)] = template[..., (2, 1)]
        template[..., 2] -= 0.5
        template[..., 2] *= -1
        template[..., 2] += 0.5

    for _ in range(0, y, 90):
        # z -> -x and x -> z
        template[..., (0, 2)] = template[..., (2, 0)]
        template[..., 0] -= 0.5
        template[..., 0] *= -1
        template[..., 0] += 0.5
    return template


def makeVerticesFromModel(templates, dataMask=0, debug=False, id=""):
    """
    Returns a function that creates vertex arrays.

    This produces vertex arrays based on the passed
    templates. This doesn't cull any faces based on
    if they are exposed.

    :param templates: list of templates to draw
    :param dataMask:  mask to mask the data
    """
    if type(templates) is list:
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
        if debug:
            print "=== " + id + " ==="
            print "Elements: " + str(elements)
            print "Data: " + str(data)
            print "Block Mask: " + str(blockData[mask])
            print "Supplied Mask: " + str(dataMask)
        for i in range(elements):
            vertexArray = numpy.zeros((len(blockIndices[0]), 6, 4, 6), dtype='float32')
            for indicies in range(3):
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
            self.vertexArrays.append(vertexArray)
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

    for dir in range(len(faceVertexTemplates)):
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
        self.level = level
        self.makeRenderstates(level.materials)

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

    def makeRenderstates(self, materials):
        self.blockRendererClasses = [
            GenericBlockRenderer,
            LeafBlockRenderer,
            PlantBlockRenderer,
            TorchBlockRenderer,
            WaterBlockRenderer,
            SlabBlockRenderer,
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
            materialMap[br.getBlocktypes(materials)] = materialCount
            br.materialIndex = materialCount
            materialCount += 1

        self.exposedMaterialMap = numpy.array(materialMap)
        self.addTransparentMaterials(self.exposedMaterialMap, materialCount)

    def addTransparentMaterials_old(self, mats, materialCount):
        transparentMaterials = [
            alphaMaterials.Glass,
            alphaMaterials.StructureVoid,
            alphaMaterials.GlassPane,
            alphaMaterials.IronBars,
            alphaMaterials.MonsterSpawner,
            alphaMaterials.Vines,
            alphaMaterials.Fire,
            alphaMaterials.Trapdoor,
            alphaMaterials.Lever,
            alphaMaterials.BrewingStand,
            alphaMaterials.Anvil,
            alphaMaterials.Barrier,
            alphaMaterials.StainedGlass,
            alphaMaterials.Hopper,
            alphaMaterials.Cauldron,
            alphaMaterials.WoodenDoor,
            alphaMaterials.IronDoor,
            alphaMaterials.AcaciaDoor,
            alphaMaterials.JungleDoor,
            alphaMaterials.IronTrapdoor,
            alphaMaterials.Button,
            alphaMaterials.WoodenButton,
            alphaMaterials.FenceGate,
            alphaMaterials.SpruceFenceGate,
            alphaMaterials.BirchFenceGate,
            alphaMaterials.JungleFenceGate,
            alphaMaterials.DarkOakFenceGate,
            alphaMaterials.AcaciaFenceGate,
            alphaMaterials.Sign,
            alphaMaterials.StructureVoid
        ]
        for b in transparentMaterials:
            mats[b.ID] = materialCount
            materialCount += 1

    def addTransparentMaterials_new(self, mats, materialCount):
        transparentMaterials = []
        logging.debug("renderer::ChunkCalculator: Dynamically adding transparent materials.")
        for b in self.level.materials:
            if hasattr(b, 'yaml'):
                if b.yaml.get('opacity', 1) < 1:
                    logging.debug("Adding '%s'"%b)
                    transparentMaterials.append(b)
        logging.debug("renderer::ChunkCalculator: Transparent materials added: %s"%len(transparentMaterials))
        for b in transparentMaterials:
            mats[b.ID] = materialCount
            materialCount += 1

#     if __builtins__.get('mcenf_addTransparentMaterials', False):
#         logging.info("Using new ChunkCalculator.addTransparentMaterials")
#         addTransparentMaterials = addTransparentMaterials_new
#     else:
#         addTransparentMaterials = addTransparentMaterials_old
    addTransparentMaterials = addTransparentMaterials_new

    # don't show boundaries between dirt,grass,sand,gravel,or stone.
    # This hiddenOreMaterial definition shall be delayed after the level is loaded, in order to get the exact ones from the game versionned data.
    hiddenOreMaterials = numpy.arange(pymclevel.materials.id_limit, dtype='uint16')
    stoneid = alphaMaterials.Stone.ID
    hiddenOreMaterials[alphaMaterials.Dirt.ID] = stoneid
    hiddenOreMaterials[alphaMaterials.Grass.ID] = stoneid
    hiddenOreMaterials[alphaMaterials.Sand.ID] = stoneid
    hiddenOreMaterials[alphaMaterials.Gravel.ID] = stoneid
    hiddenOreMaterials[alphaMaterials.Netherrack.ID] = stoneid

    roughMaterials = numpy.ones((pymclevel.materials.id_limit,), dtype='uint8')
    roughMaterials[0] = 0
    # Do not pre-load transparent materials, since it is game version dependent.
    # addTransparentMaterials(None, roughMaterials, 2)

    def calcFacesForChunkRenderer(self, cr):
        if 0 == len(cr.invalidLayers):
            #            layers = set(br.layer for br in cr.blockRenderers)
            #            assert set() == cr.visibleLayers.difference(layers)
            return

        lod = cr.detailLevel
        cx, cz = cr.chunkPosition
        level = cr.renderer.level
        try:
            chunk = level.getChunk(cx, cz)
        except Exception, e:
            if "Session lock lost" in e.message:
                yield
                return
            logging.warn(u"Error reading chunk: %s", e)
            yield
            return

        yield
        brs = []
        classes = [
            TileEntityRenderer,
            MonsterRenderer,
            ItemRenderer,
            TileTicksRenderer,
            TerrainPopulatedRenderer,
            ChunkBorderRenderer,
            LowDetailBlockRenderer,
            OverheadBlockRenderer,
        ]
        existingBlockRenderers = dict(((type(b), b) for b in cr.blockRenderers))

        for blockRendererClass in classes:
            if cr.detailLevel not in blockRendererClass.detailLevels:
                continue
            if blockRendererClass.layer not in cr.visibleLayers:
                continue
            if blockRendererClass.layer not in cr.invalidLayers:
                if blockRendererClass in existingBlockRenderers:
                    brs.append(existingBlockRenderers[blockRendererClass])

                continue

            br = blockRendererClass(self)
            br.detailLevel = cr.detailLevel

            for _ in br.makeChunkVertices(chunk):
                yield
            brs.append(br)

        blockRenderers = []

        # Recalculate high detail blocks if needed, otherwise retain the high detail renderers
        if lod == 0 and Layer.Blocks in cr.invalidLayers:
            for _ in self.calcHighDetailFaces(cr, blockRenderers):
                yield
        else:
            blockRenderers.extend(br for br in cr.blockRenderers if type(br) not in classes)

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
                # if not level.chunkIsLoaded(cx+dx,cz+dz):
                #    raise StopIteration
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
        areaBlocks[:1, 1:-1, 1:-1] = neighboringChunks[pymclevel.faces.FaceXDecreasing].Blocks[-1:, :chunkLength,
                                     :chunkHeight]
        areaBlocks[-1:, 1:-1, 1:-1] = neighboringChunks[pymclevel.faces.FaceXIncreasing].Blocks[:1, :chunkLength,
                                      :chunkHeight]
        areaBlocks[1:-1, :1, 1:-1] = neighboringChunks[pymclevel.faces.FaceZDecreasing].Blocks[:chunkWidth, -1:,
                                     :chunkHeight]
        areaBlocks[1:-1, -1:, 1:-1] = neighboringChunks[pymclevel.faces.FaceZIncreasing].Blocks[:chunkWidth, :1,
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

        nc = neighboringChunks[pymclevel.faces.FaceXDecreasing]
        numpy.maximum(nc.SkyLight[-1:, :chunkLength, :chunkHeight],
                      nc.BlockLight[-1:, :chunkLength, :chunkHeight],
                      areaBlockLights[0:1, 1:-1, 1:-1])

        nc = neighboringChunks[pymclevel.faces.FaceXIncreasing]
        numpy.maximum(nc.SkyLight[:1, :chunkLength, :chunkHeight],
                      nc.BlockLight[:1, :chunkLength, :chunkHeight],
                      areaBlockLights[-1:, 1:-1, 1:-1])

        nc = neighboringChunks[pymclevel.faces.FaceZDecreasing]
        numpy.maximum(nc.SkyLight[:chunkWidth, -1:, :chunkHeight],
                      nc.BlockLight[:chunkWidth, -1:, :chunkHeight],
                      areaBlockLights[1:-1, 0:1, 1:-1])

        nc = neighboringChunks[pymclevel.faces.FaceZIncreasing]
        numpy.maximum(nc.SkyLight[:chunkWidth, :1, :chunkHeight],
                      nc.BlockLight[:chunkWidth, :1, :chunkHeight],
                      areaBlockLights[1:-1, -1:, 1:-1])

        minimumLight = 4
        # areaBlockLights[areaBlockLights<minimumLight]=minimumLight
        numpy.clip(areaBlockLights, minimumLight, 16, areaBlockLights)

        return areaBlockLights

    def calcHighDetailFaces(self, cr,
                            blockRenderers):  # ForChunk(self, chunkPosition = (0,0), level = None, alpha = 1.0):
        """ calculate the geometry for a chunk renderer from its blockMats, data,
        and lighting array. fills in the cr's blockRenderers with verts
        for each block facing and material"""

        # chunkBlocks and chunkLights shall be indexed [x,z,y] to follow infdev's convention
        cx, cz = cr.chunkPosition
        level = cr.renderer.level

        chunk = level.getChunk(cx, cz)
        neighboringChunks = self.getNeighboringChunks(chunk)

        areaBlocks = self.getAreaBlocks(chunk, neighboringChunks)
        yield

        areaBlockLights = self.getAreaBlockLights(chunk, neighboringChunks)
        yield

        slabs = areaBlocks == alphaMaterials.StoneSlab.ID  #If someone could combine these, that would be great.
        if slabs.any():
            areaBlockLights[slabs] = areaBlockLights[:, :, 1:][slabs[:, :, :-1]]
        yield

        woodSlabs = areaBlocks == alphaMaterials.OakWoodSlab.ID
        if woodSlabs.any():
            areaBlockLights[woodSlabs] = areaBlockLights[:, :, 1:][woodSlabs[:, :, :-1]]
        yield

        redSlabs = areaBlocks == alphaMaterials.RedSandstoneSlab.ID
        if redSlabs.any():
            areaBlockLights[redSlabs] = areaBlockLights[:, :, 1:][redSlabs[:, :, :-1]]
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

        for y in range(0, chunk.world.Height, 16):
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
                    chunkRenderer):
                yield

    def computeCubeGeometry(self, y, blockRenderers, blocks, blockData, materials, blockMaterials, facingBlockIndices,
                            areaBlockLights, chunkRenderer):
        materialCounts = numpy.bincount(blockMaterials.ravel())

        def texMap(blocks, blockData=0, direction=slice(None)):
            return materials.blockTextures[blocks, blockData, direction]  # xxx slow

        for blockRendererClass in self.blockRendererClasses:
            mi = blockRendererClass.materialIndex
            if mi >= len(materialCounts) or materialCounts[mi] == 0:
                continue

            blockRenderer = blockRendererClass(self)
            blockRenderer.y = y
            blockRenderer.materials = materials
            for _ in blockRenderer.makeVertices(facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights,
                                                texMap):
                yield
            blockRenderers.append(blockRenderer)

            yield

    def makeTemplate(self, direction, blockIndices):
        return self.precomputedVertices[direction][blockIndices]


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


class BlockRenderer(object):
    # vertexArrays = None
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
        pass

    @classmethod
    def getBlocktypes(cls, mats):
        return cls.blocktypes

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
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]

        for (direction, exposedFaceIndices) in enumerate(facingBlockIndices):
            facingBlockLight = areaBlockLights[self.directionOffsets[direction]]
            vertexArray = self.makeFaceVertices(direction, materialIndices, exposedFaceIndices, blocks, blockData,
                                                blockLight, facingBlockLight, texMap)
            yield
            if len(vertexArray):
                arrays.append(vertexArray)
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
        if 0 == len(buf):
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
        if 0 == len(buf):
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
        if len(positions):
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
        for i, ent in enumerate(chunk.TileEntities):
            if i % 10 == 0:
                yield
            if 'x' not in ent:
                continue
            tilePositions.append(pymclevel.TileEntity.pos(ent))
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
        notMonsters = MCEDIT_DEFS.get('notMonsters', self.notMonsters)
        for i, ent in enumerate(chunk.Entities):
            if i % 10 == 0:
                yield
            id = ent["id"].value
            if id in notMonsters:
                continue
            pos = pymclevel.Entity.pos(ent)
            pos[1] += 0.5
            monsterPositions.append(pos)

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


#        entityPositions = []
#        for i, ent in enumerate(chunk.Entities):
#            if i % 10 == 0:
#                yield
#            entityPositions.append(pymclevel.Entity.pos(ent))
#
#        entities = self._computeVertices(entityPositions, (0x88, 0x00, 0x00, 0x66), offset=True, chunkPosition=chunk.chunkPosition)
#        yield
#        self.vertexArrays = [entities]


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
        for i, ent in enumerate(chunk.Entities):
            if i % 10 == 0:
                yield
            # Let get the color from the versionned data, and use the 'old' way as fallback
            color = MCEDIT_DEFS.get(MCEDIT_IDS.get(ent["id"].value), {}).get("mapcolor")
            if color is None:
                color = colorMap.get(ent["id"].value)

            if color is None:
                continue
            pos = pymclevel.Entity.pos(ent)
            noRenderDelta = MCEDIT_DEFS.get('noRenderDelta', ("Painting", "ItemFrame"))
            if ent["id"].value not in noRenderDelta:
                pos[1] += 0.5
            entityPositions.append(pos)
            entityColors.append(color)

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
        if 0 == len(buf):
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
        if 0 == len(buf):
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

        except ValueError, e:
            raise ValueError(str(e.args) + "Chunk shape: {0}".format(blockIndices.shape), sys.exc_info()[-1])

        if nonAirBlocks.any():
            blockTypes = blocks[blockIndices]

            flatcolors = level.materials.flatColors[blockTypes, ch.Data[blockIndices] & 0xf][:, numpy.newaxis, :]
            # flatcolors[:,:,:3] *= (0.6 + (h * (0.4 / float(chunkHeight-1)))) [topBlocks != 0][:, numpy.newaxis, numpy.newaxis]
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
                    grass = theseBlocks == alphaMaterials.Grass.ID
                    vertexArray.view('uint8')[_RGB][grass] = vertexArray.view('uint8')[_RGB][grass].astype(float) * self.grassColor
            yield

            vertexArrays.append(vertexArray)

        self.vertexArrays = vertexArrays

    grassColor = grassColorDefault = [0.39, 0.71, 0.23]  # 62C743

    makeVertices = makeGenericVertices


class LeafBlockRenderer(BlockRenderer):
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["LEAVES"]]

    @property
    def renderstate(self):
        if self.chunkCalculator.fastLeaves:
            return ChunkCalculator.renderstatePlain
        else:
            return ChunkCalculator.renderstateAlphaTest

    def makeLeafVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
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
                    #leaves |= type3

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
            arrays.append(vertexArray)

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
    def getBlocktypes(cls, mats):
        # blocktypes = [6, 37, 38, 39, 40, 59, 83]
        # if mats.name != "Classic": blocktypes += [31, 32]  # shrubs, tall grass
        # if mats.name == "Alpha": blocktypes += [115]  # nether wart
        blocktypes = [b.ID for b in mats if b.type in ("DECORATION_CROSS", "NETHER_WART", "CROPS", "STEM")]

        return blocktypes

    renderstate = ChunkCalculator.renderstateAlphaTest

    def makePlantVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        arrays = []
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield

        theseBlocks = blocks[blockIndices]

        bdata = blockData[blockIndices]
        texes = texMap(blocks[blockIndices], bdata, 0)

        blockLight = areaBlockLights[1:-1, 1:-1, 1:-1]
        lights = blockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]

        colorize = None
        if self.materials.name != "Classic":  #so hacky, someone more competent fix this
            colorize = (theseBlocks == alphaMaterials.TallGrass.ID) & (bdata != 0)
            colorize2 = (theseBlocks == alphaMaterials.TallFlowers.ID) & (bdata != 0) & (
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
            arrays.append(vertexArray)
            yield

        self.vertexArrays = arrays

    makeVertices = makePlantVertices


class TorchBlockRenderer(BlockRenderer):
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["TORCH"]]
    
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
        for direction in range(6):
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
            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeTorchVertices
    
class LeverBlockRenderer(BlockRenderer):
    blocktypes = [alphaMaterials["minecraft:lever"].ID]
    
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
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["SIMPLE_RAIL"]]
    renderstate = ChunkCalculator.renderstateAlphaTest

    railTextures = numpy.array([
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
    railTextures -= alphaMaterials.blockTextures[alphaMaterials.Rail.ID, 0, 0]

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
        bdata[railBlocks != alphaMaterials.Rail.ID] = bdata[railBlocks != alphaMaterials.Rail.ID].astype(int) & ~0x8

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
    blocktypes = [alphaMaterials["minecraft:ladder"].ID]

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
    blocktypes = [alphaMaterials["minecraft:wall_sign"].ID]
    
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
    blocktypes = [alphaMaterials["minecraft:standing_sign"].ID]
    
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
    blocktypes = [alphaMaterials["minecraft:snow_layer"].ID]

    def makeSnowVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        #snowIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeSnowVertices


class CarpetBlockRenderer(BlockRenderer):
    blocktypes = [alphaMaterials["minecraft:carpet"].ID,  #Separate before implementing layers
                  alphaMaterials["minecraft:waterlily"].ID]

    def makeCarpetVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        #snowIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeCarpetVertices


class CactusBlockRenderer(BlockRenderer):
    blocktypes = [alphaMaterials["minecraft:cactus"].ID]

    def makeCactusVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeCactusVertices


class PaneBlockRenderer(BlockRenderer):  #Basic no thickness panes, add more faces to widen.
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["SOLID_PANE"]]

    def makePaneVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makePaneVertices


class PlateBlockRenderer(BlockRenderer):  #suggestions to make this the proper shape is appreciated.
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["PRESSURE_PLATE"]]

    def makePlateVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makePlateVertices


class EnchantingBlockRenderer(
    BlockRenderer):  #Note: Enderportal frame side sprite has been lowered 1 pixel to use this renderer, will need separate renderer for eye.
    blocktypes = [alphaMaterials["minecraft:enchanting_table"].ID,
                  alphaMaterials["minecraft:end_portal_frame"].ID]

    def makeEnchantingVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeEnchantingVertices


class DaylightBlockRenderer(BlockRenderer):
    blocktypes = [alphaMaterials["minecraft:daylight_detector"].ID,
                  alphaMaterials.DaylightSensorOn.ID]

    def makeDaylightVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeDaylightVertices


class BedBlockRenderer(BlockRenderer):
    blocktypes = [alphaMaterials["minecraft:bed"].ID]

    def makeBedVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeBedVertices


class CakeBlockRenderer(BlockRenderer):  #Only shows whole cakes
    blocktypes = [alphaMaterials["minecraft:cake"].ID]

    def makeCakeVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeCakeVertices


class RepeaterBlockRenderer(BlockRenderer):  #Sticks would be nice
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["THINSLICE"]]

    def makeRepeaterVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        materialIndices = self.getMaterialIndices(blockMaterials)
        arrays = []
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

            arrays.append(vertexArray)
            yield
        self.vertexArrays = arrays

    makeVertices = makeRepeaterVertices


class RedstoneBlockRenderer(BlockRenderer):
    blocktypes = [alphaMaterials["minecraft:redstone_wire"].ID]

    def redstoneVertices(self, facingBlockIndices, blocks, blockMaterials, blockData, areaBlockLights, texMap):
        blockIndices = self.getMaterialIndices(blockMaterials)
        yield
        vertexArray = self.makeTemplate(pymclevel.faces.FaceYIncreasing, blockIndices)
        if not len(vertexArray):
            return

        vertexArray[_ST] += alphaMaterials.blockTextures[55, 0, 0]
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
    blocktypes = [alphaMaterials["minecraft:wooden_door"].ID,
                  alphaMaterials["minecraft:iron_door"].ID,
                  alphaMaterials["minecraft:spruce_door"].ID,
                  alphaMaterials["minecraft:birch_door"].ID,
                  alphaMaterials["minecraft:jungle_door"].ID,
                  alphaMaterials["minecraft:acacia_door"].ID,
                  alphaMaterials["minecraft:dark_oak_door"].ID]

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
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["BUTTON"]]

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
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["TRAPDOOR"]]

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
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["FENCE"]]
    
    fenceTemplates = makeVertexTemplates(3 / 8., 0, 3 / 8., 5 / 8., 1, 5 / 8.)

    makeVertices = makeVerticesFromModel(fenceTemplates)


class FenceGateBlockRenderer(BlockRenderer):
    blocktypes = [block.ID for block in alphaMaterials.blocksByType["FENCE_GATE"]]
    
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
        for indicies in range(3):
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

        # open gate
        for i in range(2):
            vertexArray = numpy.zeros((len(openGateIndices[0]), 6, 4, 6), dtype='float32')
            for indicies in range(3):
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
            self.vertexArrays.append(vertexArray)

    makeVertices = fenceGateVertices


class StairBlockRenderer(BlockRenderer):
    @classmethod
    def getBlocktypes(cls, mats):
        return [a.ID for a in mats.AllStairs]

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
        materialIndices = self.getMaterialIndices(blockMaterials)
        yield
        stairBlocks = blocks[materialIndices]
        stairData = blockData[materialIndices]
        stairTop = (stairData >> 2).astype(bool)
        stairData &= 3

        x, z, y = materialIndices.nonzero()

        for _ in ("slab", "step"):
            vertexArray = numpy.zeros((len(x), 6, 4, 6), dtype='float32')
            for i in range(3):
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
            arrays.append(vertexArray)
        self.vertexArrays = arrays

    makeVertices = stairVertices


class VineBlockRenderer(BlockRenderer):
    blocktypes = [alphaMaterials["minecraft:vine"].ID]

    SouthBit = 1  #FaceZIncreasing
    WestBit = 2  #FaceXDecreasing
    NorthBit = 4  #FaceZDecreasing
    EastBit = 8  #FaceXIncreasing

    renderstate = ChunkCalculator.renderstateVines

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
    blocktypes = [alphaMaterials["minecraft:wooden_slab"].ID,
                  alphaMaterials["minecraft:stone_slab"].ID,
                  alphaMaterials["minecraft:stone_slab2"].ID,
                  alphaMaterials["minecraft:purpur_slab"].ID]

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
    blocktypes = [alphaMaterials["minecraft:end_rod"].ID]

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

class WaterBlockRenderer(BlockRenderer):
    waterID = alphaMaterials["minecraft:water"].ID
    blocktypes = [alphaMaterials["minecraft:flowing_water"].ID, waterID]
    renderstate = ChunkCalculator.renderstateWater

    def waterFaceVertices(self, direction, blockIndices, exposedFaceIndices, blocks, blockData, blockLight,
                          facingBlockLight, texMap):
        blockIndices = blockIndices & exposedFaceIndices
        vertexArray = self.makeTemplate(direction, blockIndices)
        vertexArray[_ST] += texMap(self.waterID, 0, 0)[numpy.newaxis, numpy.newaxis]
        vertexArray.view('uint8')[_RGB] *= facingBlockLight[blockIndices][..., numpy.newaxis, numpy.newaxis]
        return vertexArray

    makeFaceVertices = waterFaceVertices


class IceBlockRenderer(BlockRenderer):
    iceID = alphaMaterials["minecraft:ice"].ID
    blocktypes = [iceID]
    renderstate = ChunkCalculator.renderstateIce

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
            
        if self.level.__class__.__name__ in ("FakeLevel","MCSchematic"):
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
            # self.invalidateChunkMarkers()

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
            for i in range(step):
                cx += dir
                yield (cx, cz)

            for i in range(step):
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
        # chunks = numpy.fromiter(self.chunkRenderers.iterkeys(), dtype='int32', count=len(self.chunkRenderers))
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
            # self.chunkRenderers[(cx,cz)].invalidate()
            # self.bufferUsage -= self.chunkRenderers[(cx, cz)].bufferSize

            self.chunkRenderers[(cx, cz)].invalidate(layers)
            # self.bufferUsage += self.chunkRenderers[(cx, cz)].bufferSize

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
            # chunkColor = numpy.zeros(shape=(chunks.shape[0], 4, 4), dtype='float32')
            #            chunkColor[:]= (1, 1, 1, 0.15)
            #
            #            cc = numpy.array(chunks[:,0] + chunks[:,1], dtype='int32')
            #            cc &= 1
            #            coloredChunks = cc > 0
            #            chunkColor[coloredChunks] = (1, 1, 1, 0.28)
            #            chunkColor *= 255
            #            chunkColor = numpy.array(chunkColor, dtype='uint8')
            #
            # GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, 0, chunkColor)
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

            # self.drawCompressedChunkMarkers()

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

                # lists = lists[lists.nonzero()]
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

            self.level.materials.terrainTexture.bind()
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
            # if self.drawLighting:
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
                # if not self.viewingFrustum.visible(numpy.array([[c[0] * 16 + 8, 64, c[1] * 16 + 8, 1.0]]), 64).any():
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

            except Exception, e:
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
    for i in range(frames):
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
import cProfile

if __name__ == "__main__":
    cProfile.run("rendermain()", "mcedit.profile")
