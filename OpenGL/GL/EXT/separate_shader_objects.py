'''OpenGL extension EXT.separate_shader_objects

This module customises the behaviour of the 
OpenGL.raw.GL.EXT.separate_shader_objects to provide a more 
Python-friendly API

Overview (from the spec)
	
	Prior to this extension, GLSL requires multiple shader domains
	(vertex, fragment, geometry) to be linked into a single monolithic
	program object to specify a GLSL shader for each domain.
	
	While GLSL's monolithic approach has some advantages for
	optimizing shaders as a unit that span multiple domains, all
	existing GPU hardware supports the more flexible mix-and-match
	approach.
	
	HLSL9, Cg, the prior OpenGL assembly program extensions, and game
	console programmers favor a more flexible "mix-and-match" approach to
	specifying shaders independently for these different shader domains.
	Many developers build their shader content around the mix-and-match
	approach where they can use a single vertex shader with multiple
	fragment shaders (or vice versa).
	
	This keep-it-simple extension adapts the "mix-and-match" shader
	domain model for GLSL so different GLSL program objects can be bound
	to different shader domains.
	
	This extension redefines the operation of glUseProgram(GLenum program)
	to be equivalent to:
	
	    glUseShaderProgramEXT(GL_VERTEX_SHADER, program);
	    glUseShaderProgramEXT(GL_GEOMETRY_SHADER_EXT, program);
	    glUseShaderProgramEXT(GL_FRAGMENT_SHADER, program);
	    glActiveProgramEXT(program);
	
	You can also call these commands separately to bind each respective
	domain.  The GL_VERTEX_SHADER, GL_GEOMETRY_SHADER_EXT, and
	GL_FRAGMENT_SHADER tokens refer to the conventional vertex, geometry,
	and fragment domains respectively.  glActiveProgramEXT specifies
	the program that glUniform* commands will update.
	
	Separate linking creates the possibility that certain output varyings
	of a shader may go unread by the subsequent shader inputting varyings.
	In this case, the output varyings are simply ignored.  It is also
	possible input varyings from a shader may not be written as output
	varyings of a preceding shader.  In this case, the unwritten input
	varying values are undefined.  Implementations are encouraged to
	zero these undefined input varying values.
	
	This extension is a proof-of-concept that separate shader objects
	can work for GLSL and a response to repeated requests for this
	functionality.  There are various loose ends, particularly when
	dealing with user-defined varyings.  The hope is a future extension
	will improve this situation.

The official definition of this extension is available here:
http://www.opengl.org/registry/specs/EXT/separate_shader_objects.txt
'''
from OpenGL import platform, constant, arrays
from OpenGL import extensions, wrapper
import ctypes
from OpenGL.raw.GL import _types, _glgets
from OpenGL.raw.GL.EXT.separate_shader_objects import *
from OpenGL.raw.GL.EXT.separate_shader_objects import _EXTENSION_NAME

def glInitSeparateShaderObjectsEXT():
    '''Return boolean indicating whether this extension is available'''
    from OpenGL import extensions
    return extensions.hasGLExtension( _EXTENSION_NAME )

# INPUT glCreateShaderProgramvEXT.strings size not checked against count
glCreateShaderProgramvEXT=wrapper.wrapper(glCreateShaderProgramvEXT).setInputArraySize(
    'strings', None
)
# INPUT glDeleteProgramPipelinesEXT.pipelines size not checked against n
glDeleteProgramPipelinesEXT=wrapper.wrapper(glDeleteProgramPipelinesEXT).setInputArraySize(
    'pipelines', None
)
# INPUT glGenProgramPipelinesEXT.pipelines size not checked against n
glGenProgramPipelinesEXT=wrapper.wrapper(glGenProgramPipelinesEXT).setInputArraySize(
    'pipelines', None
)
# INPUT glGetProgramPipelineInfoLogEXT.infoLog size not checked against bufSize
glGetProgramPipelineInfoLogEXT=wrapper.wrapper(glGetProgramPipelineInfoLogEXT).setInputArraySize(
    'length', 1
).setInputArraySize(
    'infoLog', None
)
# INPUT glProgramUniform1fvEXT.value size not checked against count
glProgramUniform1fvEXT=wrapper.wrapper(glProgramUniform1fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform1ivEXT.value size not checked against count
glProgramUniform1ivEXT=wrapper.wrapper(glProgramUniform1ivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform2fvEXT.value size not checked against None
glProgramUniform2fvEXT=wrapper.wrapper(glProgramUniform2fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform2ivEXT.value size not checked against None
glProgramUniform2ivEXT=wrapper.wrapper(glProgramUniform2ivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform3fvEXT.value size not checked against None
glProgramUniform3fvEXT=wrapper.wrapper(glProgramUniform3fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform3ivEXT.value size not checked against None
glProgramUniform3ivEXT=wrapper.wrapper(glProgramUniform3ivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform4fvEXT.value size not checked against None
glProgramUniform4fvEXT=wrapper.wrapper(glProgramUniform4fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform4ivEXT.value size not checked against None
glProgramUniform4ivEXT=wrapper.wrapper(glProgramUniform4ivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix2fvEXT.value size not checked against None
glProgramUniformMatrix2fvEXT=wrapper.wrapper(glProgramUniformMatrix2fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix3fvEXT.value size not checked against None
glProgramUniformMatrix3fvEXT=wrapper.wrapper(glProgramUniformMatrix3fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4fvEXT.value size not checked against None
glProgramUniformMatrix4fvEXT=wrapper.wrapper(glProgramUniformMatrix4fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform1uivEXT.value size not checked against count
glProgramUniform1uivEXT=wrapper.wrapper(glProgramUniform1uivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform2uivEXT.value size not checked against None
glProgramUniform2uivEXT=wrapper.wrapper(glProgramUniform2uivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform3uivEXT.value size not checked against None
glProgramUniform3uivEXT=wrapper.wrapper(glProgramUniform3uivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniform4uivEXT.value size not checked against None
glProgramUniform4uivEXT=wrapper.wrapper(glProgramUniform4uivEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4fvEXT.value size not checked against None
glProgramUniformMatrix4fvEXT=wrapper.wrapper(glProgramUniformMatrix4fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix2x3fvEXT.value size not checked against None
glProgramUniformMatrix2x3fvEXT=wrapper.wrapper(glProgramUniformMatrix2x3fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix3x2fvEXT.value size not checked against None
glProgramUniformMatrix3x2fvEXT=wrapper.wrapper(glProgramUniformMatrix3x2fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix2x4fvEXT.value size not checked against None
glProgramUniformMatrix2x4fvEXT=wrapper.wrapper(glProgramUniformMatrix2x4fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4x2fvEXT.value size not checked against None
glProgramUniformMatrix4x2fvEXT=wrapper.wrapper(glProgramUniformMatrix4x2fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix3x4fvEXT.value size not checked against None
glProgramUniformMatrix3x4fvEXT=wrapper.wrapper(glProgramUniformMatrix3x4fvEXT).setInputArraySize(
    'value', None
)
# INPUT glProgramUniformMatrix4x3fvEXT.value size not checked against None
glProgramUniformMatrix4x3fvEXT=wrapper.wrapper(glProgramUniformMatrix4x3fvEXT).setInputArraySize(
    'value', None
)
### END AUTOGENERATED SECTION