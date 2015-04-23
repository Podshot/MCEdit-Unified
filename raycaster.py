import math
"""
This function will produce a generator that will give out the blocks
visited by a raycast in sequence. It is up to the user to terminate the generator.

First described here by John Amanatides
http://www.cse.yorku.ca/~amana/research/grid.pdf

Implementation in javascript by Kevin Reid:
https://gamedev.stackexchange.com/questions/47362/cast-ray-to-select-block-in-voxel-game
"""


def _rawRaycast(origin, direction):
    def _signum(x):
        if x > 0:
            return 1
        elif x < 0:
            return -1
        else:
            return 0

    def _intbound(s,ds):
        if ds<0:
            return _intbound(-s,-ds)
        else:
            s %= 1
            return (1-s)/ds

    x,y,z = map(int,map(math.floor,origin))
    dx,dy,dz = direction

    if dx == 0:  #Yes, I know this is hacky. It works though.
        dx = 0.000000001
    if dy == 0:
        dy = 0.000000001
    if dz == 0:
        dz = 0.000000001

    stepX,stepY,stepZ = map(_signum,direction)
    tMaxX,tMaxY,tMaxZ = map(_intbound,origin,(dx,dy,dz))
    tDeltaX = stepX/dx
    tDeltaY = stepY/dy
    tDeltaZ = stepZ/dz

    if dx == 0 and dy == 0 and dz == 0:
        raise Exception('Infinite ray trace detected')

    face = None
    while True:
        yield ((x,y,z),face)
        if tMaxX < tMaxY:
            if tMaxX < tMaxZ:
                x += stepX
                tMaxX += tDeltaX
                face = (-stepX, 0,0)
            else:
                z += stepZ
                tMaxZ += tDeltaZ
                face = (0,0,-stepZ)
        else:
            if tMaxY < tMaxZ:
                y += stepY
                tMaxY += tDeltaY
                face = (0,-stepY,0)
            else:
                z += stepZ
                tMaxZ += tDeltaZ
                face = (0,0,-stepZ)

"""
Finds the first block from origin in the given direction by ray tracing
    origin is the coordinate of the camera given as a tuple
    direction is a vector in the direction the block wanted is from the camera given as a tuple
    callback an object that will be inform

    This method returns a (position,face) tuple pair.
"""


def firstBlock(origin, direction, level, radius, viewMode=None):
    if viewMode == "Chunk":
        raise TooFarException("There are no valid blocks within range")
    startPos =  map(int,map(math.floor,origin))
    block = level.blockAt(*startPos)
    tooMuch = 0
    if block == 8 or block == 9:
        callback = _WaterCallback()
    else:
        callback = _StandardCallback()
    for i in _rawRaycast(origin,direction):
        tooMuch += 1
        block = level.blockAt(*i[0])
        if callback.check(i[0],block):
            return i[0],i[1]
        if _tooFar(origin, i[0], radius) or _tooHighOrLow(i[0]):
            raise TooFarException("There are no valid blocks within range")
        if tooMuch >= 720:
            return i[0], i[1]


def _tooFar(origin, position, radius):
    x = abs(origin[0] - position[0])
    y = abs(origin[1] - position[1])
    z = abs(origin[2] - position[2])

    result = x>radius or y>radius or z>radius
    return result


def _tooHighOrLow(position):
    return position[1] > 255 or position[1] < 0


class TooFarException(Exception):
    def __init__(self,value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Callback:
    """
    Returns true if the ray tracer is to be terminated
    """
    def check(self, position,block):
        pass


class _WaterCallback(Callback):
    def __init__(self):
        self.escapedBlock = False

    def check(self, position, block):
        if block == 8 or block == 9:
            return False
        elif block == 0:
            self.escapedBlock = True
            return False
        elif self.escapedBlock and block != 0:
            return True
        return True


class _StandardCallback(Callback):
    def __init__(self):
        self.escapedBlock = False

    def check(self, position, block):
        if not self.escapedBlock:
            if block == 0:
                self.escapedBlock = True
            return
        if block != 0:
            return True
        return False
