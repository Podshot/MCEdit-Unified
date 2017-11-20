import os
import directories
import numpy
import png
import pymclevel
import functools
from OpenGL import GL
from glutils import DisplayList
from resource_packs import ResourcePackHandler


def drawFace(box, face, type=GL.GL_QUADS):
    x, y, z, = box.origin
    x2, y2, z2 = box.maximum

    if face == pymclevel.faces.FaceXDecreasing:

        faceVertices = numpy.array(
            (x, y2, z2,
             x, y2, z,
             x, y, z,
             x, y, z2,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceXIncreasing:

        faceVertices = numpy.array(
            (x2, y, z2,
             x2, y, z,
             x2, y2, z,
             x2, y2, z2,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceYDecreasing:
        faceVertices = numpy.array(
            (x2, y, z2,
             x, y, z2,
             x, y, z,
             x2, y, z,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceYIncreasing:
        faceVertices = numpy.array(
            (x2, y2, z,
             x, y2, z,
             x, y2, z2,
             x2, y2, z2,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceZDecreasing:
        faceVertices = numpy.array(
            (x, y, z,
             x, y2, z,
             x2, y2, z,
             x2, y, z,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceZIncreasing:
        faceVertices = numpy.array(
            (x2, y, z2,
             x2, y2, z2,
             x, y2, z2,
             x, y, z2,
            ), dtype='f4')

    faceVertices.shape = (4, 3)
    dim = face >> 1
    dims = [0, 1, 2]
    dims.remove(dim)

    texVertices = numpy.array(
        faceVertices[:, dims],
        dtype='f4'
    ).flatten()
    faceVertices.shape = (12,)

    texVertices *= 16
    GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

    GL.glVertexPointer(3, GL.GL_FLOAT, 0, faceVertices)
    GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, texVertices)

    GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glEnable(GL.GL_POLYGON_OFFSET_LINE)

    if type is GL.GL_LINE_STRIP:
        indexes = numpy.array((0, 1, 2, 3, 0), dtype='uint32')
        GL.glDrawElements(type, 5, GL.GL_UNSIGNED_INT, indexes)
    else:
        GL.glDrawArrays(type, 0, 4)
    GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glDisable(GL.GL_POLYGON_OFFSET_LINE)
    GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)


def drawCube(box, cubeType=GL.GL_QUADS, blockType=0, texture=None, textureVertices=None, selectionBox=False):
    """ pass a different cubeType e.g. GL_LINE_STRIP for wireframes """
    x, y, z, = box.origin
    x2, y2, z2 = box.maximum
    dx, dy, dz = x2 - x, y2 - y, z2 - z
    cubeVertices = numpy.array(
        (
            x, y, z,
            x, y2, z,
            x2, y2, z,
            x2, y, z,

            x2, y, z2,
            x2, y2, z2,
            x, y2, z2,
            x, y, z2,

            x2, y, z2,
            x, y, z2,
            x, y, z,
            x2, y, z,

            x2, y2, z,
            x, y2, z,
            x, y2, z2,
            x2, y2, z2,

            x, y2, z2,
            x, y2, z,
            x, y, z,
            x, y, z2,

            x2, y, z2,
            x2, y, z,
            x2, y2, z,
            x2, y2, z2,
        ), dtype='f4')
    if textureVertices is None:
        textureVertices = numpy.array(
            (
                0, -dy * 16,
                0, 0,
                dx * 16, 0,
                dx * 16, -dy * 16,

                dx * 16, -dy * 16,
                dx * 16, 0,
                0, 0,
                0, -dy * 16,

                dx * 16, -dz * 16,
                0, -dz * 16,
                0, 0,
                dx * 16, 0,

                dx * 16, 0,
                0, 0,
                0, -dz * 16,
                dx * 16, -dz * 16,

                dz * 16, 0,
                0, 0,
                0, -dy * 16,
                dz * 16, -dy * 16,

                dz * 16, -dy * 16,
                0, -dy * 16,
                0, 0,
                dz * 16, 0,

            ), dtype='f4')

        textureVertices.shape = (6, 4, 2)

        if selectionBox:
            textureVertices[0:2] += (16 * (x & 15), 16 * (y2 & 15))
            textureVertices[2:4] += (16 * (x & 15), -16 * (z & 15))
            textureVertices[4:6] += (16 * (z & 15), 16 * (y2 & 15))
            textureVertices[:] += 0.5

    GL.glVertexPointer(3, GL.GL_FLOAT, 0, cubeVertices)
    if texture is not None:
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

        texture.bind()
        GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, textureVertices),

    GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glEnable(GL.GL_POLYGON_OFFSET_LINE)

    GL.glDrawArrays(cubeType, 0, 24)
    GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glDisable(GL.GL_POLYGON_OFFSET_LINE)

    if texture is not None:
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisable(GL.GL_TEXTURE_2D)


def drawTerrainCuttingWire(box,
                           c0=(0.75, 0.75, 0.75, 0.4),
                           c1=(1.0, 1.0, 1.0, 1.0)):
    # glDepthMask(False)
    GL.glEnable(GL.GL_DEPTH_TEST)

    GL.glDepthFunc(GL.GL_LEQUAL)
    GL.glColor(*c1)
    GL.glLineWidth(2.0)
    drawCube(box, cubeType=GL.GL_LINE_STRIP)

    GL.glDepthFunc(GL.GL_GREATER)
    GL.glColor(*c0)
    GL.glLineWidth(1.0)
    drawCube(box, cubeType=GL.GL_LINE_STRIP)

    GL.glDepthFunc(GL.GL_LEQUAL)
    GL.glDisable(GL.GL_DEPTH_TEST)
    # glDepthMask(True)


def loadAlphaTerrainTexture():
    texW, texH, terraindata = loadPNGFile(os.path.join(directories.getDataDir(),  ResourcePackHandler.Instance().get_selected_resource_pack().terrain_path()))

    def _loadFunc():
        loadTextureFunc(texW, texH, terraindata)

    tex = glutils.Texture(_loadFunc)
    tex.data = terraindata
    return tex


def loadPNGData(filename_or_data):
    reader = png.Reader(filename_or_data)
    (w, h, data, metadata) = reader.read_flat()
    data = numpy.array(data, dtype='uint8')
    data.shape = (h, w, metadata['planes'])
    if data.shape[2] == 1:
        # indexed color. remarkably straightforward.
        data.shape = data.shape[:2]
        data = numpy.array(reader.palette(), dtype='uint8')[data]

    if data.shape[2] < 4:
        data = numpy.insert(data, 3, 255, 2)

    return w, h, data


def loadPNGFile(filename):
    (w, h, data) = loadPNGData(filename)

    # We need 16*16 sub images in the 'terrain' files for now.
    # Can we read comments or additional data in PNG files to get the sub-images size like 32*32 or 8*8?
    assert (w % 16 == 0) and (h % 16 == 0)

    return w, h, data

def loadTextureFunc(w, h, ndata):
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w, h, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, ndata)
    return w, h


def loadPNGTexture(filename, *a, **kw):
    filename = os.path.join(directories.getDataDir(), filename)
    try:
        w, h, ndata = loadPNGFile(filename)

        tex = glutils.Texture(functools.partial(loadTextureFunc, w, h, ndata), *a, **kw)
        tex.data = ndata
        return tex
    except Exception as e:
        print "Exception loading ", filename, ": ", repr(e)
        return glutils.Texture()


import glutils


def normalize(x):
    l = x[0] * x[0] + x[1] * x[1] + x[2] * x[2]
    if l <= 0.0:
        return [0, 0, 0]
    size = numpy.sqrt(l)
    if size <= 0.0:
        return [0, 0, 0]
    return map(lambda a: a / size, x)


def normalize_size(x):
    l = x[0] * x[0] + x[1] * x[1] + x[2] * x[2]
    if l <= 0.0:
        return [0., 0., 0.], 0.
    size = numpy.sqrt(l)
    if size <= 0.0:
        return [0, 0, 0], 0
    return (x / size), size


