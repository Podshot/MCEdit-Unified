import materials
from materials import alphaMaterials
from numpy import arange, zeros

# #!# Needed for the bad hack done with 'blocktable'...
import collections
import re

class __Rotation:
    def __init__(self):
        for i, blocktype in enumerate(self.blocktypes):
            self.blocktypes[i] = eval(blocktype)

def genericRoll(cls):
    rotation = arange(16, dtype='uint8')
    if hasattr(cls, "Up") and hasattr(cls, "Down"):
        rotation[cls.Up] = cls.North
        rotation[cls.Down] = cls.South
        rotation[cls.South] = cls.Up
        rotation[cls.North] = cls.Down
    return rotation


def genericVerticalFlip(cls):
    rotation = arange(16, dtype='uint8')
    if hasattr(cls, "Up") and hasattr(cls, "Down"):
        rotation[cls.Up] = cls.Down
        rotation[cls.Down] = cls.Up

    if hasattr(cls, "TopNorth") and hasattr(cls, "TopWest") and hasattr(cls, "TopSouth") and hasattr(cls, "TopEast"):
        rotation[cls.North] = cls.TopNorth
        rotation[cls.West] = cls.TopWest
        rotation[cls.South] = cls.TopSouth
        rotation[cls.East] = cls.TopEast
        rotation[cls.TopNorth] = cls.North
        rotation[cls.TopWest] = cls.West
        rotation[cls.TopSouth] = cls.South
        rotation[cls.TopEast] = cls.East

    return rotation


def genericRotation(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.North] = cls.West
    rotation[cls.West] = cls.South
    rotation[cls.South] = cls.East
    rotation[cls.East] = cls.North
    if hasattr(cls, "TopNorth") and hasattr(cls, "TopWest") and hasattr(cls, "TopSouth") and hasattr(cls, "TopEast"):
        rotation[cls.TopNorth] = cls.TopWest
        rotation[cls.TopWest] = cls.TopSouth
        rotation[cls.TopSouth] = cls.TopEast
        rotation[cls.TopEast] = cls.TopNorth

    return rotation


def genericEastWestFlip(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.West] = cls.East
    rotation[cls.East] = cls.West
    if hasattr(cls, "TopWest") and hasattr(cls, "TopEast"):
        rotation[cls.TopWest] = cls.TopEast
        rotation[cls.TopEast] = cls.TopWest

    return rotation


def genericNorthSouthFlip(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.South] = cls.North
    rotation[cls.North] = cls.South
    if hasattr(cls, "TopNorth") and hasattr(cls, "TopSouth"):
        rotation[cls.TopSouth] = cls.TopNorth
        rotation[cls.TopNorth] = cls.TopSouth

    return rotation


rotationClasses = []


def genericFlipRotation(cls):
    cls.rotateLeft = genericRotation(cls)
    cls.roll = genericRoll(cls)

    cls.flipVertical = genericVerticalFlip(cls)
    cls.flipEastWest = genericEastWestFlip(cls)
    cls.flipNorthSouth = genericNorthSouthFlip(cls)
    rotationClasses.append(cls)
    return cls


# Note, directions are based on the old north. North in here is East ingame.
class Torch(__Rotation):
    blocktypes = [
        'alphaMaterials.Torch.ID',
        'alphaMaterials.RedstoneTorchOn.ID',
        'alphaMaterials.RedstoneTorchOff.ID',
    ]

    South = 1
    North = 2
    West = 3
    East = 4
    # on the bottom
    Up = 5


genericFlipRotation(Torch)
Torch.roll = arange(16, dtype='uint8')
Torch.roll[Torch.Up] = Torch.North
Torch.roll[Torch.South] = Torch.Up


class Ladder(__Rotation):
    blocktypes = ['alphaMaterials.Ladder.ID']

    East = 2
    West = 3
    North = 4
    South = 5


genericFlipRotation(Ladder)


class Stair(__Rotation):
    blocktypes = ['b.ID for b in alphaMaterials.AllStairs']

    South = 0
    North = 1
    West = 2
    East = 3
    TopSouth = 4
    TopNorth = 5
    TopWest = 6
    TopEast = 7


genericFlipRotation(Stair)

Stair.roll = arange(16, dtype='uint8')
Stair.roll[Stair.East] = Stair.East
Stair.roll[Stair.West] = Stair.West
Stair.roll[Stair.TopEast] = Stair.TopEast
Stair.roll[Stair.TopWest] = Stair.TopWest

Stair.roll[Stair.North] = Stair.South
Stair.roll[Stair.South] = Stair.TopSouth
Stair.roll[Stair.TopSouth] = Stair.TopNorth
Stair.roll[Stair.TopNorth] = Stair.North

# data value 0-8 bottom and 9-15 Top


class HalfSlab(__Rotation):
    blocktypes = ['b.ID for b in alphaMaterials.AllSlabs']

HalfSlab.flipVertical = arange(16, dtype='uint8')
for i in xrange(8):
    HalfSlab.flipVertical[i] = i + 8
    HalfSlab.flipVertical[i + 8] = i
rotationClasses.append(HalfSlab)


class WallSign(__Rotation):
    blocktypes = ['alphaMaterials.WallSign.ID', 'alphaMaterials.WallBanner.ID']

    East = 2
    West = 3
    North = 4
    South = 5


genericFlipRotation(WallSign)


class FurnaceDispenserChest(__Rotation):
    blocktypes = [
        'alphaMaterials.Furnace.ID',
        'alphaMaterials.LitFurnace.ID',
        'alphaMaterials.Chest.ID',
        'alphaMaterials.EnderChest.ID',
        'alphaMaterials.TrappedChest.ID'
    ]
    East = 2
    West = 3
    North = 4
    South = 5


genericFlipRotation(FurnaceDispenserChest)


class Pumpkin(__Rotation):
    blocktypes = [
        'alphaMaterials.Pumpkin.ID',
        'alphaMaterials.JackOLantern.ID',
    ]

    East = 0
    South = 1
    West = 2
    North = 3


genericFlipRotation(Pumpkin)


class Rail(__Rotation):
    blocktypes = ['alphaMaterials.Rail.ID']

    EastWest = 0
    NorthSouth = 1
    South = 2
    North = 3
    East = 4
    West = 5

    Northeast = 6
    Southeast = 7
    Southwest = 8
    Northwest = 9


def generic8wayRotation(cls):
    cls.rotateLeft = genericRotation(cls)
    cls.rotateLeft[cls.Northeast] = cls.Northwest
    cls.rotateLeft[cls.Southeast] = cls.Northeast
    cls.rotateLeft[cls.Southwest] = cls.Southeast
    cls.rotateLeft[cls.Northwest] = cls.Southwest

    cls.flipEastWest = genericEastWestFlip(cls)
    cls.flipEastWest[cls.Northeast] = cls.Northwest
    cls.flipEastWest[cls.Northwest] = cls.Northeast
    cls.flipEastWest[cls.Southwest] = cls.Southeast
    cls.flipEastWest[cls.Southeast] = cls.Southwest

    cls.flipNorthSouth = genericNorthSouthFlip(cls)
    cls.flipNorthSouth[cls.Northeast] = cls.Southeast
    cls.flipNorthSouth[cls.Southeast] = cls.Northeast
    cls.flipNorthSouth[cls.Southwest] = cls.Northwest
    cls.flipNorthSouth[cls.Northwest] = cls.Southwest
    rotationClasses.append(cls)


generic8wayRotation(Rail)
Rail.rotateLeft[Rail.NorthSouth] = Rail.EastWest
Rail.rotateLeft[Rail.EastWest] = Rail.NorthSouth

Rail.roll = arange(16, dtype='uint8')
Rail.roll[Rail.North] = Rail.South


def applyBit(apply):
    def _applyBit(class_or_array):
        if hasattr(class_or_array, "rotateLeft"):
            for a in (class_or_array.flipEastWest,
                      class_or_array.flipNorthSouth,
                      class_or_array.rotateLeft):
                apply(a)
            if hasattr(class_or_array, "flipVertical"):
                apply(class_or_array.flipVertical)
            if hasattr(class_or_array, "roll"):
                apply(class_or_array.roll)
        else:
            array = class_or_array
            apply(array)

    return _applyBit


@applyBit
def applyBit8(array):
    array[8:16] = array[0:8] | 0x8


@applyBit
def applyBit4(array):
    array[4:8] = array[0:4] | 0x4
    array[12:16] = array[8:12] | 0x4


@applyBit
def applyBits48(array):
    array[4:8] = array[0:4] | 0x4
    array[8:16] = array[0:8] | 0x8


applyThrownBit = applyBit8


class PoweredDetectorRail(Rail):
    blocktypes = ['alphaMaterials.PoweredRail.ID', 'alphaMaterials.DetectorRail.ID', 'alphaMaterials.ActivatorRail.ID']


PoweredDetectorRail.rotateLeft = genericRotation(PoweredDetectorRail)

PoweredDetectorRail.rotateLeft[PoweredDetectorRail.NorthSouth] = PoweredDetectorRail.EastWest
PoweredDetectorRail.rotateLeft[PoweredDetectorRail.EastWest] = PoweredDetectorRail.NorthSouth

PoweredDetectorRail.flipEastWest = genericEastWestFlip(PoweredDetectorRail)
PoweredDetectorRail.flipNorthSouth = genericNorthSouthFlip(PoweredDetectorRail)
applyThrownBit(PoweredDetectorRail)
rotationClasses.append(PoweredDetectorRail)


class Lever(__Rotation):
    blocktypes = ['alphaMaterials.Lever.ID']
    ThrownBit = 0x8
    # DownSouth indicates floor lever pointing South in off state
    DownSouth = 0
    South = 1
    North = 2
    West = 3
    East = 4
    UpSouth = 5
    UpWest = 6
    DownWest = 7


Lever.rotateLeft = genericRotation(Lever)
Lever.rotateLeft[Lever.UpSouth] = Lever.UpWest
Lever.rotateLeft[Lever.UpWest] = Lever.UpSouth
Lever.rotateLeft[Lever.DownSouth] = Lever.DownWest
Lever.rotateLeft[Lever.DownWest] = Lever.DownSouth
Lever.flipEastWest = genericEastWestFlip(Lever)
Lever.flipNorthSouth = genericNorthSouthFlip(Lever)
Lever.flipVertical = arange(16, dtype='uint8')
Lever.flipVertical[Lever.UpSouth] = Lever.DownSouth
Lever.flipVertical[Lever.DownSouth] = Lever.UpSouth
Lever.flipVertical[Lever.UpWest] = Lever.DownWest
Lever.flipVertical[Lever.DownWest] = Lever.UpWest
Lever.roll = arange(16, dtype='uint8')
Lever.roll[Lever.North] = Lever.DownSouth
Lever.roll[Lever.South] = Lever.UpSouth
Lever.roll[Lever.DownSouth] = Lever.South
Lever.roll[Lever.DownWest] = Lever.South
Lever.roll[Lever.UpSouth] = Lever.North
Lever.roll[Lever.UpWest] = Lever.North

applyThrownBit(Lever)
rotationClasses.append(Lever)


@genericFlipRotation
class Button(__Rotation):
    blocktypes = ['alphaMaterials.Button.ID', 'alphaMaterials.WoodenButton.ID']
    PressedBit = 0x8
    Down = 0
    South = 1
    North = 2
    West = 3
    East = 4
    Up = 5

applyThrownBit(Button)


class SignPost(__Rotation):
    blocktypes = ['alphaMaterials.Sign.ID', 'alphaMaterials.MobHead.ID', 'alphaMaterials.StandingBanner.ID']

    South = 0
    SouthSouthWest = 1
    SouthWest = 2
    SouthWestWest = 3
    West = 4
    NorthWestWest = 5
    NorthWest = 6
    NorthNorthWest = 7
    North = 8
    NorthNorthEast = 9
    NorthEast = 10
    NorthEastEast = 11
    East = 12
    SouthEastEast = 13
    SouthEast = 14
    SouthSouthEast = 15
    
    #rotate by increasing clockwise
    rotateLeft = arange(16, dtype='uint8')
    rotateLeft -= 4
    rotateLeft &= 0xf

SignPost.flipNorthSouth = arange(16, dtype='uint8')
SignPost.flipNorthSouth[SignPost.East] = SignPost.West
SignPost.flipNorthSouth[SignPost.West] = SignPost.East
SignPost.flipNorthSouth[SignPost.SouthWestWest] = SignPost.SouthEastEast
SignPost.flipNorthSouth[SignPost.SouthEastEast] = SignPost.SouthWestWest
SignPost.flipNorthSouth[SignPost.SouthWest] = SignPost.SouthEast
SignPost.flipNorthSouth[SignPost.SouthEast] = SignPost.SouthWest
SignPost.flipNorthSouth[SignPost.SouthSouthWest] = SignPost.SouthSouthEast
SignPost.flipNorthSouth[SignPost.SouthSouthEast] = SignPost.SouthSouthWest
SignPost.flipNorthSouth[SignPost.NorthEastEast] = SignPost.NorthWestWest
SignPost.flipNorthSouth[SignPost.NorthWestWest] = SignPost.NorthEastEast
SignPost.flipNorthSouth[SignPost.NorthEast] = SignPost.NorthWest
SignPost.flipNorthSouth[SignPost.NorthWest] = SignPost.NorthEast
SignPost.flipNorthSouth[SignPost.NorthNorthEast] = SignPost.NorthNorthWest
SignPost.flipNorthSouth[SignPost.NorthNorthWest] = SignPost.NorthNorthEast


SignPost.flipEastWest = arange(16, dtype='uint8')
SignPost.flipEastWest[SignPost.North] = SignPost.South
SignPost.flipEastWest[SignPost.South] = SignPost.North
SignPost.flipEastWest[SignPost.SouthSouthEast] = SignPost.NorthNorthEast
SignPost.flipEastWest[SignPost.NorthNorthEast] = SignPost.SouthSouthEast
SignPost.flipEastWest[SignPost.NorthEast] = SignPost.SouthEast
SignPost.flipEastWest[SignPost.SouthEast] = SignPost.NorthEast
SignPost.flipEastWest[SignPost.SouthEastEast] = SignPost.NorthEastEast
SignPost.flipEastWest[SignPost.NorthEastEast] = SignPost.SouthEastEast
SignPost.flipEastWest[SignPost.NorthNorthWest] = SignPost.SouthSouthWest
SignPost.flipEastWest[SignPost.SouthSouthWest] = SignPost.NorthNorthWest
SignPost.flipEastWest[SignPost.NorthWest] = SignPost.SouthWest
SignPost.flipEastWest[SignPost.SouthWest] = SignPost.NorthWest
SignPost.flipEastWest[SignPost.NorthWestWest] = SignPost.SouthWestWest
SignPost.flipEastWest[SignPost.SouthWestWest] = SignPost.NorthWestWest

rotationClasses.append(SignPost)


class Bed(__Rotation):
    blocktypes = ['alphaMaterials.Bed.ID']
    West = 0
    North = 1
    East = 2
    South = 3


genericFlipRotation(Bed)
applyBit8(Bed)
applyBit4(Bed)


class EndPortal(__Rotation):
    blocktypes = ['alphaMaterials.PortalFrame.ID']
    West = 0
    North = 1
    East = 2
    South = 3


genericFlipRotation(EndPortal)
applyBit4(EndPortal)


class Door(__Rotation):
    blocktypes = [
        'alphaMaterials.IronDoor.ID',
        'alphaMaterials.WoodenDoor.ID',
        'alphaMaterials.SpruceDoor.ID',
        'alphaMaterials.BirchDoor.ID',
        'alphaMaterials.JungleDoor.ID',
        'alphaMaterials.AcaciaDoor.ID',
        'alphaMaterials.DarkOakDoor.ID',
        'alphaMaterials.WoodenDoor.ID',
    ]
    South = 0
    West = 1
    North = 2
    East = 3
    SouthOpen = 4
    WestOpen = 5
    NorthOpen = 6
    EastOpen = 7
    Left = 8
    Right = 9

    rotateLeft = arange(16, dtype='uint8')

Door.rotateLeft[Door.South] = Door.West
Door.rotateLeft[Door.West] = Door.North
Door.rotateLeft[Door.North] = Door.East
Door.rotateLeft[Door.East] = Door.South
Door.rotateLeft[Door.SouthOpen] = Door.WestOpen
Door.rotateLeft[Door.WestOpen] = Door.NorthOpen
Door.rotateLeft[Door.NorthOpen] = Door.EastOpen
Door.rotateLeft[Door.EastOpen] = Door.SouthOpen
    
#applyBit4(Door.rotateLeft)

Door.flipEastWest = arange(16, dtype='uint8')
Door.flipEastWest[Door.Left] = Door.Right
Door.flipEastWest[Door.Right] = Door.Left
Door.flipEastWest[Door.East] = Door.West
Door.flipEastWest[Door.West] = Door.East
Door.flipEastWest[Door.EastOpen] = Door.WestOpen
Door.flipEastWest[Door.WestOpen] = Door.EastOpen

Door.flipNorthSouth = arange(16, dtype='uint8')
Door.flipNorthSouth[Door.Left] = Door.Right
Door.flipNorthSouth[Door.Right] = Door.Left
Door.flipNorthSouth[Door.North] = Door.South
Door.flipNorthSouth[Door.South] = Door.North
Door.flipNorthSouth[Door.NorthOpen] = Door.SouthOpen
Door.flipNorthSouth[Door.SouthOpen] = Door.NorthOpen

rotationClasses.append(Door)


class Log(__Rotation):
    blocktypes = [
        'alphaMaterials.Wood.ID',
        'alphaMaterials.Wood2.ID',
    ]
    Type1Up = 0
    Type2Up = 1
    Type3Up = 2
    Type4Up = 3
    Type1NorthSouth = 4
    Type2NorthSouth = 5
    Type3NorthSouth = 6
    Type4NorthSouth = 7
    Type1EastWest = 8
    Type2EastWest = 9
    Type3EastWest = 10
    Type4EastWest = 11  
    
Log.rotateLeft = arange(16, dtype='uint8')
Log.rotateLeft[Log.Type1NorthSouth] = Log.Type1EastWest
Log.rotateLeft[Log.Type1EastWest] = Log.Type1NorthSouth
Log.rotateLeft[Log.Type2NorthSouth] = Log.Type2EastWest
Log.rotateLeft[Log.Type2EastWest] = Log.Type2NorthSouth
Log.rotateLeft[Log.Type3NorthSouth] = Log.Type3EastWest
Log.rotateLeft[Log.Type3EastWest] = Log.Type3NorthSouth
Log.rotateLeft[Log.Type4NorthSouth] = Log.Type4EastWest
Log.rotateLeft[Log.Type4EastWest] = Log.Type4NorthSouth

Log.roll = arange(16, dtype='uint8')
Log.roll[Log.Type1NorthSouth] = Log.Type1Up
Log.roll[Log.Type2NorthSouth] = Log.Type2Up
Log.roll[Log.Type3NorthSouth] = Log.Type3Up
Log.roll[Log.Type4NorthSouth] = Log.Type4Up

Log.roll[Log.Type1Up] = Log.Type1NorthSouth
Log.roll[Log.Type2Up] = Log.Type2NorthSouth
Log.roll[Log.Type3Up] = Log.Type3NorthSouth
Log.roll[Log.Type4Up] = Log.Type4NorthSouth

rotationClasses.append(Log)


class RedstoneRepeater(__Rotation):
    blocktypes = [
        'alphaMaterials.RedstoneRepeaterOff.ID',
        'alphaMaterials.RedstoneRepeaterOn.ID'
    ]

    East = 0
    South = 1
    West = 2
    North = 3


genericFlipRotation(RedstoneRepeater)

#high bits of the repeater indicate repeater delay, and should be preserved
applyBits48(RedstoneRepeater)


class Trapdoor(__Rotation):
    blocktypes = ['alphaMaterials.Trapdoor.ID', 'alphaMaterials.IronTrapdoor.ID']

    West = 0
    East = 1
    South = 2
    North = 3
    TopWest = 4
    TopEast = 5
    TopSouth = 6
    TopNorth = 7


genericFlipRotation(Trapdoor)
applyOpenedBit = applyBit8
applyOpenedBit(Trapdoor)


class PistonBody(__Rotation):
    blocktypes = ['alphaMaterials.StickyPiston.ID', 'alphaMaterials.Piston.ID']

    Down = 0
    Up = 1
    East = 2
    West = 3
    North = 4
    South = 5

genericRoll(PistonBody)
genericFlipRotation(PistonBody)
applyPistonBit = applyBit8
applyPistonBit(PistonBody)


class PistonHead(PistonBody):
    blocktypes = ['alphaMaterials.PistonHead.ID']


rotationClasses.append(PistonHead)


#Mushroom types:
#Value     Description     Textures
#0     Fleshy piece     Pores on all sides
#1     Corner piece     Cap texture on top, directions 1 (cloud direction) and 2 (sunrise)
#2     Side piece     Cap texture on top and direction 2 (sunrise)
#3     Corner piece     Cap texture on top, directions 2 (sunrise) and 3 (cloud origin)
#4     Side piece     Cap texture on top and direction 1 (cloud direction)
#5     Top piece     Cap texture on top
#6     Side piece     Cap texture on top and direction 3 (cloud origin)
#7     Corner piece     Cap texture on top, directions 0 (sunset) and 1 (cloud direction)
#8     Side piece     Cap texture on top and direction 0 (sunset)
#9     Corner piece     Cap texture on top, directions 3 (cloud origin) and 0 (sunset)
#10     Stem piece     Stem texture on all four sides, pores on top and bottom


class HugeMushroom(__Rotation):
    blocktypes = ['alphaMaterials.HugeRedMushroom.ID', 'alphaMaterials.HugeBrownMushroom.ID']
    Northeast = 1
    East = 2
    Southeast = 3
    South = 6
    Southwest = 9
    West = 8
    Northwest = 7
    North = 4


generic8wayRotation(HugeMushroom)
HugeMushroom.roll = arange(16, dtype='uint8')
HugeMushroom.roll[HugeMushroom.Southeast] = HugeMushroom.Northeast
HugeMushroom.roll[HugeMushroom.South] = HugeMushroom.North
HugeMushroom.roll[HugeMushroom.Southwest] = HugeMushroom.Northwest


class Vines(__Rotation):
    blocktypes = ['alphaMaterials.Vines.ID']

    WestBit = 1
    NorthBit = 2
    EastBit = 4
    SouthBit = 8

    rotateLeft = arange(16, dtype='uint8')
    flipEastWest = arange(16, dtype='uint8')
    flipNorthSouth = arange(16, dtype='uint8')

#Hmm... Since each bit is a direction, we can rotate by shifting!
Vines.rotateLeft = 0xf & ((Vines.rotateLeft >> 1) | (Vines.rotateLeft << 3))
# Wherever each bit is set, clear it and set the opposite bit
EastWestBits = (Vines.EastBit | Vines.WestBit)
Vines.flipEastWest[(Vines.flipEastWest & EastWestBits) > 0] ^= EastWestBits

NorthSouthBits = (Vines.NorthBit | Vines.SouthBit)
Vines.flipNorthSouth[(Vines.flipNorthSouth & NorthSouthBits) > 0] ^= NorthSouthBits

rotationClasses.append(Vines)


class Anvil(__Rotation):
    blocktypes = ['alphaMaterials.Anvil.ID']

    East = 0
    South = 1
    West = 2
    North = 3


genericFlipRotation(Anvil)
applyAnvilBit = applyBit8
applyAnvilBit(Anvil)


@genericFlipRotation
class Hay(__Rotation):
    blocktypes = ['alphaMaterials.HayBlock.ID']

    Up = 0
    Down = 0
    East = 8
    West = 8
    North = 4
    South = 4


@genericFlipRotation
class QuartzPillar(__Rotation):
    blocktypes = ['alphaMaterials.BlockofQuartz.ID']

    Up = 2
    Down = 2
    East = 4
    West = 4
    North = 3
    South = 3


@genericFlipRotation
class PurpurPillar(__Rotation):
    blocktypes = ['alphaMaterials.PurpurPillar.ID']

    Up = 0
    Down = 0
    East = 8
    West = 8
    North = 4
    South = 4


@genericFlipRotation
class NetherPortal(__Rotation):
    blocktypes = ['alphaMaterials.NetherPortal.ID']

    East = 1
    West = 1
    North = 2
    South = 2


class FenceGate(__Rotation):
    blocktypes = ['materials.alphaMaterials.FenceGate.ID',
                  'materials.alphaMaterials.SpruceFenceGate.ID',
                  'materials.alphaMaterials.BirchFenceGate.ID',
                  'materials.alphaMaterials.JungleFenceGate.ID',
                  'materials.alphaMaterials.DarkOakFenceGate.ID',
                  'materials.alphaMaterials.AcaciaFenceGate.ID']

    South = 1
    West = 2
    North = 3
    East = 0

genericFlipRotation(FenceGate)
applyFenceGateBits = applyBits48
applyFenceGateBits(FenceGate)


@genericFlipRotation
class EnderPortal(__Rotation):
    blocktypes = ['alphaMaterials.EnderPortal.ID']

    South = 0
    West = 1
    North = 2
    East = 3


@genericFlipRotation
class CocoaPlant(__Rotation):
    blocktypes = ['alphaMaterials.CocoaPlant.ID']

    North = 0
    East = 1
    South = 2
    West = 3


applyBits48(CocoaPlant)  # growth state

@genericFlipRotation
class TripwireHook(__Rotation):
    blocktypes = ['alphaMaterials.TripwireHook.ID']

    South = 1
    West = 2
    North = 3
    East = 0

applyBits48(TripwireHook)

@genericFlipRotation

class MobHead(__Rotation):
    blocktypes = ['alphaMaterials.MobHead.ID']

    East = 2
    West = 3
    North = 4
    South = 5


@genericFlipRotation
class Hopper(__Rotation):
    blocktypes = ['alphaMaterials.Hopper.ID']
    Down = 0
    East = 2
    West = 3
    North = 4
    South = 5

applyBit8(Hopper)
Hopper.roll = arange(16, dtype='uint8')
Hopper.roll[Hopper.Down] = Hopper.South
Hopper.roll[Hopper.North] = Hopper.Down


@genericFlipRotation
class DropperCommandblock(__Rotation):
    blocktypes = [
        'alphaMaterials.Dropper.ID', 
        'alphaMaterials.Dispenser.ID', 
        'alphaMaterials.CommandBlock.ID',
        'alphaMaterials.CommandBlockRepeating.ID', 
        'alphaMaterials.CommandBlockChain.ID'
    ]
    Down = 0
    Up = 1
    East = 2
    West = 3
    North = 4
    South = 5

applyBit8(DropperCommandblock)


@genericFlipRotation 
class RedstoneComparator(__Rotation):
    blocktypes = ['alphaMaterials.RedstoneComparatorInactive.ID', 'alphaMaterials.RedstoneComparatorActive.ID']

    East = 0
    South = 1
    West = 2
    North = 3


applyBits48(RedstoneComparator)


@genericFlipRotation
class EndRod(__Rotation):
    blocktypes = ['alphaMaterials.EndRod.ID']
    Down = 0
    Up = 1
    East = 2
    West = 3
    North = 4
    South = 5

def _get_attribute(obj, attr):
    # Helper function used to get arbitrary attribute from an arbitrary object.
    if hasattr(obj, attr):
        return getattr(obj, attr)
    else:
        raise AttributeError("Object {0} does not have attribute '{1}".format(obj, attr))

def masterRotationTable(attrname):
    # compute a materials.id_limitx16 table mapping each possible blocktype/data combination to
    # the resulting data when the block is rotated
    table = zeros((materials.id_limit, 16), dtype='uint8')
    table[:] = arange(16, dtype='uint8')
    for cls in rotationClasses:
        if hasattr(cls, attrname):
            blocktable = getattr(cls, attrname)
            for blocktype in cls.blocktypes:
                print type(blocktable)
                # Very bad stuff here...
                try:
                    table[blocktype] = blocktable
                except (NameError, ValueError) as e:
                    try:
                        table[eval(blocktype)] = blocktable
                    except (NameError, SyntaxError):
                        raise_malformed = False
                        res = re.findall(r"^([a-zA-Z_][,a-zA-Z0-9._]*)[ ]+for[ ]+([(a-zA-Z_][, a-zA-Z0-9_.)]*)[ ]+in[ ]+([a-zA-Z_][,a-zA-Z0-9._]*)$", blocktype)
                        if res and len(res[0]) == 3:
                            # No function call is made in 'bolcktype', so we don't need to check for them.
                            # Only 'stuff for stuff in other_stuff' is used.
                            # 'res[0]' is split in 3 elements: left part of 'for', inner part between 'for'and 'in', and right part of 'in'
                            # Let define 'left' is the left part of 'for', 'right' is the inner part between 'for'and 'in', and 'iter_obj' the right part of 'in'.

                            # If the 'left' and 'right' are the same, check 'iter_obj' for nested attributes (like in 'a for a in b.c.d')

                            # If 'left' and 'right' aren't the same, check if 'left' is using calls to attributes (like in 'a.b for a in c')
                            # If yes, check the 'iter_obj for nested attributes.

                            # To not write repeated code, let use variables to store the status of each of the three elements.

                            left, right, iter_obj = res[0]
                            left_valid = False
                            right_valid = False
                            iter_obj_valid = False

                            # Test 'right' first, since calling attribute on this element in 'for' loops is invalid in Python.
                            if '.' in right:
                                SyntaxError("Malformed string: %s. Calling attributes on the right of 'for' is invalid." % blocktype)

                            # Test 'iter_obj'.
                            _iter_obj, _o_str = iter_obj.split('.', 1)
                            if _iter_obj in globals().keys():
                                iter_obj = globals()[_iter_obj]
                                while '.' in _o_str:
                                    _iter_obj, _ostr = _ostr.split('.')
                                    iter_obj = getattr(iter_obj, _iter_obj)

                            # Test 'left'.
                            left_name, left_attrs = left.split('.')
                            if left_name != right:
                                SyntaxError("Malformed string: '%s'" % blocktype)

                            # All checks passed, we can proceed the loop.
                            if left_attrs:
                                [table[eval('a.%s' % left_attrs)] for a in iter_obj]
                                print table
                            else:
                                table[blocktype] = [a for a in iter_obj]

                        else:
                            raise_malformed = True
                        if raise_malformed:
                            raise SyntaxError("Malformed string: %s" % blocktype)

    return table


def rotationTypeTable():
    table = {}
    for cls in rotationClasses:
        for b in cls.blocktypes:
            table[b] = cls

    return table


class BlockRotation:
    def __init__(self):
        self.rotateLeft = masterRotationTable("rotateLeft")
        self.flipEastWest = masterRotationTable("flipEastWest")
        self.flipNorthSouth = masterRotationTable("flipNorthSouth")
        self.flipVertical = masterRotationTable("flipVertical")
        self.roll = masterRotationTable("roll")
        self.typeTable = rotationTypeTable()


def SameRotationType(blocktype1, blocktype2):
    #use different default values for typeTable.get() to make it return false when neither blocktype is present
    return BlockRotation().typeTable.get(blocktype1.ID) == BlockRotation().typeTable.get(blocktype2.ID, BlockRotation())


def FlipVertical(blocks, data):
    data[:] = BlockRotation().flipVertical[blocks, data]


def FlipNorthSouth(blocks, data):
    data[:] = BlockRotation().flipNorthSouth[blocks, data]


def FlipEastWest(blocks, data):
    data[:] = BlockRotation().flipEastWest[blocks, data]


def RotateLeft(blocks, data):
    data[:] = BlockRotation().rotateLeft[blocks, data]


def Roll(blocks, data):
    data[:] = BlockRotation().roll[blocks, data]