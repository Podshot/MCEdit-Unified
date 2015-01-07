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
from materials import alphaMaterials, MCMaterials, namedMaterials
from mclevelbase import exhaust
import nbt
from numpy import array, swapaxes, uint8, zeros, resize

log = getLogger(__name__)

__all__ = ['MCSchematic', 'INVEditChest']


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

        if filename:
            self.filename = filename
            if None is root_tag and os.path.exists(filename):
                root_tag = nbt.load(filename)
        else:
            self.filename = None

        if mats in namedMaterials:
            self.materials = namedMaterials[mats]
        else:
            assert (isinstance(mats, MCMaterials))
            self.materials = mats

        if root_tag:
            self.root_tag = root_tag
            if "Materials" in root_tag:
                self.materials = namedMaterials[self.Materials]
            else:
                root_tag["Materials"] = nbt.TAG_String(self.materials.name)

            w = self.root_tag["Width"].value
            l = self.root_tag["Length"].value
            h = self.root_tag["Height"].value

            self._Blocks = self.root_tag["Blocks"].value.astype('uint16').reshape(h, l, w)  # _Blocks is y, z, x
            del self.root_tag["Blocks"]
            if "AddBlocks" in self.root_tag:
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
                self.root_tag["Biomes"].value.shape = (l, w)

        else:
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
            if entity["id"].value in ("Painting", "ItemFrame"):
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
            if not 'x' in tileEntity:
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

            if entity["id"].value in ("Painting", "ItemFrame"):
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
            if entity["id"].value in ("Painting", "ItemFrame"):
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

            entity["Pos"][0].value = self.Width - entity["Pos"][0].value
            entity["Motion"][0].value = -entity["Motion"][0].value

            entity["Rotation"][0].value -= 180.0

            # Special logic for old width painting as TileX/TileZ favours -x/-z

            if entity["id"].value in ("Painting", "ItemFrame"):
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

            if entity["id"].value == "Painting":
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
            elif entity["id"].value == "ItemFrame":
                entity["TileX"].value = self.Width - entity["TileX"].value - 1
                facing.value = northSouthPaintingMap[facing.value]
        for tileEntity in self.TileEntities:
            if not 'x' in tileEntity:
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

            entity["Pos"][2].value = self.Length - entity["Pos"][2].value
            entity["Motion"][2].value = -entity["Motion"][2].value

            entity["Rotation"][0].value -= 180.0

            # Special logic for old width painting as TileX/TileZ favours -x/-z

            if entity["id"].value in ("Painting", "ItemFrame"):
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

            if entity["id"].value == "Painting":
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
            elif entity["id"].value == "ItemFrame":
                entity["TileZ"].value = self.Length - entity["TileZ"].value - 1
                facing.value = eastWestPaintingMap[facing.value]

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
        chestTag["id"] = nbt.TAG_String("Chest")
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


def extractSchematicFrom(sourceLevel, box, entities=True):
    return exhaust(extractSchematicFromIter(sourceLevel, box, entities))


def extractSchematicFromIter(sourceLevel, box, entities=True):
    p = sourceLevel.adjustExtractionParameters(box)
    if p is None:
        yield None
        return
    newbox, destPoint = p

    tempSchematic = MCSchematic(shape=box.size, mats=sourceLevel.materials)
    for i in tempSchematic.copyBlocksFromIter(sourceLevel, newbox, destPoint, entities=entities, biomes=True, first=True):
        yield i

    yield tempSchematic


MCLevel.extractSchematic = extractSchematicFrom
MCLevel.extractSchematicIter = extractSchematicFromIter
MCLevel.adjustExtractionParameters = adjustExtractionParameters

import tempfile


def extractZipSchematicFrom(sourceLevel, box, zipfilename=None, entities=True):
    return exhaust(extractZipSchematicFromIter(sourceLevel, box, zipfilename, entities))


def extractZipSchematicFromIter(sourceLevel, box, zipfilename=None, entities=True):
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
                                              biomes=True, first=True):
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
