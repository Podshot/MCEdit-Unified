"""Integer values looked up via glGetIntegerv( constant )"""
import ctypes
_get = None

class LookupInt( object ):
    def __init__( self, lookup, format=ctypes.c_int ):
        self.lookup = lookup 
        self.format = format
    def __int__( self ):
        global _get
        if _get is None:
            from OpenGL.GL import glGetIntegerv
            _get = glGetIntegerv
        output = self.format()
        _get( self.lookup, output )
        return output.value
    def __eq__( self, other ):
        return int(self) == other
    def __cmp__( self, other ):
        return cmp( int(self), other )
    
