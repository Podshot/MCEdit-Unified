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
import os
import itertools
import time

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
from glutils import DisplayList
# import time

class BaseRenderer(object):
    
    def build(self, chunk):
        raise NotImplementedError()
    
    def render(self):
        raise NotImplementedError()
    
class ChunkRenderer(BaseRenderer):
    
    def __init__(self, chunk, y=0):
        self.chunk = None
        self.renderers = []
        self.y = y
        
    def build(self, chunk):
        self.chunk = chunk
        pass
    
    def render(self):
        if not self.chunk:
            raise Exception("Call .build() before .render()!")
        cx, cz = self.chunk.chunkPosition
        GL.glTranslate(cx << 4, self.y, cz << 4)
        
        for renderer in self.renderers:
            renderer.render()
        
        GL.glTranslate(-cx << 4, -self.y, -cz << 4)
    
    def delete(self):
        self.renderers = []
    
class BlockRenderer(BaseRenderer):
    
    def __init__(self):
        self.coordinates = []
        
    def build(self, chunk):
        pass
    
    def render(self):
        pass

class NewBlockRenderer(object):
    blocks = {
              alphaMaterials['minecraft:stone'].ID: {
                                                     'texture': 'terrain.png'
                                                    }
              }
    
    def __init__(self):
        self.coords = {}
        self.chunk = None
    
    def build(self, chunk):
        self.chunk = chunk
        #print chunk.chunkPosition
        self.coords = {}
        for block in self.blocks.keys():
            if not self.coords.get(block):
                self.coords[block] = []
            _blocks = numpy.where(chunk.Blocks == block)
            for count, item in enumerate(_blocks[0]):
                self.coords[block].append((item, _blocks[2][count], _blocks[1][count]))
        if self.coords[1]:
            print "rebuilding.."
            print _blocks
            
        #print self.coords
        
    
    def render(self):
        #cx, cz = self.chunk.chunkPosition
        GL.glPushMatrix()
        if self.coords[1]:
            print self.coords
            #print self.chunk
        #GL.glTranslate(cx << 4, 0, cz << 4)
        for key in self.coords.keys():
            for value in self.coords[key]:
                array = numpy.array([
                                     (value[0], value[1], value[2]),
                                     (value[0], value[1] + 5, value[2])
                                     #(0.0, 0.0, 0.0),
                                     #(0.0, 5.0, 0.0)
                                     ], dtype='float32')
                #GL.glTranslate(value[0], value[1], value[2])
                GL.glColor3f(1.0, 0.0, 0.0);
                #GL.glBegin(GL.GL_LINES)
                
                GL.glVertexPointer(3, GL.GL_FLOAT, 6, (array.ravel()))
                GL.glDrawArrays(GL.GL_LINES, 0, len(array) * 3)
                
                #GL.glVertex3f(value[0], value[1], value[2]);
                #GL.glVertex3f(value[0], value[1] + 5, value[2]);
                #GL.glEnd();
                #GL.glTranslate(-value[0], -value[1], -value[2])
                
        GL.glPopMatrix()
            
        
        pass


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
        #self.visibleLayers = set(Layer.AllLayers)

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
    #calculatorClass = ChunkCalculator

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

    #drawEntities = layerProperty(Layer.Entities)
    #drawTileEntities = layerProperty(Layer.TileEntities)
    #drawTileTicks = layerProperty(Layer.TileTicks)
    #drawMonsters = layerProperty(Layer.Monsters)
    #drawItems = layerProperty(Layer.Items)
    #drawTerrainPopulated = layerProperty(Layer.TerrainPopulated)
    #drawChunkBorder = layerProperty(Layer.ChunkBorder)
    
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
            #self.chunkCalculator = self.calculatorClass(self.level)

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
        #ChunkCalculator.hiddenOreMaterials[ore] = ore if show else 1
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
        pass
    #    self.invalidateChunks(box.chunkPositions, [Layer.Entities])

    def invalidateTileTicksInBox(self, box):
        pass
    #    self.invalidateChunks(box.chunkPositions, [Layer.TileTicks])

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

    #       sizedChunks = chunkMarkers(chunkSet)

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
            #for size, chunks in sizedChunks.iteritems():
            #    if not len(chunks):
            #        continue
            #    chunks = numpy.array(chunks, dtype='float32')

            #    chunkPosition = numpy.zeros(shape=(chunks.shape[0], 4, 3), dtype='float32')
            #    chunkPosition[:, :, (0, 2)] = numpy.array(((0, 0), (0, 1), (1, 1), (1, 0)), dtype='float32')
            #    chunkPosition[:, :, (0, 2)] *= size
            #    chunkPosition[:, :, (0, 2)] += chunks[:, numpy.newaxis, :]
            #    chunkPosition *= 16
            #    GL.glVertexPointer(3, GL.GL_FLOAT, 0, chunkPosition.ravel())
            #    GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, (chunkPosition[..., (0, 2)] * 16).ravel())
            #    GL.glDrawArrays(GL.GL_QUADS, 0, len(chunkPosition) * 4)

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
        pass
            #for renderstate in self.chunkCalculator.renderstates:
            #    if renderstate not in self.masterLists:
            #        continue

                #if self.alpha != 0xff and renderstate is not ChunkCalculator.renderstateLowDetail:
                #    GL.glEnable(GL.GL_BLEND)
            #    renderstate.bind()
                
            #    GL.glCallLists(self.masterLists[renderstate])

            #    renderstate.release()
                #if self.alpha != 0xff and renderstate is not ChunkCalculator.renderstateLowDetail:
                #    GL.glDisable(GL.GL_BLEND)

    errorLimit = 10

    def draw(self):
        self.needsRedraw = False
        if not self.level:
            return
        #if not self.chunkCalculator:
        #    return
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
        pass

    


class PreviewRenderer(MCRenderer):
    isPreviewer = True



