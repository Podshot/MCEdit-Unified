'''OpenGL extension VERSION.GLES3_3_1

This module customises the behaviour of the 
OpenGL.raw.GLES3.VERSION.GLES3_3_1 to provide a more 
Python-friendly API

The official definition of this extension is available here:
http://www.opengl.org/registry/specs/VERSION/GLES3_3_1.txt
'''
from OpenGL import platform, constant, arrays
from OpenGL import extensions, wrapper
import ctypes
from OpenGL.raw.GLES3 import _types, _glgets
from OpenGL.raw.GLES3.VERSION.GLES3_3_1 import *
from OpenGL.raw.GLES3.VERSION.GLES3_3_1 import _EXTENSION_NAME

def glInitGles331VERSION():
    '''Return boolean indicating whether this extension is available'''
    from OpenGL import extensions
    return extensions.hasGLExtension( _EXTENSION_NAME )

# INPUT glGetFramebufferParameteriv.params size not checked against 'pname'
glGetFramebufferParameteriv=wrapper.wrapper(glGetFramebufferParameteriv).setInputArraySize(
    'params', None
)
# INPUT glGetProgramInterfaceiv.params size not checked against 'pname'
glGetProgramInterfaceiv=wrapper.wrapper(glGetProgramInterfaceiv).setInputArraySize(
    'params', None
)
# INPUT glGetProgramResourceIndex.name size not checked against 'name'
glGetProgramResourceIndex=wrapper.wrapper(glGetProgramResourceIndex).setInputArraySize(
    'name', None
)
# INPUT glGetProgramResourceName.name size not checked against bufSize
glGetProgramResourceName=wrapper.wrapper(glGetProgramResourceName).setInputArraySize(
    'length', 1
).setInputArraySize(
    'name', None
)
# INPUT glGetProgramResourceiv.params size not checked against bufSize
# INPUT glGetProgramResourceiv.props size not checked against propCount
glGetProgramResourceiv=wrapper.wrapper(glGetProgramResourceiv).setInputArraySize(
    'length', 1
).setInputArraySize(
    'params', None
).setInputArraySize(
    'props', None
)
# INPUT glGetProgramResourceLocation.name size not checked against 'name'
glGetProgramResourceLocation=wrapper.wrapper(glGetProgramResourceLocation).setInputArraySize(
    'name', None
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
glProgramUniform2iv=wrapper.wrapper(glProgramUniform2iv).setInputArraySize(
    'value', 2
)
glProgramUniform3iv=wrapper.wrapper(glProgramUniform3iv).setInputArraySize(
    'value', 3
)
glProgramUniform4iv=wrapper.wrapper(glProgramUniform4iv).setInputArraySize(
    'value', 4
)
glProgramUniform1uiv=wrapper.wrapper(glProgramUniform1uiv).setInputArraySize(
    'value', 1
)
glProgramUniform2uiv=wrapper.wrapper(glProgramUniform2uiv).setInputArraySize(
    'value', 2
)
glProgramUniform3uiv=wrapper.wrapper(glProgramUniform3uiv).setInputArraySize(
    'value', 3
)
glProgramUniform4uiv=wrapper.wrapper(glProgramUniform4uiv).setInputArraySize(
    'value', 4
)
glProgramUniform1fv=wrapper.wrapper(glProgramUniform1fv).setInputArraySize(
    'value', 1
)
glProgramUniform2fv=wrapper.wrapper(glProgramUniform2fv).setInputArraySize(
    'value', 2
)
glProgramUniform3fv=wrapper.wrapper(glProgramUniform3fv).setInputArraySize(
    'value', 3
)
glProgramUniform4fv=wrapper.wrapper(glProgramUniform4fv).setInputArraySize(
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
glGetProgramPipelineInfoLog=wrapper.wrapper(glGetProgramPipelineInfoLog).setOutput(
    'length',size=(1,),orPassIn=True
).setOutput(
    'infoLog',size=lambda x:(x,),pnameArg='bufSize',orPassIn=True
)
glGetBooleani_v=wrapper.wrapper(glGetBooleani_v).setOutput(
    'data',size=_glgets._glget_size_mapping,pnameArg='target',orPassIn=True
)
glGetMultisamplefv=wrapper.wrapper(glGetMultisamplefv).setOutput(
    'val',size=_glgets._glget_size_mapping,pnameArg='pname',orPassIn=True
)
glGetTexLevelParameteriv=wrapper.wrapper(glGetTexLevelParameteriv).setOutput(
    'params',size=_glgets._glget_size_mapping,pnameArg='pname',orPassIn=True
)
glGetTexLevelParameterfv=wrapper.wrapper(glGetTexLevelParameterfv).setOutput(
    'params',size=_glgets._glget_size_mapping,pnameArg='pname',orPassIn=True
)
### END AUTOGENERATED SECTION