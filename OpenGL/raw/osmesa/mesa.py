from OpenGL.raw.GL._types import GLenum,GLboolean,GLsizei,GLint
from OpenGL.raw.osmesa._types import *
from OpenGL.constant import Constant as _C
from OpenGL import platform as _p
import ctypes

def _f( function ):
    return _p.createFunction( 
        function,_p.PLATFORM.OSMesa,
        None,
        error_checker=None
    )

OSMESA_COLOR_INDEX = _C('OSMESA_COLOR_INDEX', 6400)
OSMESA_RGBA = _C('OSMESA_RGBA', 6408)
OSMESA_BGRA = _C('OSMESA_BGRA', 0x1)
OSMESA_ARGB = _C('OSMESA_ARGB', 0x2)
OSMESA_RGB = _C('OSMESA_RGB', 6407)
OSMESA_BGR = _C('OSMESA_BGR',	0x4)
OSMESA_RGB_565 = _C('OSMESA_BGR', 0x5)
OSMESA_ROW_LENGTH = _C('OSMESA_ROW_LENGTH', 0x10)
OSMESA_Y_UP = _C('OSMESA_Y_UP', 0x11)
OSMESA_WIDTH = _C('OSMESA_WIDTH', 0x20)
OSMESA_HEIGHT = _C('OSMESA_HEIGHT', 0x21)
OSMESA_FORMAT = _C('OSMESA_FORMAT', 0x22)
OSMESA_TYPE = _C('OSMESA_TYPE', 0x23)
OSMESA_MAX_WIDTH = _C('OSMESA_MAX_WIDTH', 0x24)
OSMESA_MAX_HEIGHT = _C('OSMESA_MAX_HEIGHT', 0x25)

OSMesaGetCurrentContext = _p.GetCurrentContext

@_f
@_p.types(OSMesaContext,GLenum, OSMesaContext)
def OSMesaCreateContext(format,sharelist): pass

@_f
@_p.types(OSMesaContext,GLenum, GLint, GLint, GLint, OSMesaContext)
def OSMesaCreateContextExt(format, depthBits, stencilBits,accumBits,sharelist ): pass

@_f
@_p.types(None, OSMesaContext)
def OSMesaDestroyContext(ctx): pass

@_f 
@_p.types(GLboolean, OSMesaContext, ctypes.POINTER(None), GLenum, GLsizei, GLsizei )
def OSMesaMakeCurrent( ctx, buffer, type,width,height ): pass

@_f 
@_p.types(None, GLint, GLint )
def OSMesaPixelStore( ctx, buffer, type,width,height ): pass

def OSMesaGetIntegerv(pname):
    value = GLint()
    _p.PLATFORM.GL.OSMesaGetIntegerv(pname, ctypes.byref(value))
    return value.value

def OSMesaGetDepthBuffer(c):
    width, height, bytesPerValue = GLint(), GLint(), GLint()
    buffer = ctypes.POINTER(GLint)()

    if _p.PLATFORM.GL.OSMesaGetDepthBuffer(c, ctypes.byref(width),
                                    ctypes.byref(height),
                                    ctypes.byref(bytesPerValue),
                                    ctypes.byref(buffer)):
        return width.value, height.value, bytesPerValue.value, buffer
    else:
        return 0, 0, 0, None

def OSMesaGetColorBuffer(c):
    # TODO: make output array types which can handle the operation 
    # provide an API to convert pointers + sizes to array instances,
    # e.g. numpy.ctypeslib.as_array( ptr, bytesize ).astype( 'B' ).reshape( height,width )
    width, height, format = GLint(), GLint(), GLint()
    buffer = ctypes.c_void_p()

    if GL.OSMesaGetColorBuffer(c, ctypes.byref(width),
                                    ctypes.byref(height),
                                    ctypes.byref(format),
                                    ctypes.byref(buffer)):
        return width.value, height.value, format.value, buffer
    else:
        return 0, 0, 0, None


__all__ = [
    'OSMesaCreateContext',
    'OSMesaCreateContextExt', 'OSMesaMakeCurrent', 'OSMesaGetIntegerv',
    'OSMesaGetCurrentContext', 'OSMesaDestroyContext', 'OSMesaPixelStore',
    'OSMesaGetDepthBuffer', 'OSMesaGetColorBuffer',
    'OSMESA_COLOR_INDEX', 'OSMESA_RGBA', 'OSMESA_BGRA', 'OSMESA_ARGB',
    'OSMESA_RGB', 'OSMESA_BGR', 'OSMESA_BGR', 'OSMESA_ROW_LENGTH',
    'OSMESA_Y_UP', 'OSMESA_WIDTH', 'OSMESA_HEIGHT', 'OSMESA_FORMAT',
    'OSMESA_TYPE', 'OSMESA_MAX_WIDTH', 'OSMESA_MAX_HEIGHT',
]
