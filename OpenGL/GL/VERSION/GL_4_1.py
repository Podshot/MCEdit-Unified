'''OpenGL extension VERSION.GL_4_1

This module customises the behaviour of the 
OpenGL.raw.GL.VERSION.GL_4_1 to provide a more 
Python-friendly API

The official definition of this extension is available here:
http://www.opengl.org/registry/specs/VERSION/GL_4_1.txt
'''
from OpenGL import platform, constant, arrays
from OpenGL import extensions, wrapper
import ctypes
from OpenGL.raw.GL import _types, _glgets
from OpenGL.raw.GL.VERSION.GL_4_1 import *
from OpenGL.raw.GL.VERSION.GL_4_1 import _EXTENSION_NAME

def glInitGl41VERSION():
    '''Return boolean indicating whether this extension is available'''
    from OpenGL import extensions
    return extensions.hasGLExtension( _EXTENSION_NAME )

# INPUT glShaderBinary.binary size not checked against length
# INPUT glShaderBinary.shaders size not checked against count
glShaderBinary=wrapper.wrapper(glShaderBinary).setInputArraySize(
    'binary', None
).setInputArraySize(
    'shaders', None
)
glGetShaderPrecisionFormat=wrapper.wrapper(glGetShaderPrecisionFormat).setOutput(
    'range',size=(2,),orPassIn=True
).setOutput(
    'precision',size=(2,),orPassIn=True
)
glGetProgramBinary=wrapper.wrapper(glGetProgramBinary).setOutput(
    'binary',size=lambda x:(x,),pnameArg='bufSize',orPassIn=True
).setOutput(
    'length',size=(1,),orPassIn=True
).setOutput(
    'binaryFormat',size=(1,),orPassIn=True
)
# INPUT glProgramBinary.binary size not checked against length
glProgramBinary=wrapper.wrapper(glProgramBinary).setInputArraySize(
    'binary', None
)
# INPUT glCreateShaderProgramv.strings size not checked against count
glCreateShaderProgramv=wrapper.wrapper(glCreateShaderProgramv).setInputArraySize(
    'strings', None
)
# INPUT glDeleteProgramPipelines.pipelines size not checked against n
glDeleteProgramPipelines=wrapper.wrapper(glDeleteProgramPipelines).setInputArraySize(
    'pipelines', None
)
glGenProgramPipelines=wrapper.wrapper(glGenProgramPipelines).setOutput(
    'pipelines',size=lambda x:(x,),pnameArg='n',orPassIn=True
)
glGetProgramPipelineiv=wrapper.wrapper(glGetProgramPipelineiv).setOutput(
    'params',size=_glgets._glget_size_mapping,pnameArg='pname',orPassIn=True
)
glProgramUniform1iv=wrapper.wrapper(glProgramUniform1iv).setInputArraySize(
    'value', 1
)
glProgramUniform1fv=wrapper.wrapper(glProgramUniform1fv).setInputArraySize(
    'value', 1
)
glProgramUniform1dv=wrapper.wrapper(glProgramUniform1dv).setInputArraySize(
    'value', 1
)
glProgramUniform1uiv=wrapper.wrapper(glProgramUniform1uiv).setInputArraySize(
    'value', 1
)
glProgramUniform2iv=wrapper.wrapper(glProgramUniform2iv).setInputArraySize(
    'value', 2
)
glProgramUniform2fv=wrapper.wrapper(glProgramUniform2fv).setInputArraySize(
    'value', 2
)
glProgramUniform2dv=wrapper.wrapper(glProgramUniform2dv).setInputArraySize(
    'value', 2
)
glProgramUniform2uiv=wrapper.wrapper(glProgramUniform2uiv).setInputArraySize(
    'value', 2
)
glProgramUniform3iv=wrapper.wrapper(glProgramUniform3iv).setInputArraySize(
    'value', 3
)
glProgramUniform3fv=wrapper.wrapper(glProgramUniform3fv).setInputArraySize(
    'value', 3
)
glProgramUniform3dv=wrapper.wrapper(glProgramUniform3dv).setInputArraySize(
    'value', 3
)
glProgramUniform3uiv=wrapper.wrapper(glProgramUniform3uiv).setInputArraySize(
    'value', 3
)
glProgramUniform4iv=wrapper.wrapper(glProgramUniform4iv).setInputArraySize(
    'value', 4
)
glProgramUniform4fv=wrapper.wrapper(glProgramUniform4fv).setInputArraySize(
    'value', 4
)
glProgramUniform4dv=wrapper.wrapper(glProgramUniform4dv).setInputArraySize(
    'value', 4
)
glProgramUniform4uiv=wrapper.wrapper(glProgramUniform4uiv).setInputArraySize(
    'value', 4
)
glProgramUniformMatrix2fv=wrapper.wrapper(glProgramUniformMatrix2fv).setInputArraySize(
    'value', 2
)
glProgramUniformMatrix3fv=wrapper.wrapper(glProgramUniformMatrix3fv).setInputArraySize(
    'value', 3
)
glProgramUniformMatrix4fv=wrapper.wrapper(glProgramUniformMatrix4fv).setInputArraySize(
    'value', 4
)
glProgramUniformMatrix2dv=wrapper.wrapper(glProgramUniformMatrix2dv).setInputArraySize(
    'value', 2
)
glProgramUniformMatrix3dv=wrapper.wrapper(glProgramUniformMatrix3dv).setInputArraySize(
    'value', 3
)
glProgramUniformMatrix4dv=wrapper.wrapper(glProgramUniformMatrix4dv).setInputArraySize(
    'value', 4
)
# INPUT glProgramUniformMatrix2x3fv.value size not checked against count
glProgramUniformMatrix2x3fv=wrapper.wrapper(glProgramUniformMatrix2x3fv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix3x2fv.value size not checked against count
glProgramUniformMatrix3x2fv=wrapper.wrapper(glProgramUniformMatrix3x2fv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix2x4fv.value size not checked against count
glProgramUniformMatrix2x4fv=wrapper.wrapper(glProgramUniformMatrix2x4fv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4x2fv.value size not checked against count
glProgramUniformMatrix4x2fv=wrapper.wrapper(glProgramUniformMatrix4x2fv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix3x4fv.value size not checked against count
glProgramUniformMatrix3x4fv=wrapper.wrapper(glProgramUniformMatrix3x4fv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4x3fv.value size not checked against count
glProgramUniformMatrix4x3fv=wrapper.wrapper(glProgramUniformMatrix4x3fv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix2x3dv.value size not checked against count
glProgramUniformMatrix2x3dv=wrapper.wrapper(glProgramUniformMatrix2x3dv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix3x2dv.value size not checked against count
glProgramUniformMatrix3x2dv=wrapper.wrapper(glProgramUniformMatrix3x2dv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix2x4dv.value size not checked against count
glProgramUniformMatrix2x4dv=wrapper.wrapper(glProgramUniformMatrix2x4dv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4x2dv.value size not checked against count
glProgramUniformMatrix4x2dv=wrapper.wrapper(glProgramUniformMatrix4x2dv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix3x4dv.value size not checked against count
glProgramUniformMatrix3x4dv=wrapper.wrapper(glProgramUniformMatrix3x4dv).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4x3dv.value size not checked against count
glProgramUniformMatrix4x3dv=wrapper.wrapper(glProgramUniformMatrix4x3dv).setInputArraySize(
    'value', None
)
glGetProgramPipelineInfoLog=wrapper.wrapper(glGetProgramPipelineInfoLog).setOutput(
    'length',size=(1,),orPassIn=True
).setOutput(
    'infoLog',size=lambda x:(x,),pnameArg='bufSize',orPassIn=True
)
glVertexAttribL1dv=wrapper.wrapper(glVertexAttribL1dv).setInputArraySize(
    'v', 1
)
glVertexAttribL2dv=wrapper.wrapper(glVertexAttribL2dv).setInputArraySize(
    'v', 2
)
glVertexAttribL3dv=wrapper.wrapper(glVertexAttribL3dv).setInputArraySize(
    'v', 3
)
glVertexAttribL4dv=wrapper.wrapper(glVertexAttribL4dv).setInputArraySize(
    'v', 4
)
# INPUT glVertexAttribLPointer.pointer size not checked against size
glVertexAttribLPointer=wrapper.wrapper(glVertexAttribLPointer).setInputArraySize(
    'pointer', None
)
glGetVertexAttribLdv=wrapper.wrapper(glGetVertexAttribLdv).setOutput(
    'params',size=_glgets._glget_size_mapping,pnameArg='pname',orPassIn=True
)
# INPUT glViewportArrayv.v size not checked against 'count'
glViewportArrayv=wrapper.wrapper(glViewportArrayv).setInputArraySize(
    'v', None
)
glViewportIndexedfv=wrapper.wrapper(glViewportIndexedfv).setInputArraySize(
    'v', 4
)
# INPUT glScissorArrayv.v size not checked against 'count'
glScissorArrayv=wrapper.wrapper(glScissorArrayv).setInputArraySize(
    'v', None
)
glScissorIndexedv=wrapper.wrapper(glScissorIndexedv).setInputArraySize(
    'v', 4
)
# INPUT glDepthRangeArrayv.v size not checked against 'count'
glDepthRangeArrayv=wrapper.wrapper(glDepthRangeArrayv).setInputArraySize(
    'v', None
)
glGetFloati_v=wrapper.wrapper(glGetFloati_v).setOutput(
    'data',size=_glgets._glget_size_mapping,pnameArg='target',orPassIn=True
)
glGetDoublei_v=wrapper.wrapper(glGetDoublei_v).setOutput(
    'data',size=_glgets._glget_size_mapping,pnameArg='target',orPassIn=True
)
### END AUTOGENERATED SECTION
from OpenGL.GL.ARB.ES2_compatibility import *
from OpenGL.GL.ARB.get_program_binary import *
from OpenGL.GL.ARB.separate_shader_objects import *
from OpenGL.GL.ARB.shader_precision import *
from OpenGL.GL.ARB.vertex_attrib_64bit import *
from OpenGL.GL.ARB.viewport_array import *
