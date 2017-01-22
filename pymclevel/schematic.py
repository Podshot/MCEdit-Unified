'''
Created on Jul 22, 2011

@author: Rio
'''
import atexit
from contextlib import closing
import os
import shutil
import zipfile
from logging import getLogger

import blockrotation
from box import BoundingBox
import infiniteworld
from level import MCLevel, EntityLevel
from materials import alphaMaterials, MCMaterials, namedMaterials, blockstateToID
from mclevelbase import exhaust
import nbt
from numpy import array, swapaxes, uint8, zeros, resize, ndenumerate
from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
from pymclevel.materials import BlockstateAPI
from release import TAG as RELEASE_TAG
import math
import copy

log = getLogger(__name__)

__all__ = ['MCSchematic', 'INVEditChest', 'StructureNBT']

DEBUG = True


class MCSchematic(EntityLevel):
    materials = alphaMaterials

    def __init__(self, shape=None, root_tag=None, filename=None, mats='Alpha'):
        """ shape is (x,y,z) for a new level's shape.  if none, takes
        root_tag as a TAG_Compound for an existing schematic file.  if
        none, tries to read the tag from filename.  if none, results
        are undefined. materials can be a MCMaterials instance, or one of
        "Classic", "Alpha", "Pocket" to indicate allowable blocks. The default
        is Alpha.

        block coordinate order in the file is y,z,x to use the same code as classic/indev levels.
        in hindsight, this was a completely arbitrary decision.

        the Entities and TileEntities are nbt.TAG_List objects containing TAG_Compounds.
        this makes it easy to copy entities without knowing about their insides.

        rotateLeft swaps the axes of the different arrays.  because of this, the Width, Height, and Length
        reflect the current dimensions of the schematic rather than the ones specified in the NBT structure.
        I'm not sure what happens when I try to re-save a rotated schematic.
        """

        if DEBUG: log.debug(u"Creating scematic.")
        if filename:
            if DEBUG: log.debug(u"Using %s"%filename)
            self.filename = filename
            if None is root_tag and os.path.exists(filename):
                root_tag = nbt.load(filename)
                if DEBUG: log.debug(u"%s loaded."%filename)
        else:
            self.filename = None

        if mats in namedMaterials:
            if DEBUG: log.debug(u"Using named materials.")
            self.materials = namedMaterials[mats]
        else:
            assert (isinstance(mats, MCMaterials))
            self.materials = mats

        if root_tag:
            self.root_tag = root_tag
            if DEBUG: log.debug(u"Processing materials.")
            if "Materials" in root_tag:
                self.materials = namedMaterials[self.Materials]
            else:
                root_tag["Materials"] = nbt.TAG_String(self.materials.name)

            if DEBUG: log.debug(u"Processing size.")
            w = self.root_tag["Width"].value
            l = self.root_tag["Length"].value
            h = self.root_tag["Height"].value

            if DEBUG: log.debug(u"Reshaping blocks.")
            self._Blocks = self.root_tag["Blocks"].value.astype('uint16').reshape(h, l, w)  # _Blocks is y, z, x
            del self.root_tag["Blocks"]
            if "AddBlocks" in self.root_tag:
                if DEBUG: log.debug(u"Processing AddBlocks.")
                # Use WorldEdit's "AddBlocks" array to load and store the 4 high bits of a block ID.
                # Unlike Minecraft's NibbleArrays, this array stores the first block's bits in the
                # 4 high bits of the first byte.

                size = (h * l * w)

                # If odd, add one to the size to make sure the adjacent slices line up.
                add = zeros(size + (size & 1), 'uint16')

                # Fill the even bytes with data
                add[::2] = self.root_tag["AddBlocks"].value

                # Copy the low 4 bits to the odd bytes
                add[1::2] = add[::2] & 0xf

                # Shift the even bytes down
                add[::2] >>= 4

                # Shift every byte up before merging it with Blocks
                add <<= 8
                self._Blocks |= add[:size].reshape(h, l, w)
                del self.root_tag["AddBlocks"]

            self.root_tag["Data"].value = self.root_tag["Data"].value.reshape(h, l, w)

            if "Biomes" in self.root_tag:
                if DEBUG: log.debug(u"Processing Biomes.")
                self.root_tag["Biomes"].value.shape = (l, w)

        else:
            if DEBUG: log.debug(u"No root tag found, creating a blank schematic.")
            assert shape is not None
            root_tag = nbt.TAG_Compound(name="Schematic")
            root_tag["Height"] = nbt.TAG_Short(shape[1])
            root_tag["Length"] = nbt.TAG_Short(shape[2])
            root_tag["Width"] = nbt.TAG_Short(shape[0])

            root_tag["Entities"] = nbt.TAG_List()
            root_tag["TileEntities"] = nbt.TAG_List()
            root_tag["TileTicks"] = nbt.TAG_List()
            root_tag["Materials"] = nbt.TAG_String(self.materials.name)

            self._Blocks = zeros((shape[1], shape[2], shape[0]), 'uint16')
            root_tag["Data"] = nbt.TAG_Byte_Array(zeros((shape[1], shape[2], shape[0]), uint8))

            root_tag["Biomes"] = nbt.TAG_Byte_Array(zeros((shape[2], shape[0]), uint8))

            self.root_tag = root_tag

        self.root_tag["Data"].value &= 0xF  # discard high bits

    def saveToFile(self, filename=None):
        """ save to file named filename, or use self.filename.  XXX NOT THREAD SAFE AT ALL. """
        if filename is None:
            filename = self.filename
        if filename is None:
            raise IOError, u"Attempted to save an unnamed schematic in place"

        self.Materials = self.materials.name

        self.root_tag["Blocks"] = nbt.TAG_Byte_Array(self._Blocks.astype('uint8'))

        add = self._Blocks >> 8
        if add.any():
            # WorldEdit AddBlocks compatibility.
            # The first 4-bit value is stored in the high bits of the first byte.

            # Increase odd size by one to align slices.
            packed_add = zeros(add.size + (add.size & 1), 'uint8')
            packed_add[:add.size] = add.ravel()

            # Shift even bytes to the left
            packed_add[::2] <<= 4

            # Merge odd bytes into even bytes
            packed_add[::2] |= packed_add[1::2]

            # Save only the even bytes, now that they contain the odd bytes in their lower bits.
            packed_add = packed_add[0::2]
            self.root_tag["AddBlocks"] = nbt.TAG_Byte_Array(packed_add)

        with open(filename, 'wb') as chunkfh:
            self.root_tag.save(chunkfh)

        del self.root_tag["Blocks"]
        self.root_tag.pop("AddBlocks", None)

    def __str__(self):
        return u"MCSchematic(shape={0}, materials={2}, filename=\"{1}\")".format(self.size, self.filename or u"",
                                                                                 self.Materials)

    # these refer to the blocks array instead of the file's height because rotation swaps the axes
    # this will have an impact later on when editing schematics instead of just importing/exporting
    @property
    def Length(self):
        return self.Blocks.shape[1]

    @property
    def Width(self):
        return self.Blocks.shape[0]

    @property
    def Height(self):
        return self.Blocks.shape[2]

    @property
    def Blocks(self):
        return swapaxes(self._Blocks, 0, 2)

    @property
    def Data(self):
        return swapaxes(self.root_tag["Data"].value, 0, 2)

    @property
    def Entities(self):
        return self.root_tag["Entities"]

    @property
    def TileEntities(self):
        return self.root_tag["TileEntities"]

    @property
    def TileTicks(self):
        if "TileTicks" in self.root_tag:
            return self.root_tag["TileTicks"]
        else:
            self.root_tag["TileTicks"] = nbt.TAG_List()
            return self.root_tag["TileTicks"]

    @property
    def Materials(self):
        return self.root_tag["Materials"].value

    @Materials.setter
    def Materials(self, val):
        if "Materials" not in self.root_tag:
            self.root_tag["Materials"] = nbt.TAG_String()
        self.root_tag["Materials"].value = val

    @property
    def Biomes(self):
        return swapaxes(self.root_tag["Biomes"].value, 0, 1)

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "Schematic" == root_tag.name

    def _update_shape(self):
        root_tag = self.root_tag
        shape = self.Blocks.shape
        root_tag["Height"] = nbt.TAG_Short(shape[2])
        root_tag["Length"] = nbt.TAG_Short(shape[1])
        root_tag["Width"] = nbt.TAG_Short(shape[0])

    def rotateLeftBlocks(self):
        """
        rotateLeft the blocks direction without there location
        """
        blockrotation.RotateLeft(self.Blocks, self.Data)

    def rotateLeft(self):
        self._fakeEntities = None
        self._Blocks = swapaxes(self._Blocks, 1, 2)[:, ::-1, :]  # x=z; z=-x
        if "Biomes" in self.root_tag:
            self.root_tag["Biomes"].value = swapaxes(self.root_tag["Biomes"].value, 0, 1)[::-1, :]

        self.root_tag["Data"].value = swapaxes(self.root_tag["Data"].value, 1, 2)[:, ::-1, :]  # x=z; z=-x
        self._update_shape()

        blockrotation.RotateLeft(self.Blocks, self.Data)

        log.info(u"Relocating entities...")
        for entity in self.Entities:
            for p in "Pos", "Motion":
                if p == "Pos":
                    zBase = self.Length
                else:
                    zBase = 0.0
                newX = entity[p][2].value
                newZ = zBase - entity[p][0].value

                entity[p][0].value = newX
                entity[p][2].value = newZ
            entity["Rotation"][0].value -= 90.0
            if entity["id"].value in ("Painting", "ItemFrame") or MCEDIT_IDS.get(entity["id"]) in ('DEFS_ENTITIES_PAINTING', 'DEFS_ENTITIES_ITEM_FRAME'):
                x, z = entity["TileX"].value, entity["TileZ"].value
                newx = z
                newz = self.Length - x - 1

                entity["TileX"].value, entity["TileZ"].value = newx, newz
                facing = entity.get("Facing", entity.get("Direction"))
                if facing is None:
                    dirFacing = entity.get("Dir")
                    if dirFacing is not None:
                        if dirFacing.value == 0:
                            dirFacing.value = 2
                        elif dirFacing.value == 2:
                            dirFacing.value = 0
                        facing = dirFacing
                    else:
                        raise Exception("None of tags Facing/Direction/Dir found in entity %s during rotating -  %r" % (entity["id"].value, entity))
                facing.value = (facing.value - 1) % 4

        for tileEntity in self.TileEntities:
            if 'x' not in tileEntity:
                continue

            newX = tileEntity["z"].value
            newZ = self.Length - tileEntity["x"].value - 1

            tileEntity["x"].value = newX
            tileEntity["z"].value = newZ

        if "TileTicks" in self.root_tag:
            for tileTick in self.TileTicks:
                newX = tileTick["z"].value
                newZ = tileTick["x"].value

                tileTick["x"].value = newX
                tileTick["z"].value = newZ

    def rollBlocks(self):
        """
        rolls the blocks direction without the block location
        """
        blockrotation.Roll(self.Blocks, self.Data)

    def roll(self):
        " xxx rotate stuff - destroys biomes"
        self.root_tag.pop('Biomes', None)
        self._fakeEntities = None

        self._Blocks = swapaxes(self._Blocks, 2, 0)[:, :, ::-1]  # x=y; y=-x
        self.root_tag["Data"].value = swapaxes(self.root_tag["Data"].value, 2, 0)[:, :, ::-1]
        self._update_shape()

        blockrotation.Roll(self.Blocks, self.Data)

        log.info(u"N/S Roll: Relocating entities...")
        for i, entity in enumerate(self.Entities):
            newX = self.Width - entity["Pos"][1].value
            newY = entity["Pos"][0].value
            entity["Pos"][0].value = newX
            entity["Pos"][1].value = newY
            newX = entity["Motion"][1].value
            newY = -entity["Motion"][0].value
            entity["Motion"][0].value = newX
            entity["Motion"][1].value = newY
            # I think this is right
            # Although rotation isn't that important as most entities can't rotate and mobs
            # don't serialize rotation.
            newX = entity["Rotation"][1].value
            newY = -entity["Rotation"][0].value
            entity["Rotation"][0].value = newX
            entity["Rotation"][1].value = newY

            if entity["id"].value in ("Painting", "ItemFrame") or MCEDIT_IDS.get(entity["id"]) in ('DEFS_ENTITIES_PAINTING', 'DEFS_ENTITIES_ITEM_FRAME'):
                newX = self.Width - entity["TileY"].value - 1
                newY = entity["TileX"].value
                entity["TileX"].value = newX
                entity["TileY"].value = newY

        for tileEntity in self.TileEntities:
            newX = self.Width - tileEntity["y"].value - 1
            newY = tileEntity["x"].value
            tileEntity["x"].value = newX
            tileEntity["y"].value = newY
        if hasattr(self, "TileTicks"):
            for tileTick in self.TileTicks:
                newX = self.Width - tileTick["y"].value - 1
                newY = tileTick["x"].value
                tileTick["x"].value = newX
                tileTick["y"].value = newY

    def flipVerticalBlocks(self):
        blockrotation.FlipVertical(self.Blocks, self.Data)

    def flipVertical(self):
        " xxx delete stuff "
        self._fakeEntities = None

        blockrotation.FlipVertical(self.Blocks, self.Data)
        self._Blocks = self._Blocks[::-1, :, :]  # y=-y
        self.root_tag["Data"].value = self.root_tag["Data"].value[::-1, :, :]

        log.info(u"N/S Flip: Relocating entities...")
        for entity in self.Entities:
            entity["Pos"][1].value = self.Height - entity["Pos"][1].value
            entity["Motion"][1].value = -entity["Motion"][1].value
            entity["Rotation"][1].value = -entity["Rotation"][1].value
            if entity["id"].value in ("Painting", "ItemFrame") or MCEDIT_IDS.get(entity["id"]) in ('DEFS_ENTITIES_PAINTING', 'DEFS_ENTITIES_ITEM_FRAME'):
                entity["TileY"].value = self.Height - entity["TileY"].value - 1
        for tileEntity in self.TileEntities:
            tileEntity["y"].value = self.Height - tileEntity["y"].value - 1
        if "TileTicks" in self.root_tag:
            for tileTick in self.TileTicks:
                tileTick["y"].value = self.Height - tileTick["y"].value - 1

    # Width of paintings
    paintingMap = {'Kebab': 1,
                   'Aztec': 1,
                   'Alban': 1,
                   'Aztec2': 1,
                   'Bomb': 1,
                   'Plant': 1,
                   'Wasteland': 1,
                   'Wanderer': 1,
                   'Graham': 1,
                   'Pool': 2,
                   'Courbet': 2,
                   'Sunset': 2,
                   'Sea': 2,
                   'Creebet': 2,
                   'Match': 2,
                   'Stage': 2,
                   'Void': 2,
                   'SkullAndRoses': 2,
                   'Wither': 2,
                   'Fighters': 4,
                   'Skeleton': 4,
                   'DonkeyKong': 4,
                   'Pointer': 4,
                   'Pigscene': 4,
                   'BurningSkull': 4}

    def flipNorthSouthBlocks(self):
        blockrotation.FlipNorthSouth(self.Blocks, self.Data)

    def flipNorthSouth(self):
        if "Biomes" in self.root_tag:
            self.root_tag["Biomes"].value = self.root_tag["Biomes"].value[::-1, :]

        self._fakeEntities = None

        blockrotation.FlipNorthSouth(self.Blocks, self.Data)
        self._Blocks = self._Blocks[:, :, ::-1]  # x=-x
        self.root_tag["Data"].value = self.root_tag["Data"].value[:, :, ::-1]

        northSouthPaintingMap = [0, 3, 2, 1]

        log.info(u"N/S Flip: Relocating entities...")
        for entity in self.Entities:

            try:
                entity["Pos"][0].value = self.Width - entity["Pos"][0].value
            except:
                pass
            try:
                entity["Motion"][0].value = -entity["Motion"][0].value
            except:
                pass

            try:
                entity["Rotation"][0].value *= -1.0
            except:
                pass

            # Special logic for old width painting as TileX/TileZ favours -x/-z

            try:
                if entity["id"].value in ("Painting", "ItemFrame") or MCEDIT_IDS.get(entity["id"]) in ('DEFS_ENTITIES_PAINTING', 'DEFS_ENTITIES_ITEM_FRAME'):
                    facing = entity.get("Facing", entity.get("Direction"))
                    if facing is None:
                        dirFacing = entity.get("Dir")
                        if dirFacing is not None:
                            if dirFacing.value == 0:
                                dirFacing.value = 2
                            elif dirFacing.value == 2:
                                dirFacing.value = 0
                            facing = dirFacing
                        else:
                            raise Exception("None of tags Facing/Direction/Dir found in entity %s during flipping -  %r" % (entity["id"].value, entity))

                if entity["id"].value == "Painting" or MCEDIT_IDS.get(entity["id"]) == 'DEFS_ENTITIES_PAINTING':
                    if facing.value == 2:
                        entity["TileX"].value = self.Width - entity["TileX"].value - self.paintingMap[entity["Motive"].value] % 2
                    elif facing.value == 0:
                        entity["TileX"].value = self.Width - entity["TileX"].value - 2 + self.paintingMap[entity["Motive"].value] % 2
                    else:
                        entity["TileX"].value = self.Width - entity["TileX"].value - 1
                    if facing.value == 3:
                        entity["TileZ"].value = entity["TileZ"].value - 1 + self.paintingMap[entity["Motive"].value] % 2
                    elif facing.value == 1:
                        entity["TileZ"].value = entity["TileZ"].value + 1 - self.paintingMap[entity["Motive"].value] % 2
                    facing.value = northSouthPaintingMap[facing.value]
                elif entity["id"].value == "ItemFrame" or MCEDIT_IDS.get(entity["id"]) == 'DEFS_ENTITIES_ITEM_FRAME':
                    entity["TileX"].value = self.Width - entity["TileX"].value - 1
                    facing.value = northSouthPaintingMap[facing.value]
            except:
                pass
        for tileEntity in self.TileEntities:
            if 'x' not in tileEntity:
                continue

            tileEntity["x"].value = self.Width - tileEntity["x"].value - 1

        if "TileTicks" in self.root_tag:
            for tileTick in self.TileTicks:
                tileTick["x"].value = self.Width - tileTick["x"].value - 1

    def flipEastWestBlocks(self):
        blockrotation.FlipEastWest(self.Blocks, self.Data)

    def flipEastWest(self):
        if "Biomes" in self.root_tag:
            self.root_tag["Biomes"].value = self.root_tag["Biomes"].value[:, ::-1]

        self._fakeEntities = None

        blockrotation.FlipEastWest(self.Blocks, self.Data)
        self._Blocks = self._Blocks[:, ::-1, :]  # z=-z
        self.root_tag["Data"].value = self.root_tag["Data"].value[:, ::-1, :]

        eastWestPaintingMap = [2, 1, 0, 3]

        log.info(u"E/W Flip: Relocating entities...")
        for entity in self.Entities:

            try:
                entity["Pos"][2].value = self.Length - entity["Pos"][2].value
            except:
                pass
            try:
                entity["Motion"][2].value = -entity["Motion"][2].value
            except:
                pass

            try:
                entity["Rotation"][0].value = entity["Rotation"][0].value * -1.0 + 180
            except:
                pass

            # Special logic for old width painting as TileX/TileZ favours -x/-z

            try:
                if entity["id"].value in ("Painting", "ItemFrame") or MCEDIT_IDS.get(entity["id"]) in ('DEFS_ENTITIES_PAINTING', 'DEFS_ENTITIES_ITEM_FRAME'):
                    facing = entity.get("Facing", entity.get("Direction"))
                    if facing is None:
                        dirFacing = entity.get("Dir")
                        if dirFacing is not None:
                            if dirFacing.value == 0:
                                dirFacing.value = 2
                            elif dirFacing.value == 2:
                                dirFacing.value = 0
                            facing = dirFacing
                        else:
                            raise Exception("None of tags Facing/Direction/Dir found in entity %s during flipping -  %r" % (entity["id"].value, entity))

                if entity["id"].value == "Painting" or MCEDIT_IDS.get(entity["id"]) == 'DEFS_ENTITIES_PAINTING':
                    if facing.value == 1:
                        entity["TileZ"].value = self.Length - entity["TileZ"].value - 2 + self.paintingMap[entity["Motive"].value] % 2
                    elif facing.value == 3:
                        entity["TileZ"].value = self.Length - entity["TileZ"].value - self.paintingMap[entity["Motive"].value] % 2
                    else:
                        entity["TileZ"].value = self.Length - entity["TileZ"].value - 1
                    if facing.value == 0:
                        entity["TileX"].value = entity["TileX"].value + 1 - self.paintingMap[entity["Motive"].value] % 2
                    elif facing.value == 2:
                        entity["TileX"].value = entity["TileX"].value - 1 + self.paintingMap[entity["Motive"].value] % 2
                    facing.value = eastWestPaintingMap[facing.value]
                elif entity["id"].value == "ItemFrame" or MCEDIT_IDS.get(entity["id"]) == 'DEFS_ENTITIES_ITEM_FRAME':
                    entity["TileZ"].value = self.Length - entity["TileZ"].value - 1
                    facing.value = eastWestPaintingMap[facing.value]
            except:
                pass

        for tileEntity in self.TileEntities:
            tileEntity["z"].value = self.Length - tileEntity["z"].value - 1

        if "TileTicks" in self.root_tag:
            for tileTick in self.TileTicks:
                tileTick["z"].value = self.Length - tileTick["z"].value - 1

    def setBlockDataAt(self, x, y, z, newdata):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        self.Data[x, z, y] = (newdata & 0xf)

    def blockDataAt(self, x, y, z):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        return self.Data[x, z, y]

    @classmethod
    def chestWithItemID(cls, itemID, count=64, damage=0):
        """ Creates a chest with a stack of 'itemID' in each slot.
        Optionally specify the count of items in each stack. Pass a negative
        value for damage to create unnaturally sturdy tools. """
        root_tag = nbt.TAG_Compound()
        invTag = nbt.TAG_List()
        root_tag["Inventory"] = invTag
        for slot in range(9, 36):
            itemTag = nbt.TAG_Compound()
            itemTag["Slot"] = nbt.TAG_Byte(slot)
            itemTag["Count"] = nbt.TAG_Byte(count)
            itemTag["id"] = nbt.TAG_Short(itemID)
            itemTag["Damage"] = nbt.TAG_Short(damage)
            invTag.append(itemTag)

        chest = INVEditChest(root_tag, "")

        return chest

    def getChunk(self, cx, cz):
        chunk = super(MCSchematic, self).getChunk(cx, cz)
        if "Biomes" in self.root_tag:
            x = cx << 4
            z = cz << 4
            chunk.Biomes = self.Biomes[x:x + 16, z:z + 16]
        return chunk


class INVEditChest(MCSchematic):
    Width = 1
    Height = 1
    Length = 1
    Blocks = array([[[alphaMaterials.Chest.ID]]], 'uint8')
    Data = array([[[0]]], 'uint8')
    Entities = nbt.TAG_List()
    Materials = alphaMaterials

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "Inventory" in root_tag

    def __init__(self, root_tag, filename):

        if filename:
            self.filename = filename
            if None is root_tag:
                try:
                    root_tag = nbt.load(filename)
                except IOError, e:
                    log.info(u"Failed to load file {0}".format(e))
                    raise
        else:
            assert root_tag, "Must have either root_tag or filename"
            self.filename = None

        for item in list(root_tag["Inventory"]):
            slot = item["Slot"].value
            if slot < 9 or slot >= 36:
                root_tag["Inventory"].remove(item)
            else:
                item["Slot"].value -= 9  # adjust for different chest slot indexes

        self.root_tag = root_tag

    @property
    def TileEntities(self):
        chestTag = nbt.TAG_Compound()
        chest_id = "Chest"
        split_ver = self.gameVersion.split('.')
        if int(split_ver[0]) >= 1 and int(split[1]) >= 11:
            chest_id = "minecraft:chest"
        chestTag["id"] = nbt.TAG_String(chest_id)
        chestTag["Items"] = nbt.TAG_List(self.root_tag["Inventory"])
        chestTag["x"] = nbt.TAG_Int(0)
        chestTag["y"] = nbt.TAG_Int(0)
        chestTag["z"] = nbt.TAG_Int(0)

        return nbt.TAG_List([chestTag], name="TileEntities")


class ZipSchematic(infiniteworld.MCInfdevOldLevel):
    def __init__(self, filename, create=False):
        self.zipfilename = filename

        tempdir = tempfile.mktemp("schematic")
        if create is False:
            zf = zipfile.ZipFile(filename)
            zf.extractall(tempdir)
            zf.close()

        super(ZipSchematic, self).__init__(tempdir, create)
        atexit.register(shutil.rmtree, self.worldFolder.filename, True)

        try:
            schematicDat = nbt.load(self.worldFolder.getFilePath("schematic.dat"))

            self.Width = schematicDat['Width'].value
            self.Height = schematicDat['Height'].value
            self.Length = schematicDat['Length'].value

            if "Materials" in schematicDat:
                self.materials = namedMaterials[schematicDat["Materials"].value]

        except Exception, e:
            print "Exception reading schematic.dat, skipping: {0!r}".format(e)
            self.Width = 0
            self.Length = 0

    def __del__(self):
        shutil.rmtree(self.worldFolder.filename, True)

    def saveInPlaceGen(self):
        self.saveToFile(self.zipfilename)
        yield

    def saveToFile(self, filename):
        schematicDat = nbt.TAG_Compound()
        schematicDat.name = "Mega Schematic"

        schematicDat["Width"] = nbt.TAG_Int(self.size[0])
        schematicDat["Height"] = nbt.TAG_Int(self.size[1])
        schematicDat["Length"] = nbt.TAG_Int(self.size[2])
        schematicDat["Materials"] = nbt.TAG_String(self.materials.name)

        schematicDat.save(self.worldFolder.getFilePath("schematic.dat"))

        basedir = self.worldFolder.filename
        assert os.path.isdir(basedir)
        with closing(zipfile.ZipFile(filename, "w", zipfile.ZIP_STORED)) as z:
            for root, dirs, files in os.walk(basedir):
                # NOTE: ignore empty directories
                for fn in files:
                    absfn = os.path.join(root, fn)
                    zfn = absfn[len(basedir) + len(os.sep):]  # XXX: relative path
                    z.write(absfn, zfn)

    def getWorldBounds(self):
        return BoundingBox((0, 0, 0), (self.Width, self.Height, self.Length))

    @classmethod
    def _isLevel(cls, filename):
        return zipfile.is_zipfile(filename)
    
class StructureNBT(object):
    SUPPORTED_VERSIONS = [1, ]
    
    def __init__(self, filename=None, root_tag=None, size=None, mats=alphaMaterials):
        self._author = None
        self._blocks = None
        self._palette = None
        self._entities = []
        self._tile_entities = None
        self._size = None
        self._version = None
        self._mat = mats
        
        if filename:
            root_tag = nbt.load(filename)
        
        if root_tag:
            self._root_tag = root_tag
            self._size = (self._root_tag["size"][0].value, self._root_tag["size"][1].value, self._root_tag["size"][2].value)
                
            self._author = self._root_tag.get("author", nbt.TAG_String()).value
            self._version = self._root_tag.get("version", nbt.TAG_Int(1)).value
            self._version = self._root_tag.get("DataVersion", nbt.TAG_Int(1)).value
                
            self._palette = self.__toPythonPrimitive(self._root_tag["palette"])
            
            self._blocks = zeros(self.Size, dtype=tuple)
            self._blocks.fill((0, 0))
            self._entities = []
            self._tile_entities = zeros(self.Size, dtype=nbt.TAG_Compound)
            self._tile_entities.fill({})
            
            for block in self._root_tag["blocks"]:
                x, y, z = [ p.value for p in block["pos"].value ]
                self._blocks[x, y, z] = blockstateToID(*self.get_state(block["state"].value))
                if "nbt" in block:
                    compound = nbt.TAG_Compound()
                    compound.update(block["nbt"])
                    self._tile_entities[x, y, z] = compound
                    
            for e in self._root_tag["entities"]:
                entity = e["nbt"]
                entity["Pos"] = e["pos"]
                self._entities.append(entity)
        elif size:
            self._root_tag = nbt.TAG_Compound()
            self._size = size
            
            self._blocks = zeros(self.Size, dtype=tuple)
            self._blocks.fill((0, 0))
            self._entities = []
            self._tile_entities = zeros(self.Size, dtype=nbt.TAG_Compound)
            self._tile_entities.fill({})
            
    def toSchematic(self):
        schem = MCSchematic(shape=self.Size, mats=self._mat)
        for (x, y, z), value in ndenumerate(self._blocks):
            b_id, b_data = value
            schem.Blocks[x, z, y] = b_id
            schem.Data[x, z, y] = b_data
            
        for (x, y, z), value in ndenumerate(self._tile_entities):
            if not value:
                continue
            tag = value
            tag["x"] = nbt.TAG_Int(x)
            tag["y"] = nbt.TAG_Int(y)
            tag["z"] = nbt.TAG_Int(z)
            schem.addTileEntity(tag)
        
        entity_list = nbt.TAG_List()
        for e in self._entities:
            entity_list.append(e)
        schem.root_tag["Entities"] = entity_list
            
        return schem
    
    @classmethod
    def fromSchematic(cls, schematic):
        structure = cls(size=(schematic.Width, schematic.Height, schematic.Length), mats=namedMaterials[getattr(schematic, "Materials", 'Alpha')])
        schematic = copy.deepcopy(schematic)
        
        for (x, z, y), b_id in ndenumerate(schematic.Blocks):
            data = schematic.Data[x, z, y]
            structure._blocks[x, y, z] = (b_id, data)
            
        for te in schematic.TileEntities:
            x, y, z = te["x"].value, te["y"].value, te["z"].value
            del te["x"]
            del te["y"]
            del te["z"]
            structure._tile_entities[x, y, z] = te
            
        for e in schematic.Entities:
            structure._entities.append(e)
        return structure
        
    
    def __toPythonPrimitive(self, _nbt):
        if isinstance(_nbt, nbt.TAG_Compound):
            d = {}
            for key in _nbt.keys():
                if isinstance(_nbt[key], nbt.TAG_Compound):
                    d[key] = self.__toPythonPrimitive(_nbt[key])
                elif isinstance(_nbt[key], nbt.TAG_List):
                    l = []
                    for value in _nbt[key]:
                        if isinstance(value, nbt.TAG_Compound):
                            l.append(self.__toPythonPrimitive(value))
                        else:
                            l.append(value.value)
                    d[key] = l
                else:
                    d[key] = _nbt[key].value
            return d
        elif isinstance(_nbt, nbt.TAG_List):
            l = []
            for tag in _nbt:
                if isinstance(tag, nbt.TAG_Compound):
                    l.append(self.__toPythonPrimitive(tag))
                elif isinstance(tag, nbt.TAG_List):
                    l.append(self.__toPythonPrimitive(tag))
                else:
                    l.append(tag.value)
            return l
    
    def __convertPaletteToDict(self):
        palette = []
        for state in self._root_tag["palette"]:
            block = {}
            block["Name"] = state["Name"].value
            if "Properties" in state:
                block["Properties"] = {}
                for (key, value) in state["Properties"].iteritems():
                    block["Properties"][key] = value.value
            palette.append(block)
        return palette
    
    def get_state(self, index):
        if index > (len(self._palette) - 1):
            raise IndexError()
        return (self._palette[index]["Name"], self._palette[index].get("Properties", {}))
            
    def get_palette_index(self, name, properties=None):  # TODO: Switch to string comparison of properties, instead of dict comparison
        for i in range(len(self._palette)):
            if self._palette[i]["Name"] == name:
                if properties and "Properties" in self._palette[i]:
                    for (key, value) in properties.iteritems():
                        if not self._palette[i]["Properties"].get(key, None) == value:
                            continue
                    return i
                else:
                    return i
        return -1
        
    def _find_air(self):
        for i in range(len(self._palette)):
            if self._palette[i]["Name"] == "minecraft:air":
                return i
        return -1
    
    def save(self, filename=""):
        structure_tag = nbt.TAG_Compound()
        blocks_tag = nbt.TAG_List()
        palette_tag = nbt.TAG_List()
        entities_tag = nbt.TAG_List()
        
        
        palette = []
        
        if not self._author:
            self._author = "MCEdit-Unified v{}".format(RELEASE_TAG)
        
        structure_tag["author"] = nbt.TAG_String(self._author)
        if self._version:
            structure_tag["DataVersion"] = nbt.TAG_Int(self.Version)
        else:
            structure_tag["DataVersion"] = nbt.TAG_Int(self.SUPPORTED_VERSIONS[-1])
            
        structure_tag["size"] = nbt.TAG_List(
                                             [
                                              nbt.TAG_Int(self.Size[0]),
                                              nbt.TAG_Int(self.Size[1]),
                                              nbt.TAG_Int(self.Size[2])
                                              ]
                                             )
        
        blockstate_api = BlockstateAPI.material_map.get(self._mat, BlockstateAPI.material_map[alphaMaterials])
        for z in range(self._blocks.shape[2]):  # For some reason, ndenumerate() didn't work, but this does
            for x in range(self._blocks.shape[0]):
                for y in range(self._blocks.shape[1]):
                    
                    value = self._blocks[x, y, z]
                    name, properties = blockstate_api.idToBlockstate(*value)
                    blockstate = blockstate_api.stringifyBlockstate(name, properties)
            
                    #if blockstate not in index_table:
                    #    index_table[blockstate] = len(index_table)
                    #index = index_table[blockstate]
                    if blockstate not in palette:
                        palette.append(blockstate)
                    index = palette.index(blockstate)
            
                    block = nbt.TAG_Compound()
                    block["state"] = nbt.TAG_Int(index)
                    block["pos"] = nbt.TAG_List(
                                        [
                                         nbt.TAG_Int(x),
                                         nbt.TAG_Int(y),
                                         nbt.TAG_Int(z)
                                         ]
                                        )
            
                    if self._tile_entities[x, y, z]:
                        block["nbt"] = self._tile_entities[x, y, z]
            
                    blocks_tag.append(block)
        structure_tag["blocks"] = blocks_tag
        
        for blockstate in palette:
            name, properties = blockstate_api.deStringifyBlockstate(blockstate)
            
            state = nbt.TAG_Compound()
            state["Name"] = nbt.TAG_String(name)
            
            if properties:
                props = nbt.TAG_Compound()
                for (key, value) in properties.iteritems():
                    props[key] = nbt.TAG_String(value)
                state["Properties"] = props
                
            palette_tag.insert(palette.index(blockstate), state)
        structure_tag["palette"] = palette_tag
        
        for e in self._entities:
            entity = nbt.TAG_Compound()
            pos = e["Pos"]
            entity["pos"] = pos
            entity["nbt"] = e
            blockPos = nbt.TAG_List()
            for coord in pos:
                blockPos.append(nbt.TAG_Int(math.floor(coord.value)))
            entity["blockPos"] = blockPos
            
            entities_tag.append(entity)
            
        structure_tag["entities"] = entities_tag
        structure_tag.save(filename)
        
    @property
    def Version(self):
        return self._version
    
    @property
    def Author(self):
        return self._author
    
    @property
    def Size(self):
        return self._size
    
    @property
    def Blocks(self):
        return self._blocks
    
    @property
    def Entities(self):
        return self._entities
        
    @property
    def Palette(self):
        return self._palette

def adjustExtractionParameters(self, box):
    x, y, z = box.origin
    w, h, l = box.size
    destX = destY = destZ = 0

    if y < 0:
        destY -= y
        h += y
        y = 0

    if y >= self.Height:
        return

    if y + h >= self.Height:
        h -= y + h - self.Height
        y = self.Height - h

    if h <= 0:
        return

    if self.Width:
        if x < 0:
            w += x
            destX -= x
            x = 0
        if x >= self.Width:
            return

        if x + w >= self.Width:
            w = self.Width - x

        if w <= 0:
            return

        if z < 0:
            l += z
            destZ -= z
            z = 0

        if z >= self.Length:
            return

        if z + l >= self.Length:
            l = self.Length - z

        if l <= 0:
            return

    box = BoundingBox((x, y, z), (w, h, l))

    return box, (destX, destY, destZ)


def extractSchematicFrom(sourceLevel, box, entities=True, cancelCommandBlockOffset=False):
    return exhaust(extractSchematicFromIter(sourceLevel, box, entities, cancelCommandBlockOffset))


def extractSchematicFromIter(sourceLevel, box, entities=True, cancelCommandBlockOffset=False):
    p = sourceLevel.adjustExtractionParameters(box)
    if p is None:
        yield None
        return
    newbox, destPoint = p

    tempSchematic = MCSchematic(shape=box.size, mats=sourceLevel.materials)
    for i in tempSchematic.copyBlocksFromIter(sourceLevel, newbox, destPoint, entities=entities, biomes=True, first=True, cancelCommandBlockOffset=cancelCommandBlockOffset):
        yield i

    yield tempSchematic


MCLevel.extractSchematic = extractSchematicFrom
MCLevel.extractSchematicIter = extractSchematicFromIter
MCLevel.adjustExtractionParameters = adjustExtractionParameters

import tempfile


def extractZipSchematicFrom(sourceLevel, box, zipfilename=None, entities=True):
    return exhaust(extractZipSchematicFromIter(sourceLevel, box, zipfilename, entities))


def extractZipSchematicFromIter(sourceLevel, box, zipfilename=None, entities=True, cancelCommandBlockOffset=False):
    # converts classic blocks to alpha
    # probably should only apply to alpha levels

    if zipfilename is None:
        zipfilename = tempfile.mktemp("zipschematic.zip")
    atexit.register(shutil.rmtree, zipfilename, True)

    p = sourceLevel.adjustExtractionParameters(box)
    if p is None:
        return
    sourceBox, destPoint = p

    destPoint = (0, 0, 0)

    tempSchematic = ZipSchematic(zipfilename, create=True)
    tempSchematic.materials = sourceLevel.materials

    for i in tempSchematic.copyBlocksFromIter(sourceLevel, sourceBox, destPoint, entities=entities, create=True,
                                              biomes=True, first=True, cancelCommandBlockOffset=cancelCommandBlockOffset):
        yield i

    tempSchematic.Width, tempSchematic.Height, tempSchematic.Length = sourceBox.size
    tempSchematic.saveInPlace()  # lights not needed for this format - crashes minecraft though
    yield tempSchematic


MCLevel.extractZipSchematic = extractZipSchematicFrom
MCLevel.extractZipSchematicIter = extractZipSchematicFromIter


def extractAnySchematic(level, box):
    return exhaust(level.extractAnySchematicIter(box))


def extractAnySchematicIter(level, box):
    if box.chunkCount < infiniteworld.MCInfdevOldLevel.loadedChunkLimit:
        for i in level.extractSchematicIter(box):
            yield i
    else:
        for i in level.extractZipSchematicIter(box):
            yield i


MCLevel.extractAnySchematic = extractAnySchematic
MCLevel.extractAnySchematicIter = extractAnySchematicIter
