'''OpenGL extension OES.fixed_point

This module customises the behaviour of the 
OpenGL.raw.GL.OES.fixed_point to provide a more 
Python-friendly API

The official definition of this extension is available here:
http://www.opengl.org/registry/specs/OES/fixed_point.txt
'''
from OpenGL import platform, constant, arrays
from OpenGL import extensions, wrapper
import ctypes
from OpenGL.raw.GL import _types, _glgets
from OpenGL.raw.GL.OES.fixed_point import *
from OpenGL.raw.GL.OES.fixed_point import _EXTENSION_NAME

def glInitFixedPointOES():
    '''Return boolean indicating whether this extension is available'''
    from OpenGL import extensions
    return extensions.hasGLExtension( _EXTENSION_NAME )

glClipPlanexOES=wrapper.wrapper(glClipPlanexOES).setInputArraySize(
    'equation', 4
)
# INPUT glFogxvOES.param size not checked against 'pname'
glFogxvOES=wrapper.wrapper(glFogxvOES).setInputArraySize(
    'param', None
)
glGetClipPlanexOES=wrapper.wrapper(glGetClipPlanexOES).setInputArraySize(
    'equation', 4
)
# INPUT glGetFixedvOES.params size not checked against 'pname'
glGetFixedvOES=wrapper.wrapper(glGetFixedvOES).setInputArraySize(
    'params', None
)
# INPUT glGetTexEnvxvOES.params size not checked against 'pname'
glGetTexEnvxvOES=wrapper.wrapper(glGetTexEnvxvOES).setInputArraySize(
    'params', None
)
# INPUT glGetTexParameterxvOES.params size not checked against 'pname'
glGetTexParameterxvOES=wrapper.wrapper(glGetTexParameterxvOES).setInputArraySize(
    'params', None
)
# INPUT glLightModelxvOES.param size not checked against 'pname'
glLightModelxvOES=wrapper.wrapper(glLightModelxvOES).setInputArraySize(
    'param', None
)
# INPUT glLightxvOES.params size not checked against 'pname'
glLightxvOES=wrapper.wrapper(glLightxvOES).setInputArraySize(
    'params', None
)
glLoadMatrixxOES=wrapper.wrapper(glLoadMatrixxOES).setInputArraySize(
    'm', 16
)
# INPUT glMaterialxvOES.param size not checked against 'pname'
glMaterialxvOES=wrapper.wrapper(glMaterialxvOES).setInputArraySize(
    'param', None
)
glMultMatrixxOES=wrapper.wrapper(glMultMatrixxOES).setInputArraySize(
    'm', 16
)
# INPUT glPointParameterxvOES.params size not checked against 'pname'
glPointParameterxvOES=wrapper.wrapper(glPointParameterxvOES).setInputArraySize(
    'params', None
)
# INPUT glTexEnvxvOES.params size not checked against 'pname'
glTexEnvxvOES=wrapper.wrapper(glTexEnvxvOES).setInputArraySize(
    'params', None
)
# INPUT glTexParameterxvOES.params size not checked against 'pname'
glTexParameterxvOES=wrapper.wrapper(glTexParameterxvOES).setInputArraySize(
    'params', None
)
# INPUT glGetLightxvOES.params size not checked against 'pname'
glGetLightxvOES=wrapper.wrapper(glGetLightxvOES).setInputArraySize(
    'params', None
)
# INPUT glGetMaterialxvOES.params size not checked against 'pname'
glGetMaterialxvOES=wrapper.wrapper(glGetMaterialxvOES).setInputArraySize(
    'params', None
)
# INPUT glBitmapxOES.bitmap size not checked against 'width,height'
glBitmapxOES=wrapper.wrapper(glBitmapxOES).setInputArraySize(
    'bitmap', None
)
glColor3xvOES=wrapper.wrapper(glColor3xvOES).setInputArraySize(
    'components', 3
)
glColor4xvOES=wrapper.wrapper(glColor4xvOES).setInputArraySize(
    'components', 4
)
# INPUT glConvolutionParameterxvOES.params size not checked against 'pname'
glConvolutionParameterxvOES=wrapper.wrapper(glConvolutionParameterxvOES).setInputArraySize(
    'params', None
)
glEvalCoord1xvOES=wrapper.wrapper(glEvalCoord1xvOES).setInputArraySize(
    'coords', 1
)
glEvalCoord2xvOES=wrapper.wrapper(glEvalCoord2xvOES).setInputArraySize(
    'coords', 2
)
# INPUT glFeedbackBufferxOES.buffer size not checked against n
glFeedbackBufferxOES=wrapper.wrapper(glFeedbackBufferxOES).setInputArraySize(
    'buffer', None
)
# INPUT glGetConvolutionParameterxvOES.params size not checked against 'pname'
glGetConvolutionParameterxvOES=wrapper.wrapper(glGetConvolutionParameterxvOES).setInputArraySize(
    'params', None
)
# INPUT glGetHistogramParameterxvOES.params size not checked against 'pname'
glGetHistogramParameterxvOES=wrapper.wrapper(glGetHistogramParameterxvOES).setInputArraySize(
    'params', None
)
# INPUT glGetLightxOES.params size not checked against 'pname'
glGetLightxOES=wrapper.wrapper(glGetLightxOES).setInputArraySize(
    'params', None
)
# INPUT glGetMapxvOES.v size not checked against 'query'
glGetMapxvOES=wrapper.wrapper(glGetMapxvOES).setInputArraySize(
    'v', None
)
# INPUT glGetPixelMapxv.values size not checked against size
glGetPixelMapxv=wrapper.wrapper(glGetPixelMapxv).setInputArraySize(
    'values', None
)
# INPUT glGetTexGenxvOES.params size not checked against 'pname'
glGetTexGenxvOES=wrapper.wrapper(glGetTexGenxvOES).setInputArraySize(
    'params', None
)
# INPUT glGetTexLevelParameterxvOES.params size not checked against 'pname'
glGetTexLevelParameterxvOES=wrapper.wrapper(glGetTexLevelParameterxvOES).setInputArraySize(
    'params', None
)
glIndexxvOES=wrapper.wrapper(glIndexxvOES).setInputArraySize(
    'component', 1
)
glLoadTransposeMatrixxOES=wrapper.wrapper(glLoadTransposeMatrixxOES).setInputArraySize(
    'm', 16
)
glMultTransposeMatrixxOES=wrapper.wrapper(glMultTransposeMatrixxOES).setInputArraySize(
    'm', 16
)
glMultiTexCoord1xvOES=wrapper.wrapper(glMultiTexCoord1xvOES).setInputArraySize(
    'coords', 1
)
glMultiTexCoord2xvOES=wrapper.wrapper(glMultiTexCoord2xvOES).setInputArraySize(
    'coords', 2
)
glMultiTexCoord3xvOES=wrapper.wrapper(glMultiTexCoord3xvOES).setInputArraySize(
    'coords', 3
)
glMultiTexCoord4xvOES=wrapper.wrapper(glMultiTexCoord4xvOES).setInputArraySize(
    'coords', 4
)
glNormal3xvOES=wrapper.wrapper(glNormal3xvOES).setInputArraySize(
    'coords', 3
)
# INPUT glPixelMapx.values size not checked against size
glPixelMapx=wrapper.wrapper(glPixelMapx).setInputArraySize(
    'values', None
)
# INPUT glPrioritizeTexturesxOES.textures size not checked against n
# INPUT glPrioritizeTexturesxOES.priorities size not checked against n
glPrioritizeTexturesxOES=wrapper.wrapper(glPrioritizeTexturesxOES).setInputArraySize(
    'textures', None
).setInputArraySize(
    'priorities', None
)
glRasterPos2xvOES=wrapper.wrapper(glRasterPos2xvOES).setInputArraySize(
    'coords', 2
)
glRasterPos3xvOES=wrapper.wrapper(glRasterPos3xvOES).setInputArraySize(
    'coords', 3
)
glRasterPos4xvOES=wrapper.wrapper(glRasterPos4xvOES).setInputArraySize(
    'coords', 4
)
glRectxvOES=wrapper.wrapper(glRectxvOES).setInputArraySize(
    'v1', 2
).setInputArraySize(
    'v2', 2
)
glTexCoord1xvOES=wrapper.wrapper(glTexCoord1xvOES).setInputArraySize(
    'coords', 1
)
glTexCoord2xvOES=wrapper.wrapper(glTexCoord2xvOES).setInputArraySize(
    'coords', 2
)
glTexCoord3xvOES=wrapper.wrapper(glTexCoord3xvOES).setInputArraySize(
    'coords', 3
)
glTexCoord4xvOES=wrapper.wrapper(glTexCoord4xvOES).setInputArraySize(
    'coords', 4
)
# INPUT glTexGenxvOES.params size not checked against 'pname'
glTexGenxvOES=wrapper.wrapper(glTexGenxvOES).setInputArraySize(
    'params', None
)
glVertex2xvOES=wrapper.wrapper(glVertex2xvOES).setInputArraySize(
    'coords', 2
)
glVertex3xvOES=wrapper.wrapper(glVertex3xvOES).setInputArraySize(
    'coords', 3
)
glVertex4xvOES=wrapper.wrapper(glVertex4xvOES).setInputArraySize(
    'coords', 4
)
### END AUTOGENERATED SECTION