import os
from os.path import join
import time
import traceback
import unittest
import numpy
from pymclevel import nbt
from templevel import TempLevel

__author__ = 'Rio'


class TestNBT(unittest.TestCase):

    @staticmethod
    def testLoad():
        """Load an indev level."""
        level = nbt.load("testfiles/hell.mclevel")

        # The root tag must have a name, and so must any tag within a TAG_Compound
        assert len(level.name) > 0

        # Use the [] operator to look up subtags of a TAG_Compound.
        assert level["Environment"]["SurroundingGroundHeight"].value is not None

        # Numeric, string, and bytearray types have a value that can be accessed and changed.
        assert level["Map"]["Blocks"].value is not None
        assert True
        return level

    @staticmethod
    def testLoadUncompressed():
        nbt.load("testfiles/uncompressed.nbt")

    @staticmethod
    def testLoadNBTExplorer():
        nbt.load("testfiles/modified_by_nbtexplorer.dat")

    @staticmethod
    def testCreate():
        """Create an indev level."""

        # The root of an NBT file is always a TAG_Compound.
        level = nbt.TAG_Compound(name="MinecraftLevel")

        # Subtags of a TAG_Compound are automatically named when you use the [] operator.
        level["About"] = nbt.TAG_Compound()
        level["About"]["Author"] = nbt.TAG_String("codewarrior")
        level["About"]["CreatedOn"] = nbt.TAG_Long(time.time())

        level["Environment"] = nbt.TAG_Compound()
        level["Environment"]["SkyBrightness"] = nbt.TAG_Byte(16)
        level["Environment"]["SurroundingWaterHeight"] = nbt.TAG_Short(32)
        level["Environment"]["FogColor"] = nbt.TAG_Int(0xcccccc)

        entity = nbt.TAG_Compound()
        entity["id"] = nbt.TAG_String("Creeper")
        entity["Pos"] = nbt.TAG_List([nbt.TAG_Float(d) for d in (32.5, 64.0, 33.3)])

        level["Entities"] = nbt.TAG_List([entity])

        # You can also create and name a tag before adding it to the compound.
        spawn = nbt.TAG_List((nbt.TAG_Short(100), nbt.TAG_Short(45), nbt.TAG_Short(55)))
        spawn.name = "Spawn"

        mapTag = nbt.TAG_Compound()
        mapTag.add(spawn)
        mapTag.name = "Map"
        level.add(mapTag)

        mapTag2 = nbt.TAG_Compound([spawn])
        mapTag2.name = "Map"

        # I think it looks more familiar with [] syntax.

        l, w, h = 128, 128, 128
        mapTag["Height"] = nbt.TAG_Short(h)  # y dimension
        mapTag["Length"] = nbt.TAG_Short(l)  # z dimension
        mapTag["Width"] = nbt.TAG_Short(w)  # x dimension

        # Byte arrays are stored as numpy.uint8 arrays.

        mapTag["Blocks"] = nbt.TAG_Byte_Array()
        mapTag["Blocks"].value = numpy.zeros(l * w * h, dtype=numpy.uint8)  # create lots of air!

        # The blocks array is indexed (y,z,x) for indev levels, so reshape the blocks
        mapTag["Blocks"].value.shape = (h, l, w)

        # Replace the bottom layer of the indev level with wood
        mapTag["Blocks"].value[0, :, :] = 5

        # This is a great way to learn the power of numpy array slicing and indexing.

        mapTag["Data"] = nbt.TAG_Byte_Array()
        mapTag["Data"].value = numpy.zeros(l * w * h, dtype=numpy.uint8)

        # Save a few more tag types for completeness

        level["ShortArray"] = nbt.TAG_Short_Array(numpy.zeros((16, 16), dtype='uint16'))
        level["IntArray"] = nbt.TAG_Int_Array(numpy.zeros((16, 16), dtype='uint32'))
        level["Float"] = nbt.TAG_Float(0.3)

        return level

    def testToStrings(self):
        level = self.testCreate()
        repr(level)
        repr(level["Map"]["Blocks"])
        repr(level["Entities"])

        str(level)

    def testModify(self):
        level = self.testCreate()

        # Most of the value types work as expected. Here, we replace the entire tag with a TAG_String
        level["About"]["Author"] = nbt.TAG_String("YARRR~!")

        # Because the tag type usually doesn't change,
        # we can replace the string tag's value instead of replacing the entire tag.
        level["About"]["Author"].value = "Stew Pickles"

        # Remove members of a TAG_Compound using del, similar to a python dict.
        del (level["About"])

        # Replace all of the wood blocks with gold using a boolean index array
        blocks = level["Map"]["Blocks"].value
        blocks[blocks == 5] = 41

        level["Entities"][0] = nbt.TAG_Compound([nbt.TAG_String("Creeper", "id"),
                                                 nbt.TAG_List([nbt.TAG_Double(d) for d in (1, 1, 1)], "Pos")])

    @staticmethod
    def testMultipleCompound():
        """ According to rumor, some TAG_Compounds store several tags with the same name. Once I find a chunk file
        with such a compound, I need to test TAG_Compound.get_all()"""

        pass

    def testSave(self):
        try:
            level = self.testCreate()
            level["Environment"]["SurroundingWaterHeight"].value += 6

            # Save the entire TAG structure to a different file.
            TempLevel("atlantis.mclevel", createFunc=level.save)  # xxx don't use templevel here
        except Exception as err:
            print err
            traceback.print_exc()
            assert False
        assert True

    @staticmethod
    def testList():
        tag = nbt.TAG_List()
        tag.append(nbt.TAG_Int(258))
        del tag[0]

    def testErrors(self):
        """
        attempt to name elements of a TAG_List
        named list elements are not allowed by the NBT spec,
        so we must discard any names when writing a list.
        """

        level = self.testCreate()
        level["Map"]["Spawn"][0].name = "Torg Potter"
        print 'saving'
        data = level.save()
        print 'loading'
        newlevel = nbt.load(buf=data)

        n = newlevel["Map"]["Spawn"][0].name
        if n:
            print "Named list element failed: %s" % n

        # attempt to delete non-existent TAG_Compound elements
        # this generates a KeyError like a python dict does.
        level = self.testCreate()
        try:
            del level["DEADBEEF"]
        except KeyError:
            pass
        else:
            assert False

    @staticmethod
    def testLittleEndianNBT():
        raw_string = open("testfiles/little_endian_level.dat").read()[8:]
        level = nbt.load(buf=raw_string, endianness=nbt.LITTLE_ENDIAN)
        saved_level = level.save(endianness=nbt.LITTLE_ENDIAN, compressed=False)
        with open('test.txt', 'w') as f:
            f.write(raw_string)
            f.write(saved_level)
        assert saved_level == raw_string

    @staticmethod
    def testSpeed():
        d = join("testfiles", "TileTicks_chunks")
        files = [join(d, f) for f in os.listdir(d)]
        startTime = time.time()
        for f in files[:40]:
            nbt.load(f)
        duration = time.time() - startTime

        assert duration < 1.0  # Will fail when not using _nbt.pyx
