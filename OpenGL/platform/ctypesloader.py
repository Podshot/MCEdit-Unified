"""ctypes abstraction layer

We keep rewriting functions as the main entry points change,
so let's just localise the changes here...
"""
import ctypes, logging, os, sys
_log = logging.getLogger( 'OpenGL.platform.ctypesloader' )
#_log.setLevel( logging.DEBUG )
ctypes_version = [
    int(x) for x in ctypes.__version__.split('.')
]
from ctypes import util
import OpenGL

DLL_DIRECTORY = os.path.join( os.path.dirname( OpenGL.__file__ ), 'DLLS' )

def loadLibrary( dllType, name, mode = ctypes.RTLD_GLOBAL ):
    """Load a given library by name with the given mode
    
    dllType -- the standard ctypes pointer to a dll type, such as
        ctypes.cdll or ctypes.windll or the underlying ctypes.CDLL or 
        ctypes.WinDLL classes.
    name -- a short module name, e.g. 'GL' or 'GLU'
    mode -- ctypes.RTLD_GLOBAL or ctypes.RTLD_LOCAL,
        controls whether the module resolves names via other
        modules already loaded into this process.  GL modules
        generally need to be loaded with GLOBAL flags
    
    returns the ctypes C-module object
    """
    if isinstance( dllType, ctypes.LibraryLoader ):
        dllType = dllType._dlltype
    fullName = None
    try:
        fullName = util.find_library( name )
        if fullName is not None:
            name = fullName
        elif os.path.isfile( os.path.join( DLL_DIRECTORY, name + '.dll' )):
            name = os.path.join( DLL_DIRECTORY, name + '.dll' )
    except Exception as err:
        _log.info( '''Failed on util.find_library( %r ): %s''', name, err )
        # Should the call fail, we just try to load the base filename...
        pass
    try:
        return dllType( name, mode )
    except Exception as err:
        err.args += (name,fullName)
        raise

def buildFunction( functionType, name, dll ):
    """Abstract away the ctypes function-creation operation"""
    return functionType( (name, dll), )
