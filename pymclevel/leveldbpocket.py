import itertools
import time
from math import floor, ceil, log
from level import FakeChunk, MCLevel
import logging
from materials import pocketMaterials

import os

from mclevelbase import ChunkNotPresent, ChunkMalformed
import nbt
import numpy
import struct
from infiniteworld import ChunkedLevelMixin, SessionLockLost, AnvilChunkData, AnvilWorldFolder, unpackNibbleArray, packNibbleArray
from level import LightedChunk
from contextlib import contextmanager
from pymclevel import entity, BoundingBox, Entity, TileEntity
import traceback
import shutil

logger = logging.getLogger(__name__)

# Support for PE 0.9.0 to 1.0.0
leveldb_available = True
leveldb_mcpe = None

try:
    import leveldb as leveldb_mcpe
except Exception as e:
    trace_msg = traceback.format_exc().splitlines()
    logger.warn("Error while trying to import leveldb:")
    [logger.warn(a) for a in trace_msg]

try:
    if leveldb_mcpe is None:
        import leveldb_mcpe
    leveldb_mcpe.Options()
except Exception as e:
    logger.info("Error while trying to import leveldb_mcpe ({0})".format(e))


#---------------------------------------------------------------------
# TRACKING ERRORS
#
# Some debug messages will be displayed in the console, and a file will be used to put more information.
import sys
DEBUG_PE = False
dump_fName = 'dump_pe.txt'
longest_complist_len = 0
longest_complist = ''
shortest_complist_len = sys.maxint
shortest_complist = ''

if '--debug-pe' in sys.argv:
    sys.argv.remove('--debug-pe')
    DEBUG_PE = True
    # Override nbt module DEBUG_PE and dump_fName
    nbt.DEBUG_PE = DEBUG_PE
    nbt.dump_fName = dump_fName

# Check if the --debug-pe CLI option is given several times to set a higher verbose level.
# 'True' is considered being 1, so let set DEBUG_PE to 2 if it's found a secondtime on the CLI
# and add 1 to the value each time it's found.
while '--debug-pe' in sys.argv:
    sys.argv.remove('--debug-pe')
    if DEBUG_PE is True:
        DEBUG_PE = 2
    else:
        DEBUG_PE += 1

if DEBUG_PE:
    open(dump_fName, 'w').close()


def write_dump(msg):
    """Helper function to write data to the PE dump file when using '--debug-pe' CLI option."""
    open(dump_fName, 'a').write(msg)


# =====================================================================
def loadNBTCompoundList(data, littleEndian=True, partNBT=False, count=None):
    """
    Loads a list of NBT Compound tags from a bunch of data.
    Uses sep to determine where the next Compound tag starts.
    :param data: str, the NBT to load from
    :param littleEndian: bool. Determines endianness
    :param partNBT: bool. If part of the data is NBT (begins with NBT), the function will return the list of compounds with the rest of the data that was not NBT
    :return: list of TAG_Compounds
    """
    def load(_data, _partNBT, _count):
        compound_list = []
        idx = 0
        count = 0
        while idx < len(_data) and (_count is None or count < _count):
            try:
                __data = nbt.load(buf=_data[idx:])
                idx += len(nbt.gunzip(__data.save()))
                count += 1
            except Exception as e:
                if _partNBT:
                    return compound_list, _data[idx:]
                msg1 = "PE support could not read compound list data:"
                msg2 = "Data dump:"
                msg3 = "Data length: %s"
                logger.error(msg1)
                logger.error(e)
                if len(_data[idx:]) > 80:
                    logger.error("Partial data dump:")
                    logger.error("%s [...] %s", repr(_data[:idx + 40]), repr(_data[-40:]))
                else:
                    logger.error(msg2)
                    logger.error(repr(_data[idx:]))
                logger.error(msg3, len(data))
                if DEBUG_PE:
                    try:
                        dump_line = len(open(dump_fName).read().splitlines()) + 1
                        dump_msg = "**********\n{m1}\n{e}\n{m2}\n{d}\n{m3} {l}".format(m1=msg1,
                                   e=e, m2=msg2, d=repr(_data[idx:]), m3=msg3, l=len(data))
                        msg_len = len(dump_msg.splitlines())
                        write_dump(dump_msg)
                        logger.warn("Error info and data dumped to %s at line %s (%s lines long)", dump_fName, dump_line, msg_len)
                    except Exception as _e:
                        logger.error("Could not dump PE debug info:")
                        logger.error(_e)
                raise e
            if DEBUG_PE == 2:
                write_dump("++++++++++\nloadNBTCompoundList_new parsed data:\n{d}\nis compound ? {ic}\n".format(d=__data, ic=__data.isCompound()))
            compound_list.append(__data)
        if _partNBT:
            return compound_list, _data[idx:]
        return compound_list

    if littleEndian:
        with nbt.littleEndianNBT():
            return load(data, partNBT, count)
    else:
        return load(data, partNBT, count)


# =====================================================================
def TagProperty(tagName, tagType, default_or_func=None):
    """
    Copied from infiniteworld.py. Custom property object to handle NBT-tag properties.
    :param tagName: str, Name of the NBT-tag
    :param tagType: int, (nbt.TAG_TYPE) Type of the NBT-tag
    :param default_or_func: function or default value. If function, function should return the default.
    :return: property
    """
    def getter(self):
        root_tag = self.root_tag["Data"]
        if tagName not in root_tag:
            if hasattr(default_or_func, "__call__"):
                default = default_or_func(self)
            else:
                default = default_or_func

            root_tag[tagName] = tagType(default)
        return root_tag[tagName].value

    def setter(self, val):
        self.root_tag[tagName] = tagType(value=val)

    return property(getter, setter)


class InvalidPocketLevelDBWorldException(Exception):
    pass


# =====================================================================
def get_blocks_storage_from_blocks_and_data(blocks, data):
    blocksCombined = numpy.stack((blocks, data))
    uniqueBlocks = numpy.transpose(numpy.unique(blocksCombined, axis=1))
    palette = []
    numpy_blocks = numpy.zeros(4096, 'uint16')
    for index, (blockID, blockData) in enumerate(uniqueBlocks):
        try:
            if blockID != 0:
                block_string = "minecraft:" + pocketMaterials.idStr[blockID]
                block_data = blockData
            else:
                block_string = "minecraft:air"
                block_data = blockData
        except:
            block_string = "minecraft:air"
            block_data = 0
        with nbt.littleEndianNBT():
            block_nbt = nbt.TAG_Compound([nbt.TAG_String(block_string, "name"), nbt.TAG_Short(block_data, "val")]).save(compressed=False)
        if block_nbt not in palette:
            palette.append(block_nbt)
        position = palette.index(block_nbt)
        numpy_blocks[(blocksCombined[0]==blockID) & (blocksCombined[1]==blockData)] = position
    max_bits = len('{0:b}'.format(numpy_blocks.max()))
    possible_bits_per_blocks = [1, 2, 3, 4, 5, 6, 8, 16]
    bits_per_block = possible_bits_per_blocks[numpy.searchsorted(possible_bits_per_blocks, max_bits, side='left')]
    word_size = 32
    blocks_per_word = int(floor(32 / bits_per_block))
    word_count = int(ceil(4096 / float(blocks_per_word)))
    blocks_binary = (numpy_blocks.reshape(-1, 1) >> numpy.arange(bits_per_block)[::-1] & 1).astype(bool)
    bits_per_word = bits_per_block * blocks_per_word
    bits_missing = bits_per_word - (blocks_binary.shape[0] * blocks_binary.shape[1]) % bits_per_word
    if bits_missing == bits_per_word:
        bits_missing = 0
    final_blocks_binary = numpy.concatenate([blocks_binary, numpy.array([False] * bits_missing).reshape(-1, bits_per_block)])
    clean_blocks_binary = final_blocks_binary.reshape(-1, word_size / bits_per_block, bits_per_block)[:, ::-1].reshape(-1, blocks_per_word * bits_per_block)
    full_blocks_binary = numpy.hstack([numpy.empty([word_count, word_size - bits_per_word], dtype=bool), clean_blocks_binary])
    flat_blocks_binary = full_blocks_binary.reshape(-1, word_size / 8, 8)[:, ::-1, :].ravel()
    blocks_in_bytes = numpy.packbits(flat_blocks_binary.astype(int)).tobytes()

    palette_size = struct.pack("<i", len(palette))
    palette_string = "".join(palette)

    return chr(bits_per_block << 1) + blocks_in_bytes + palette_size + palette_string


class PocketLeveldbDatabase(object):
    """
    Not to be confused with leveldb.DB
    A PocketLeveldbDatabase is an interface around leveldb_mcpe.DB, providing various functions
    to load/write chunk data, and access the level.dat file.
    The leveldb_mcpe.DB object handles the actual leveldb database.
    To access the actual database, world_db() should be called.
    """
    holdDatabaseOpen = True
    _world_db = None
    world_version = None  # to be set to 'pre1.0' or '1.plus'

    def __open_db(self):
        """Opens a DB and return the associated object."""
        pth = os.path.join(self.path, 'db').encode(sys.getfilesystemencoding())
        compressors = self.compressors
        if not compressors:
            compressors = (2,)
            if ord(self.dat_world_version) >= 6:
                compressors = (4, 2)
        if DEBUG_PE:
            write_dump("Binary world version: %s; compressor: %s\n" % (repr(self.dat_world_version), compressors))
        return self.ldb.DB(self.options, pth, compressors=compressors)

    @contextmanager
    def world_db(self, compressors=None):
        """
        Opens a leveldb and keeps it open until editing finished.
        :param compressors: None or tuple of ints: The compressor type(s) to be used.
                If None, the value is decided according to the 'dat_world_version'.
        :yield: DB
        """
        if not self.compressors:
            self.compressors = compressors
        if PocketLeveldbDatabase.holdDatabaseOpen:
            if self._world_db is None:
                self._world_db = self.__open_db()
            yield self._world_db
            pass
        else:
            db = self.__open_db()
            yield db
            del db

    def __init__(self, path, level, create=False, world_version=None, dat_world_version=None, compressors=None):
        """
        :param path: string, path to file.
        :param level: parent PocketLeveldbWorld instance.
        :param create: bool, wheter to create the world. Defaults to False.
        :param world_version: string or None, world version. Defaults to None.
        :param dat_world_version: char or None, binary world version as stored on the disk.
        :param compressors: None or tuple of ints: The compressor type(s) to be used.
                If None, the value is decided according to the 'dat_world_version'.
        :return: None
        """
        if not world_version:
            raise TypeError("Wrong world version sent: %s"%world_version)
        self.world_version = world_version
        self.dat_world_version = dat_world_version
        self.path = path
        if not os.path.exists(path):
            file(path, 'w').close()
        self.level = level
        self.compressors = compressors


        self.options = leveldb_mcpe.Options()
        self.writeOptions = leveldb_mcpe.WriteOptions()
        self.readOptions = leveldb_mcpe.ReadOptions()
        self.ldb = leveldb_mcpe

        if create:
            # Rework this, because leveldb.Options() is a function...
            #self.options.create_if_missing = True  # The database will be created once needed first.
            return

        needsRepair = False
        try:

            # Let's try to 'magicaly' find the right compression for the world.
            compressors_list = (None, (4,), (2,))
            i = 0
            while True:
                compressors = compressors_list[i]
                with self.world_db(compressors) as db:
                    try:
                        it = db.NewIterator(self.readOptions)
                        it.SeekToFirst()
                        if not db.Get(self.readOptions, it.key()) == it.value():
                            needsRepair = True
                        it.status()
                        del it
                        break
                    except leveldb_mcpe.ZipCompressionError:
                        if i < len(compressors_list) - 1:
                            i += 1
                            self._world_db.close()
                            self._world_db = None
                            self.compressors = None
                        else:
                            raise

        except RuntimeError as err:
            logger.error("Error while opening world database from %s (%s)"%(path, err))
            needsRepair = True

        if needsRepair:
            logger.info("Trying to repair world %s"%path)
            try:
                self.ldb.RepairWrapper(os.path.join(path, 'db'))
            except RuntimeError as err:
                logger.error("Error while repairing world %s %s"%(path, err))

    def close(self):
        """
        Should be called before deleting this instance of the level.
        Not calling this method may result in corrupted worlds
        :return: None
        """
        if PocketLeveldbDatabase.holdDatabaseOpen:
            if self._world_db is not None:
                del self._world_db
                self._world_db = None

    def _readChunk_pre1_0(self, cx, cz, readOptions=None, key=None):
        """
        :param cx, cz: int Coordinates of the chunk
        :param readOptions: ReadOptions
        :return: None
        """
        if key is None:
            key = struct.pack('<i', cx) + struct.pack('<i', cz)
        with self.world_db() as db:
            rop = self.readOptions if readOptions is None else readOptions

            # Only way to see if value exists is by failing db.Get()
            try:
                terrain = db.Get(rop, key + "0")
            except RuntimeError:
                return None

            try:
                tile_entities = db.Get(rop, key + "1")
            except RuntimeError:
                tile_entities = None

            try:
                entities = db.Get(rop, key + "2")
            except RuntimeError:
                entities = None

        if len(terrain) != 83200:
            raise ChunkMalformed(str(len(terrain)))

        return terrain, tile_entities, entities

    def _readSubChunk_1plus(self, cx, cz, y, readOptions=None, key=None):
        """Read PE 1.0+ subchunk

        cx, cz: int: coordinates of the chunk.
        y: int: 'height' index of the subchunk, generaly a0 to 15 number.
        readOptions: object: Pocket DB read options container to be used with the data base. Default to 'None'.
            Automatically gathered if the default 'None' value is used.
        key: str: binary form of the key to request data for. Default to 'None'.
            Automatically calculated from cx and cz if the default 'None' value is used.
        """
        if key is None:
            key = struct.pack('<i', cx) + struct.pack('<i', cz)
        with self.world_db() as db:
            rop = self.readOptions if readOptions is None else readOptions
            c = chr(y)

            try:
                terrain = db.Get(rop, key + "\x2f" + c)
            except RuntimeError:
                if DEBUG_PE:
                    write_dump("!!! No terrain found for sub-chunk (%s, %s, %s)\n" % (cx, cz, y))
                terrain = None
            except Exception as e:
                if DEBUG_PE:
                    write_dump("!!! An unhandled error occured when loading sub-chunk (%s, %s, %s) terrain.\n" % (cx, cz, y))
                    write_dump("%s" % e)
                terrain = None

            if y == 0:
                try:
                    tile_entities = db.Get(rop, key + "\x31")
                except RuntimeError:
                    tile_entities = None

                try:
                    entities = db.Get(rop, key + "\x32")
                except RuntimeError:
                    entities = None
            else:
                tile_entities = entities = None

        return terrain, tile_entities, entities

    def _readChunk(self, cx, cz, world, readOptions=None):
        """
        :param cx, cz: int Coordinates of the chunk
        :param readOptions: ReadOptions
        :return: chunk data in a tuple: (terrain, tile_entities, entities)
        """
        # PE 1+ worlds can contain pre 1.0 chunks.
        # Let check which version of the chunk we have before doing anything else.
        with self.world_db() as db:
            rop = self.readOptions if readOptions is None else readOptions
            key = struct.pack('<i', cx) + struct.pack('<i', cz)
            raise_err = False
            try:
                chunk_version = db.Get(rop, key + chr(118))
                if chunk_version is None:
                    raise_err = True
            except:
                raise_err = True
            if raise_err:
                raise ChunkNotPresent((cx, cz, self))
            if DEBUG_PE:
                write_dump("** Loading chunk ({x}, {z}) for PE {vs} ({v}).\n".format(x=cx, z=cz, vs={"\x02": "pre 1.0", "\x03": "1.0", "\x04": "1.1"}.get(chunk_version, 'Unknown'), v=repr(chunk_version)))

            if chunk_version == "\x02":
                # We have a pre 1.0 chunk
                data = self._readChunk_pre1_0(cx, cz, rop, key)
                if data is None:
                    raise ChunkNotPresent((cx, cz, self))
                chunk = PocketLeveldbChunkPre1(cx, cz, world, data, world_version=self.world_version)
            # Let assume that any chunk wich version is greater or equal to 3 in a PE 1+ one.
            elif ord(chunk_version) >= 3:
                # PE 1+ chunk detected. Iterate through the subchunks to rebuild the whole data.
                # If the world version was set o pre1.0 during initialization, change it for 1+.
                # Change also the world height to 256...
                if world.world_version == 'pre1.0':
                    logger.info("Detected pre 1.0 world, but 1.0+ chunk found. Changing world version and height accordingly.")
                    world.world_version = '1.plus'
                    world.Height = 256
                    self.world_version = '1.plus'

                    # Reload the 'allChunks' object
                    world._allChunks = None
                    world.allChunks

                chunk = PocketLeveldbChunk1Plus(cx, cz, world, world_version=self.world_version, chunk_version=chunk_version)
                d2d = db.Get(rop, key + "\x2d")
                if d2d:
                    # data_2d contains the heightmap (currently computed dynamically, may change)
                    # and the biome information of the chunk on the last 256 bytes.
                    chunk.data_2d = d2d
                    biomes = numpy.fromstring(d2d[512:], 'uint8')
                    biomes.shape = (16, 16)
                    chunk.Biomes = biomes
                for i in range(16):
                    tr, te, en = self._readSubChunk_1plus(cx, cz, i, rop, key)
                    chunk.add_data(terrain=tr, tile_entities=te, entities=en, subchunk=i)

                # Generate the lights if we have a PE 1.1 chunk.
                if ord(chunk.chunk_version) >= 4:
                    chunk.genFastLights()
                if DEBUG_PE:
                    write_dump(">>> Chunk (%s, %s) sub-chunks: %s\n" % (cx, cz, repr(chunk.subchunks)))
            elif chunk_version is not None:
                raise AttributeError("Unknown PE chunk version %s" % repr(chunk_version))
            elif chunk_version is None:
                if DEBUG_PE:
                    write_dump("Chunk (%s, %s) version seem to be 'None'. Do this chunk exists in this world?" % (cx, cz))
                return None
            else:
                if DEBUG_PE:
                    write_dump("Unknown chunk version detected for chunk (%s, %s): %s" % (cx, cz, repr(chunk_version)))
                raise AttributeError("Unknown chunk version detected for chunk (%s, %s): %s" % (cx, cz, repr(chunk_version)))
            logger.debug("CHUNK LOAD %s %s" % (cx, cz))
            return chunk

    def _saveChunk_pre1_0(self, chunk, batch=None, writeOptions=None):
        """
        :param chunk: PocketLeveldbChunk
        :param batch: WriteBatch
        :param writeOptions: WriteOptions
        :return: None
        """
        cx, cz = chunk.chunkPosition
        data = chunk.savedData()
        key = struct.pack('<i', cx) + struct.pack('<i', cz)

        if batch is None:
            with self.world_db() as db:
                wop = self.writeOptions if writeOptions is None else writeOptions
                db.Put(wop, key + "0", data[0])
                if data[1] is not None:
                    db.Put(wop, key + "1", data[1])
                if data[2] is not None:
                    db.Put(wop, key + "2", data[2])
        else:
            batch.Put(key + "0", data[0])
            if data[1] is not None:
                batch.Put(key + "1", data[1])
            if data[2] is not None:
                batch.Put(key + "2", data[2])

    def _saveChunk_1plus(self, chunk, batch=None, writeOptions=None):
        """
        :param chunk: PocketLeveldbChunk
        :param batch: WriteBatch
        :param writeOptions: WriteOptions
        :return: None
        """
        cx, cz = chunk.chunkPosition
        key = struct.pack('<i', cx) + struct.pack('<i', cz)

        with nbt.littleEndianNBT():
            mcedit_defs = self.level.defsIds.mcedit_defs
            defs_get = mcedit_defs.get
            ids_get = self.level.defsIds.mcedit_ids.get
            tileEntityData = ''
            for ent in chunk.TileEntities:
                tileEntityData += ent.save(compressed=False)

            entityData = ''
            for ent in chunk.Entities:
                v = ent["id"].value
                ent_data = defs_get(ids_get(v, v), {'id': -1})
                id = ent_data['id']
                ent['id'] = nbt.TAG_Int(id + mcedit_defs['entity_types'].get(ent_data.get('type', None),0))
                entityData += ent.save(compressed=False)
                # We have to re-invert after saving otherwise the next save will fail.
                ent["id"] = nbt.TAG_String(v)

        wop = self.writeOptions if writeOptions is None else writeOptions
        chunk._Blocks.update_subchunks()
        chunk._Data.subchunks = chunk._Blocks.subchunks
        chunk._Data.update_subchunks()
        chunk._extra_blocks.subchunks = chunk._Blocks.subchunks
        chunk._extra_blocks_data.subchunks = chunk._Blocks.subchunks
        chunk._extra_blocks.update_subchunks()
        chunk._extra_blocks_data.update_subchunks()
        data_2d = getattr(chunk, 'data_2d', None)
        if hasattr(chunk, 'Biomes') and data_2d:
            data_2d = data_2d[:512] + chunk.Biomes.tostring()
        if chunk.chunk_version == "\x03":
            chunk._SkyLight.subchunks = chunk._Blocks.subchunks
            chunk._SkyLight.update_subchunks()
            chunk._BlockLight.subchunks = chunk._Blocks.subchunks
            chunk._BlockLight.update_subchunks()
        chunk.subchunks = chunk._Blocks.subchunks

        for y in chunk.subchunks:
            c = chr(y)
            ver = chr(8)
            if chunk._Blocks.binary_data[y] is None or chunk._Data.binary_data[y] is None:
                continue

            blocks = chunk._Blocks.binary_data[y].ravel()
            blockData = chunk._Data.binary_data[y].ravel()
            blocks_storage = get_blocks_storage_from_blocks_and_data(blocks, blockData)

            if hasattr(chunk, "_extra_blocks") and chunk._extra_blocks.binary_data[y].max() > 0:
                extra_blocks = chunk._extra_blocks.binary_data[y].ravel()
                extra_blocks_data = chunk._extra_blocks_data.binary_data[y].ravel()
                extra_blocks_storage = get_blocks_storage_from_blocks_and_data(extra_blocks, extra_blocks_data)
                num_of_storages = 2
            else:
                extra_blocks_storage = ""
                num_of_storages = 1

            terrain = ver + chr(num_of_storages) + blocks_storage + extra_blocks_storage

            if batch is None:
                with self.world_db() as db:
                    if blocks is None or blockData is None or (numpy.all(chunk._Blocks.binary_data[y] == 0) and numpy.all(chunk._Data.binary_data[y] == 0)):
                        db.Delete(key + "\x2f" + c)
                    else:
                        db.Put(wop, key + "\x2f" + c, terrain)
                    if y == 0:
                        db.Put(wop, key + '\x76', chunk.chunk_version)
                        if len(chunk.TileEntities) > 0:
                            db.Put(wop, key + '\x31', tileEntityData)
                        else:
                            db.Delete(key + '\x31')
                        if len(chunk.Entities) > 0:
                            db.Put(wop, key + '\x32', entityData)
                        else:
                            db.Delete(key + '\x32')
                        if data_2d:
                            db.Put(wop, key + '\x2d', data_2d)
            else:
                if blocks is None or blockData is None or (numpy.all(chunk._Blocks.binary_data[y] == 0) and numpy.all(chunk._Data.binary_data[y] == 0)):
                    batch.Delete(key + "\x2f" + c)
                else:
                    batch.Put(key + "\x2f" + c, terrain)
                if y == 0:
                    batch.Put(key + '\x76', chunk.chunk_version)
                    if len(chunk.TileEntities) > 0:
                        batch.Put(key + '\x31', tileEntityData)
                    else:
                        batch.Delete(key + '\x31')
                    if len(chunk.Entities) > 0:
                        batch.Put(key + '\x32', entityData)
                    else:
                        batch.Delete(key + '\x32')
                    if data_2d:
                        batch.Put(key + '\x2d', data_2d)

    def saveChunk(self, chunk, batch=None, writeOptions=None):
        """
        Wrapper for the methods corresponding to the world version.
        :param chunk: PocketLeveldbChunk
        :param batch: WriteBatch
        :param writeOptions: WriteOptions
        :return: None
        """
        # Check the chunk version, since PE 1.0+ can contain pre 1.0+ chunks
        ver = chunk.chunk_version
        if ver == "\x02":
            self._saveChunk_pre1_0(chunk, batch, writeOptions)
        elif ord(ver) >= 3:
            self._saveChunk_1plus(chunk, batch, writeOptions)
        else:
            raise AttributeError("Unknown version %s for chunk %s"%(ver, chunk.chunkPosition()))

    def loadChunk(self, cx, cz, world):
        """
        :param cx, cz: int Coordinates of the chunk
        :param world: PocketLeveldbWorld
        :return: PocketLeveldbChunk
        """
        chunk = self._readChunk(cx, cz, world)
        return chunk

    _allChunks = None

    def deleteChunk(self, cx, cz, batch=None):
        if self.world_version == 'pre1.0':
            keys = [struct.pack('<i', cx) + struct.pack('<i', cz) + "0"]
        else:
            keys = []
            keys_append = keys.append
            coords_str = struct.pack('<i', cx) + struct.pack('<i', cz)
            for i in xrange(16):
                keys_append(coords_str + "\x2f" + chr(i))
            for k in ("\x2d", "\x2e", "\x30", "\x31", "\x32", "\x33", "\x34",
                      "\x35", "\x36", "\x76"):
                keys_append(coords_str + k)

        if batch is None:
            with self.world_db() as db:
                for key in keys:
                    db.Delete(key)
        else:
            for key in keys:
                batch.Delete(key)

        logger.debug("DELETED CHUNK %s %s" % (cx, cz))

    def getAllChunks(self, readOptions=None, world_version=None):
        """
        Returns a list of all chunks that have terrain data in the database.
        Chunks with only Entities or TileEntities are ignored.
        :param readOptions: ReadOptions
        :param world_version: game version to read the data for. Default: None.
        :return: list
        """
        allChunks = set()
        with self.world_db() as db:
            if not world_version:
                world_version = self.world_version
            rop = self.readOptions if readOptions is None else readOptions

            it = db.NewIterator(rop)
            it.SeekToFirst()
            if it.Valid():
                firstKey = it.key()
            else:
                # ie the database is empty
                return []

            it.SeekToLast()
            key = ''
            while key[0:8] != firstKey[0:8]:
                key = it.key()
                if len(key) >= 8:
                    try:
                        if world_version == 'pre1.0':
                            val = db.Get(rop, key[:8] + '\x30')
                        elif world_version == '1.plus':
                            val = db.Get(rop, key[:8]+'\x76')
                        # if the above key exists it is a valid chunk so add it
                        if val is not None:
                            allChunks.add(struct.unpack('<2i', key[:8]))
                    except RuntimeError:
                        pass

                # seek to the first key with this beginning and go one further
                it.seek(key[:8])
                it.stepBackward()

            it.status()  # All this does is cause an exception if something went wrong. Might be unneeded?
            del it
        return allChunks

    def getAllPlayerData(self, readOptions=None):
        """
        Returns the raw NBT data of all players in the database.
        Every player is stored as player_<player-id>. The single-player player is stored as ~local_player
        :param readOptions:
        :return: dictonary key, value: key: player-id, value = player nbt data as str
        """
        with self.world_db() as db:
            allPlayers = {}
            rop = self.readOptions if readOptions is None else readOptions

            try:
                allPlayers["~local_player"] = db.Get(rop, "~local_player")
            except RuntimeError:
                pass

            it = db.NewIterator(rop)
            it.seek("player_")
            key = it.key()
            while it.Valid() and key.startswith("player_"):
                allPlayers[key] = it.value()
                it.stepForward()
                key = it.key()

            del it
            return allPlayers

    def savePlayer(self, player, playerData, batch=None, writeOptions=None):
        if writeOptions is None:
            writeOptions = self.writeOptions
        if batch is None:
            with self.world_db() as db:
                db.Put(writeOptions, player, playerData)
        else:
            batch.Put(player, playerData)


# =====================================================================
class PocketLeveldbWorld(ChunkedLevelMixin, MCLevel):

    # Methods are missing and prvent some parts of MCEdit to work properly.
    # brush.py need copyChunkFrom()

#     Height = 128 # Let that being defined by the world version
    Width = 0
    Length = 0

    isInfinite = True
    materials = pocketMaterials
    noTileTicks = True
    _bounds = None
    oldPlayerFolderFormat = False

    _allChunks = None  # An array of cx, cz pairs.
    _loadedChunks = {}  # A dictionary of actual PocketLeveldbChunk objects mapped by (cx, cz)
    _playerData = None
    playerTagCache = {}
    _playerList = None

    entityClass = entity.PocketEntity

    world_version = None # to be set to 'pre1.0' or '1.plus'
    # It may happen that 1+ world has a an internale .dat version set to pre 1 (0x04).
    # Let store this internal .dat version to be able to deal with mixed pre 1 and 1+ chunks.
    dat_world_version = None
    _gamePlatform = 'PE'

    @property
    def LevelName(self):
        root_tag = self.root_tag["Data"]
        if "LevelName" not in root_tag:
            with open(os.path.join(self.worldFile.path, "levelname.txt"), 'r') as f:
                name = f.read()
            if name is None:
                name = os.path.basename(self.worldFile.path)
            root_tag["LevelName"] = name
        return root_tag["LevelName"].value

    @LevelName.setter
    def LevelName(self, name):
        self.root_tag["Data"]["LevelName"] = nbt.TAG_String(value=name)
        with open(os.path.join(self.worldFile.path, "levelname.txt"), 'w') as f:
            f.write(name)

    @property
    def allChunks(self):
        """
        :return: list with all chunks in the world.
        """
        if self._allChunks is None:
            self._allChunks = self.worldFile.getAllChunks()
            if self.world_version == '1.plus' and self.dat_world_version == '\x04':
                self._allChunks.union(self.worldFile.getAllChunks(world_version='pre1.0'))
        return self._allChunks

    @property
    def chunkCount(self):
        """Returns the number of chunks in the level. May initiate a costly chunk scan."""
        if len(self._loadedChunks) != 0:
            return len(self._loadedChunks)
        else:
            return len(self.allChunks)

    @property
    def players(self):
        if self._playerList is None:
            self._playerList = []
            for key in self.playerData.keys():
                self._playerList.append(key)
        return self._playerList

    @property
    def playerData(self):
        if self._playerData is None:
            self._playerData = self.worldFile.getAllPlayerData()
        return self._playerData

    @staticmethod
    def getPlayerPath(player, dim=0):
        """
        player.py loads players from files, but PE caches them differently. This is necessary to make it work.
        :param player: str
        :param dim: int
        :return: str
        """
        if dim == 0:
            return player

    def __init__(self, filename=None, create=False, random_seed=None, last_played=None, readonly=False, height=None):
        """
        :param filename: path to the root dir of the level
        :param create: bool or hexstring/int: wether to create the level. If bool, only False is allowed.
            Hex strings or ints must reflect a valid PE world version as '\x02' or 5.
        :return:
        """
        if not os.path.isdir(filename):
            filename = os.path.dirname(filename)

        # Can we rely on this to know which version of PE was used to create the world?
        # Looks like that 1+ world can also have a storage version equal to 4...
        if not create:
            self.dat_world_version = open(os.path.join(filename, 'level.dat')).read(1)
            if ord(self.dat_world_version) >= 5:
                self.world_version = '1.plus'
                self.Height = 256
            else:
                self.world_version = 'pre1.0'
                self.Height = 128

            logger.info('PE world verion found: %s (%s)' % (self.world_version, repr(self.dat_world_version)))
        else:
            self.world_version = create
            if height is not None:
                self.Height = height
            logger.info('Creating PE world version %s (%s)' % (self.world_version, repr(self.dat_world_version)))

        self.filename = filename
        self.worldFile = PocketLeveldbDatabase(filename, self, create=create, world_version=self.world_version, dat_world_version=self.dat_world_version)

        self.world_version = self.worldFile.world_version
        self.readonly = readonly
        self.loadLevelDat(create, random_seed, last_played)

        self.worldFolder = AnvilWorldFolder(filename)
        workFolderPath2 = self.worldFolder.getFolderPath("##MCEDIT.TEMP2##")
        if os.path.exists(workFolderPath2):
            shutil.rmtree(workFolderPath2, True)
        self.fileEditsFolder = AnvilWorldFolder(workFolderPath2)
        self.editFileNumber = 1

    def _createLevelDat(self, random_seed, last_played):
        """
        Creates a new level.dat root_tag, and puts it in self.root_tag.
        To write it to the disk, self.save() should be called.
        :param random_seed: long
        :param last_played: long
        :return: None
        """
        with nbt.littleEndianNBT():
            root_tag = nbt.TAG_Compound()
            root_tag["Data"] = nbt.TAG_Compound()
            root_tag["Data"]["SpawnX"] = nbt.TAG_Int(0)
            root_tag["Data"]["SpawnY"] = nbt.TAG_Int(2)
            root_tag["Data"]["SpawnZ"] = nbt.TAG_Int(0)

            if last_played is None:
                last_played = long(time.time() * 100)
            if random_seed is None:
                random_seed = long(numpy.random.random() * 0xffffffffffffffffL) - 0x8000000000000000L

            self.root_tag = root_tag

            self.LastPlayed = long(last_played)
            self.RandomSeed = long(random_seed)
            self.SizeOnDisk = 0
            self.Time = 1
            self.LevelName = os.path.basename(self.worldFile.path)

    def loadLevelDat(self, create=False, random_seed=None, last_played=None):
        """
        Loads the level.dat from the worldfolder.
        :param create: bool. If it's True, a fresh level.dat will be created instead.
        :param random_seed: long
        :param last_played: long
        :return: None
        """
        def _loadLevelDat(filename):
            root_tag_buf = open(filename, 'rb').read()
            magic, length, root_tag_buf = root_tag_buf[:4], root_tag_buf[4:8], root_tag_buf[8:]
            if struct.Struct('<i').unpack(magic)[0] < 3:
                logger.info("Found an old level.dat file. Aborting world load")
                raise InvalidPocketLevelDBWorldException()  # Maybe try convert/load old PE world?
            if len(root_tag_buf) != struct.Struct('<i').unpack(length)[0]:
                raise nbt.NBTFormatError()
            self.root_tag = nbt.TAG_Compound()
            level_nbt_data = nbt.load(buf=root_tag_buf)
            if "Data" in level_nbt_data:
                self.root_tag = level_nbt_data
            else:
                self.root_tag["Data"] = nbt.load(buf=root_tag_buf)

        if create:
            print "Creating PE level.dat"
            self._createLevelDat(random_seed, last_played)
            return
        try:
            with nbt.littleEndianNBT():
                _loadLevelDat(os.path.join(self.worldFile.path, "level.dat"))
            return
        except (nbt.NBTFormatError, IOError) as err:
            logger.info("Failed to load level.dat, trying to load level.dat_old ({0})".format(err))
        try:
            with nbt.littleEndianNBT():
                _loadLevelDat(os.path.join(self.worldFile.path, "level.dat_old"))
            return
        except (nbt.NBTFormatError, IOError) as err:
            logger.info("Failed to load level.dat_old, creating new level.dat ({0})".format(err))
        self._createLevelDat(random_seed, last_played)

    # --- NBT Tag variables ---

    SizeOnDisk = TagProperty('SizeOnDisk', nbt.TAG_Int, 0)
    RandomSeed = TagProperty('RandomSeed', nbt.TAG_Long, 0)

    # TODO PE worlds have a different day length, this has to be changed to that.
    Time = TagProperty('Time', nbt.TAG_Long, 0)
    LastPlayed = TagProperty('LastPlayed', nbt.TAG_Long, lambda self: long(time.time() * 1000))

    GeneratorName = TagProperty('Generator', nbt.TAG_String, 'Infinite')

    GameType = TagProperty('GameType', nbt.TAG_Int, 0)

    def defaultDisplayName(self):
        return os.path.basename(os.path.dirname(self.filename))

    def __str__(self):
        """
        How to represent this level
        :return: str
        """
        return "PocketLeveldbWorld(\"%s\")" % os.path.basename(os.path.dirname(self.worldFile.path))

    def getChunk(self, cx, cz):
        """
        Used to obtain a chunk from the database.
        :param cx, cz: cx, cz coordinates of the chunk
        :return: PocketLeveldbChunk
        """
        if DEBUG_PE:
            write_dump("*** Getting chunk %s,%s\n"%(cx, cz))
        c = self._loadedChunks.get((cx, cz))
        if c is None:
            if DEBUG_PE:
                write_dump("    Not loaded, loading\n")
            c = self.worldFile.loadChunk(cx, cz, self)
            self._loadedChunks[(cx, cz)] = c
            if DEBUG_PE:
                write_dump("*** Loaded chunks num.: %s\n" % len(self._loadedChunks))
        return c

    def unload(self):
        """
        Unload all chunks and close all open file-handlers.
        """
        self._loadedChunks.clear()
        self._allChunks = None
        self.worldFile.close()

    def close(self):
        """
        Unload all chunks and close all open file-handlers. Discard any unsaved data.
        """
        self.playerTagCache.clear()
        self.unload()
        try:
            shutil.rmtree(self.fileEditsFolder.filename, True)
            # Setup a way to close a work-folder?
        except SessionLockLost:
            pass

    def deleteChunk(self, cx, cz, batch=None):
        """
        Deletes a chunk at given cx, cz. Deletes using the batch if batch is given, uses world_db() otherwise.
        :param cx, cz Coordinates of the chunk
        :param batch WriteBatch
        :return: None
        """
        self.worldFile.deleteChunk(cx, cz, batch=batch)
        if self._loadedChunks is not None and (cx, cz) in self._loadedChunks:  # Unnecessary check?
            del self._loadedChunks[(cx, cz)]
            self.allChunks.remove((cx, cz))

    def deleteChunksInBox(self, box):
        """
        Deletes all chunks in a given box.
        :param box pymclevel.box.BoundingBox
        :return: None
        """
        logger.info(u"Deleting {0} chunks in {1}".format((box.maxcx - box.mincx) * (box.maxcz - box.mincz),
                                                         ((box.mincx, box.mincz), (box.maxcx, box.maxcz))))
        i = 0
        ret = []
        batch = leveldb_mcpe.WriteBatch()
        for cx, cz in itertools.product(xrange(box.mincx, box.maxcx), xrange(box.mincz, box.maxcz)):
            i += 1
            if self.containsChunk(cx, cz):
                self.deleteChunk(cx, cz, batch=batch)
                ret.append((cx, cz))

            assert not self.containsChunk(cx, cz), "Just deleted {0} but it didn't take".format((cx, cz))

            if i % 100 == 0:
                logger.info(u"Chunk {0}...".format(i))

        with self.worldFile.world_db() as db:
            wop = self.worldFile.writeOptions
            db.Write(wop, batch)

        del batch
        return ret

    @property
    def bounds(self):
        """
        Returns a boundingbox containing the entire level
        :return: pymclevel.box.BoundingBox
        """
        if self._bounds is None:
            self._bounds = self._getWorldBounds()
        return self._bounds

    @property
    def size(self):
        return self.bounds.size

    def _getWorldBounds(self):
        allChunks = self.allChunks
        if not allChunks:
            return BoundingBox((0, 0, 0), (0, 0, 0))

        allChunks = numpy.array(list(allChunks))
        min_cx = (allChunks[:, 0]).min()
        max_cx = (allChunks[:, 0]).max()
        min_cz = (allChunks[:, 1]).min()
        max_cz = (allChunks[:, 1]).max()

        origin = (min_cx << 4, 0, min_cz << 4)
        size = ((max_cx - min_cx + 1) << 4, self.Height, (max_cz - min_cz + 1) << 4)

        return BoundingBox(origin, size)

    @classmethod
    def _isLevel(cls, filename):
        """
        Determines whether or not the path in filename has a Pocket Edition 0.9.0 or later in it
        :param filename string with path to level root directory.
        """
        clp = ("db", "level.dat")
        if not os.path.isdir(filename):
            f = os.path.basename(filename)
            if f not in clp:
                return False
            filename = os.path.dirname(filename)

        return all([os.path.exists(os.path.join(filename, fl)) for fl in clp])

    def saveInPlaceGen(self):
        """
        Save all chunks to the database, and write the root_tag back to level.dat.
        """
        if DEBUG_PE:
            open(dump_fName, 'a').write("*** saveInPlaceGen\n")
        self.saving = True
        batch = leveldb_mcpe.WriteBatch()
        dirtyChunkCount = 0
        for c in self.chunksNeedingLighting:
            self.getChunk(*c).genFastLights()

        for chunk in self._loadedChunks.itervalues():
            if chunk.dirty:
                dirtyChunkCount += 1
                self.worldFile.saveChunk(chunk, batch=batch)
                chunk.dirty = False
            yield

        with nbt.littleEndianNBT():
            for p in self.players:
                # The player data may not be in the cache if we have multi-player game.
                # So, accessing the cache using the player as key crashes the program...
                playerData = self.playerTagCache.get(p)
                if playerData is not None:
                    playerData = playerData.save(compressed=False)  # It will get compressed in the DB itself
                    self.worldFile.savePlayer(p, playerData, batch=batch)

        with self.worldFile.world_db() as db:
            wop = self.worldFile.writeOptions
            db.Write(wop, batch)

        self.saving = False
        logger.info(u"Saved {0} chunks to the database".format(dirtyChunkCount))
        path = os.path.join(self.worldFile.path, 'level.dat')
        with nbt.littleEndianNBT():
            rootTagData = self.root_tag["Data"].save(compressed=False)
#             if self.world_version == '1.plus':
#                 magic = 5
#             else:
#                 magic = 4

            magic = self.dat_world_version
            if isinstance(magic, (str, unicode)):
                magic = ord(magic)

            rootTagData = struct.Struct('<i').pack(magic) + struct.Struct('<i').pack(len(rootTagData)) + rootTagData
            with open(path, 'wb') as f:
                f.write(rootTagData)

    def containsChunk(self, cx, cz):
        """
        Determines if the chunk exist in this world.
        :param cx, cz: int, Coordinates of the chunk
        :return: bool (if chunk exists)
        """
        return (cx, cz) in self.allChunks

    def createChunk(self, cx, cz):
        """
        Creates an empty chunk at given cx, cz coordinates, and stores it in self._loadedChunks
        :param cx, cz: int, Coordinates of the chunk
        :return:
        """
        if self.containsChunk(cx, cz):
            raise ValueError("{0}:Chunk {1} already present!".format(self, (cx, cz)))
        if self.allChunks is not None:
            self.allChunks.add((cx, cz))

        if self.world_version == 'pre1.0':
            self._loadedChunks[(cx, cz)] = PocketLeveldbChunkPre1(cx, cz, self, create=True, world_version=self.world_version)
        else:
            self._loadedChunks[(cx, cz)] = PocketLeveldbChunk1Plus(cx, cz, self, create=True, world_version=self.world_version)

        self._bounds = None

    def saveGeneratedChunk(self, cx, cz, tempChunkBytes):
        """
        Chunks get generated using Anvil generation. This is a (slow) way of importing anvil chunk bytes
        and converting them to MCPE chunk data. Could definitely use some improvements, but at least it works.
        :param cx, cx: Coordinates of the chunk
        :param tempChunkBytes: str. Raw MCRegion chunk data.
        :return:
        """
        loaded_data = nbt.load(buf=tempChunkBytes)

        class fake:
            def __init__(self):
                self.Height = 128

        tempChunk = AnvilChunkData(fake(), (0, 0), loaded_data)

        if not self.containsChunk(cx, cz):
            self.createChunk(cx, cz)
            chunk = self.getChunk(cx, cz)
            chunk.Blocks = numpy.array(tempChunk.Blocks, dtype='uint16')
            chunk.Data = numpy.array(tempChunk.Data, dtype='uint8')
            chunk.SkyLight = numpy.array(tempChunk.SkyLight, dtype='uint8')
            chunk.BlockLight = numpy.array(tempChunk.BlockLight, dtype='uint8')

            chunk.dirty = True
            self.worldFile.saveChunk(chunk)
        else:
            logger.info("Tried to import generated chunk at %s, %s but the chunk already existed."%(cx, cz))

    @property
    def chunksNeedingLighting(self):
        """
        Generator containing all chunks that need lighting.
        :yield: int (cx, cz) Coordinates of the chunk
        """
        for chunk in self._loadedChunks.itervalues():
            if chunk.needsLighting:
                yield chunk.chunkPosition

    # -- Entity Stuff --

    # A lot of this code got copy-pasted from MCInfDevOldLevel
    # Slight modifications to make it work with MCPE

    def getTileEntitiesInBox(self, box):
        """
        Returns the Tile Entities in given box.
        :param box: pymclevel.box.BoundingBox
        :return: list of nbt.TAG_Compound
        """
        tileEntites = []
        for chunk, slices, point in self.getChunkSlices(box):
            tileEntites += chunk.getTileEntitiesInBox(box)

        return tileEntites

    def getEntitiesInBox(self, box):
        """
        Returns the Entities in given box.
        :param box: pymclevel.box.BoundingBox
        :return: list of nbt.TAG_Compound
        """
        entities = []
        for chunk, slices, point in self.getChunkSlices(box):
            entities += chunk.getEntitiesInBox(box)

        return entities

    def getTileTicksInBox(self, box):
        """
        Always returns None, as MCPE has no TileTicks.
        :param box: pymclevel.box.BoundingBox
        :return: list
        """
        return []

    def addEntity(self, entityTag):
        """
        Adds an entity to the level.
        :param entityTag: nbt.TAG_Compound containing the entity's data.
        :return:
        """
        assert isinstance(entityTag, nbt.TAG_Compound)
        x, y, z = map(lambda p: int(floor(p)), Entity.pos(entityTag))

        try:
            chunk = self.getChunk(x >> 4, z >> 4)
        except (ChunkNotPresent, ChunkMalformed):
            return
        chunk.addEntity(entityTag)
        chunk.dirty = True

    def addTileEntity(self, tileEntityTag):
        """
        Adds an entity to the level.
        :param tileEntityTag: nbt.TAG_Compound containing the Tile entity's data.
        :return:
        """
        assert isinstance(tileEntityTag, nbt.TAG_Compound)
        if 'x' not in tileEntityTag:
            return
        x, y, z = TileEntity.pos(tileEntityTag)

        try:
            chunk = self.getChunk(x >> 4, z >> 4)
        except (ChunkNotPresent, ChunkMalformed):
            return
        chunk.addTileEntity(tileEntityTag)
        chunk.dirty = True

    def addTileTick(self, tickTag):
        """
        MCPE doesn't have Tile Ticks, so this can't be added.
        :param tickTag: nbt.TAG_Compound
        :return: None
        """
        return

    def tileEntityAt(self, x, y, z):
        """
        Retrieves a tile entity at given x, y, z coordinates
        :param x: int
        :param y: int
        :param z: int
        :return: nbt.TAG_Compound or None
        """
        chunk = self.getChunk(x >> 4, z >> 4)
        return chunk.tileEntityAt(x, y, z)

    def removeEntitiesInBox(self, box):
        """
        Removes all entities in given box
        :param box: pymclevel.box.BoundingBox
        :return: int, count of entities removed
        """
        count = 0
        for chunk, slices, point in self.getChunkSlices(box):
            count += chunk.removeEntitiesInBox(box)

        logger.info("Removed {0} entities".format(count))
        return count

    def removeTileEntitiesInBox(self, box):
        """
        Removes all tile entities in given box
        :param box: pymclevel.box.BoundingBox
        :return: int, count of tile entities removed
        """
        count = 0
        for chunk, slices, point in self.getChunkSlices(box):
            count += chunk.removeTileEntitiesInBox(box)

        logger.info("Removed {0} tile entities".format(count))
        return count

    def removeTileTicksInBox(self, box):
        """
        MCPE doesn't have TileTicks, so this does nothing.
        :param box: pymclevel.box.BoundingBox
        :return: int, count of TileTicks removed.
        """
        return 0

    # -- Player and spawn stuff

    def playerSpawnPosition(self, player=None):
        """
        Returns the default spawn position for the world. If player is given, the players spawn is returned instead.
        :param player: nbt.TAG_Compound, root tag of the player.
        :return: tuple int (x, y, z), coordinates of the spawn.
        """
        dataTag = self.root_tag["Data"]
        if player is None:
            playerSpawnTag = dataTag
        else:
            playerSpawnTag = self.getPlayerTag(player)

        return [playerSpawnTag.get(i, dataTag[i]).value for i in ("SpawnX", "SpawnY", "SpawnZ")]

    def setPlayerSpawnPosition(self, pos, player=None):
        """
        Sets the worlds spawn point to pos. If player is given, sets that players spawn point instead.
        :param pos: tuple int (x, y, z)
        :param player: nbt.TAG_Compound, root tag of the player
        :return: None
        """
        if player is None:
            playerSpawnTag = self.root_tag["Data"]
        else:
            playerSpawnTag = self.getPlayerTag(player)
        for name, val in zip(("SpawnX", "SpawnY", "SpawnZ"), pos):
            playerSpawnTag[name] = nbt.TAG_Int(val)

    def getPlayerTag(self, player='Player'):
        """
        Obtains a player from the world.
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: nbt.TAG_Compound, root tag of the player.
        """
        if player == '[No players]':  # Apparently this is being called somewhere?
            return None
        if player == 'Player':
            player = '~local_player'
        _player = self.playerTagCache.get(player)
        if _player is not None:
            return _player
        playerData = self.playerData[player]
        with nbt.littleEndianNBT():
            _player = nbt.load(buf=playerData)
            self.playerTagCache[player] = _player
        return _player

    def getPlayerDimension(self, player="Player"):
        """
        Always returns 0, as MCPE only has the overworld dimension.
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: int
        """
        return 0

    def setPlayerPosition(self, (x, y, z), player="Player"):
        """
        Sets the players position to x, y, z
        :param (x, y, z): tuple of the coordinates of the player
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return:
        """
        playerTag = self.getPlayerTag(player)
        nbt_type = type(playerTag["Pos"][0])
        posList = nbt.TAG_List([nbt_type(p) for p in (x, y - 1.75, z)])

        playerTag["Pos"] = posList

    def getPlayerPosition(self, player="Player"):
        """
        Gets the players position
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: tuple int (x, y, z): Coordinates of the player.
        """
        playerTag = self.getPlayerTag(player)
        posList = playerTag["Pos"]
        x, y, z = map(lambda c: c.value, posList)
        return x, y + 1.75, z

    def setPlayerOrientation(self, yp, player="Player"):
        """
        Gets the players orientation.
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :param yp: int tuple (yaw, pitch)
        :return: None
        """
        self.getPlayerTag(player)["Rotation"] = nbt.TAG_List([nbt.TAG_Float(p) for p in yp])

    def getPlayerOrientation(self, player="Player"):
        """
        Gets the players orientation.
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: tuple int (yaw, pitch)
        """
        yp = map(lambda x: x.value, self.getPlayerTag(player)["Rotation"])
        y, p = yp
        if p == 0:
            p = 0.000000001
        if p == 180.0:
            p -= 0.000000001
        yp = y, p
        return numpy.array(yp)

    @staticmethod  # Editor keeps putting this in. Probably unnecesary
    def setPlayerAbilities(gametype, player="Player"):
        """
        This method is just to override the standard one, as MCPE has no abilities, as it seems.
        :parm gametype, int of gamemode player gets set at.
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        """
        pass

    def setPlayerGameType(self, gametype, player="Player"):
        """
        Sets the game type for player
        :param gametype: int (0=survival, 1=creative, 2=adventure, 3=spectator)
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: None
        """

        # This annoyingly works differently between single- and multi-player.
        if player == "Player":
            self.GameType = gametype
            self.setPlayerAbilities(gametype, player)
        else:
            playerTag = self.getPlayerTag(player)
            playerTag['playerGameType'] = nbt.TAG_Int(gametype)
            self.setPlayerAbilities(gametype, player)

    def getPlayerGameType(self, player="Player"):
        """
        Obtains the players gametype.
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: int (0=survival, 1=creative, 2=adventure, 3=spectator)
        """
        if player == "Player":
            return self.GameType
        else:
            playerTag = self.getPlayerTag(player)
            return playerTag["playerGameType"].value

    def markDirtyChunk(self, cx, cz):
        self.getChunk(cx, cz).chunkChanged()

    def markDirtyBox(self, box):
        for cx, cz in box.chunkPositions:
            self.markDirtyChunk(cx, cz)

    def setSpawnerData(self, tile_entity, mob_id):
        """Set the data in a given mob spawner.

        tile_entity: TileEntity object: the mob spawner to update.
        mod_id: str/unicode: the mob string id to update the spawner with.

        Return tile_entity
        """
        fullid = self.defsIds.mcedit_defs.get(self.defsIds.mcedit_ids.get(mob_id, "Unknown"), {}).get("fullid", None)
#         print fullid
        if fullid is not None:
            # This is mostly a copy of what we have in camera.py.
            # Has to be optimized for PE...
            if "EntityId" in tile_entity:
                tile_entity["EntityId"] = nbt.TAG_Int(fullid)
            if "SpawnData" in tile_entity:
                # Try to not clear the spawn data, but only update the mob id
                tag_id = nbt.TAG_Int(fullid)
                if "id" in tile_entity["SpawnData"]:
                    tag_id.name = "id"
                    tile_entity["SpawnData"]["id"] = tag_id
                if "EntityId" in tile_entity["SpawnData"]:
                    tile_entity["SpawnData"]["EntityId"] = tag_id
            if "SpawnPotentials" in tile_entity:
                for potential in tile_entity["SpawnPotentials"]:
                    if "Entity" in potential:
                        # MC 1.9+
                        if potential["Entity"]["id"].value == id or ("EntityId" in potential["Entity"] and potential["Entity"]["EntityId"].value == id):
                            potential["Entity"] = nbt.TAG_Compound()
                            potential["Entity"]["id"] = nbt.TAG_Int(fullid)
                    elif "Properties" in potential:
                        # MC before 1.9
                        if "Type" in potential and potential["Type"].value == id:
                            potential["Type"] = nbt.TAG_Int(fullid)
        else:
            raise AttributeError("Could not find entity data for '%s' in MCEDIT_DEFS"%mob_id)
        return tile_entity


# =====================================================================
class PocketLeveldbChunkPre1(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    Height = 128

    _Entities = nbt.TAG_List()
    _TileEntities = nbt.TAG_List()
    dirty = False
    chunk_version = "\x02"

    def __init__(self, cx, cz, world, data=None, create=False, world_version=None):
        """
        :param cx, cz int, int Coordinates of the chunk
        :param data List of 3 strings. (83200 bytes of terrain data, tile-entity data, entity data)
        :param world PocketLeveldbWorld, instance of the world the chunk belongs too
        """
        self.world_version = world_version  # For info and tracking
        self.chunkPosition = (cx, cz)
        self.world = world

        if create:
            self.Blocks = numpy.zeros(32768, 'uint16')
            self.Data = numpy.zeros(16384, 'uint8')
            self.SkyLight = numpy.zeros(16384, 'uint8')
            self.BlockLight = numpy.zeros(16384, 'uint8')
            self.DirtyColumns = numpy.zeros(256, 'uint8')
            self.GrassColors = numpy.zeros(1024, 'uint8')

            self.TileEntities = nbt.TAG_List()
            self.Entities = nbt.TAG_List()

        else:
            terrain = numpy.fromstring(data[0], dtype='uint8')
            if data[1] is not None:
                if DEBUG_PE:
                    write_dump(('/' * 80) + '\nParsing TileEntities in chunk %s,%s\n' % (cx, cz))
                TileEntities = loadNBTCompoundList(data[1])
                self.TileEntities = nbt.TAG_List(TileEntities, list_type=nbt.TAG_COMPOUND)

            if data[2] is not None:
                if DEBUG_PE:
                    write_dump(('\\' * 80) + '\nParsing Entities in chunk %s,%s\n' % (cx, cz))
                Entities = loadNBTCompoundList(data[2])
                # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
                # Whenever we save an entity, we need to make sure to swap back.
                defs_get = self.world.defsIds.mcedit_defs.get
                ids_get = self.world.defsIds.mcedit_ids.get
                for ent in Entities:
                    # Get the string id, or a build one
                    # ! For PE debugging
                    try:
                        v = ent["id"].value
                    except Exception as e:
                        logger.warning("An error occured while getting entity ID:")
                        logger.warning(e)
                        logger.warning("Default 'Unknown' ID is used...")
                        v = 'Unknown'

                    id = defs_get(ids_get(v, 'Unknown'),
                                         {'name': 'Unknown Entity %s' % v,
                                          'idStr': 'Unknown Entity %s' % v,
                                          'id': -1}
                                         )['name']
                    ent["id"] = nbt.TAG_String(id)
                self.Entities = nbt.TAG_List(Entities, list_type=nbt.TAG_COMPOUND)

            self.Blocks, terrain = terrain[:32768], terrain[32768:]
            self.Data, terrain = terrain[:16384], terrain[16384:]
            self.SkyLight, terrain = terrain[:16384], terrain[16384:]
            self.BlockLight, terrain = terrain[:16384], terrain[16384:]
            self.DirtyColumns, terrain = terrain[:256], terrain[256:]

            # Unused at the moment. Might need a special editor? Maybe hooked up to biomes?
            self.GrassColors = terrain[:1024]

        self._unpackChunkData()
        self.shapeChunkData()

    def _unpackChunkData(self):
        """
        Unpacks the terrain data to match mcedit's formatting.
        """
        for key in ('SkyLight', 'BlockLight', 'Data'):
            dataArray = getattr(self, key)
            dataArray.shape = (16, 16, 64)
            s = dataArray.shape

            unpackedData = numpy.zeros((s[0], s[1], s[2] * 2), dtype='uint8')

            unpackedData[:, :, ::2] = dataArray
            unpackedData[:, :, ::2] &= 0xf
            unpackedData[:, :, 1::2] = dataArray
            unpackedData[:, :, 1::2] >>= 4
            setattr(self, key, unpackedData)

    def shapeChunkData(self):
        """
        Determines the shape of the terrain data.
        :return:
        """
        chunkSize = 16
        self.Blocks.shape = (chunkSize, chunkSize, self.Height)
        self.SkyLight.shape = (chunkSize, chunkSize, self.Height)
        self.BlockLight.shape = (chunkSize, chunkSize, self.Height)
        self.Data.shape = (chunkSize, chunkSize, self.Height)
        self.DirtyColumns.shape = chunkSize, chunkSize

    def savedData(self):
        """
        Returns the data of the chunk to save to the database.
        :return: str of 83200 bytes of chunk data.
        """

        def packData(dataArray):
            """
            Repacks the terrain data to Mojang's leveldb library's format.
            """
            assert dataArray.shape[2] == self.Height

            data = numpy.array(dataArray).reshape(16, 16, self.Height / 2, 2)
            data[..., 1] <<= 4
            data[..., 1] |= data[..., 0]
            return numpy.array(data[:, :, :, 1])

        if self.dirty:
            # elements of DirtyColumns are bitfields. Each bit corresponds to a
            # 16-block segment of the column. We set all of the bits because
            # we only track modifications at the chunk level.
            self.DirtyColumns[:] = 255

        with nbt.littleEndianNBT():
            entityData = ""
            tileEntityData = ""
            defs_get = self.world.defsIds.mcedit_defs.get
            ids_get = self.world.defsIds.mcedit_ids.get

            for ent in self.TileEntities:
                tileEntityData += ent.save(compressed=False)

            for ent in self.Entities:
                v = ent["id"].value
#                 ent["id"] = nbt.TAG_Int(entity.PocketEntity.entityList[v])
#                 id = entity.PocketEntity.getNumId(v)
#                 print v, id, MCEDIT_DEFS.get(MCEDIT_IDS.get(v, v), {'id': -1})['id']
                id = defs_get(ids_get(v, v), {'id': -1})['id']
                if id >= 1000:
                    print id
                    print type(ent)
                    print ent
                ent['id'] = nbt.TAG_Int(id)
                entityData += ent.save(compressed=False)
                # We have to re-invert after saving otherwise the next save will fail.
                ent["id"] = nbt.TAG_String(v)

        terrain = ''.join([self.Blocks.tostring(),
                           packData(self.Data).tostring(),
                           packData(self.SkyLight).tostring(),
                           packData(self.BlockLight).tostring(),
                           self.DirtyColumns.tostring(),
                           self.GrassColors.tostring(),
                           ])

        return terrain, tileEntityData, entityData

    # -- Entities and TileEntities

    @property
    def Entities(self):
        return self._Entities

    @Entities.setter
    def Entities(self, Entities):
        """
        :param Entities: list
        :return:
        """
        self._Entities = Entities

    @property
    def TileEntities(self):
        return self._TileEntities

    @TileEntities.setter
    def TileEntities(self, TileEntities):
        """
        :param TileEntities: list
        :return:
        """
        self._TileEntities = TileEntities

    @property
    def TileTicks(self):
        return nbt.TAG_List()


# =====================================================================
class PE1PlusDataContainer:
    """Container for subchunks data for MCPE 1.0+."""
    def __init__(self, subdata_length, bin_type, name='none', shape=None, chunk_height=256):
        """subdata_length: int: the length for the underlying numpy objects.
        bin_type: str: the binary data type, like uint8
        destination: numpy array class (not instance): destination object to be used by other MCEdit objects as 'chunk.Blocks', or 'chunk.Data'
                     If a subchunk does not exists, the corresponding 'destination' aera is filled with zeros
                     The 'destination is initialized filled and shaped here.
        name: str: the interna name used mainly for debug display
        shape: tuple: the subchunk array shape, unused
        """
        self.name = name
        self.subdata_length = subdata_length
        self.bin_type = bin_type
        # the first two argument for the shape always are 16
        if shape is None:
            self.shape = (16, 16, subdata_length / (16 * 16))
        else:
            self.shape = shape
        self.destination = numpy.zeros(subdata_length * (chunk_height / 16), bin_type)
        self.destination.shape = (self.shape[0], self.shape[1], chunk_height)
        self.subchunks = []  # Store here the valid subchunks as ints
        self.binary_data = [None] * 16  # Has to be a numpy arrays. This list is indexed using the subchunks content.

    def __repr__(self):
        return "PE1PlusDataContainer { subdata_length: %s, bin_type: %s, shape: %s, subchunks: %s }" % (self.subdata_length, self.bin_type, self.shape, self.subchunks)

    def __getitem__(self, x, z, y):
        subchunk = y / 16
        if subchunk in self.subchunks:
            binary_data = self.binary_data[subchunk]
            return binary_data[x, z, y - (subchunk * 16)]

    def __setitem__(self, x, z, y, data):
        subchunk = y / 16
        if subchunk in self.subchunks:
            binary_data = self.binary_data[subchunk]
            binary_data[x, z, y - (subchunk * 16)] = data

    def __len__(self):
        return len(self.subchunks) * self.subdata_length

    def add_data(self, y, data):
        """Add data to 'y' subchunk.

        y: int: the subchunk to add data to
        data: ndarray: data to be added. Must be 4096 numbers long.

        Does not raise an error if the subchunk already has data.
        The old data is overriden.
        Creates the subchunk if it does not exists.
        """
        self.binary_data[y] = data
        if len(data) != self.subdata_length:
            raise ValueError("%s: Data does not match the required %s bytes length: %s bytes"%(self.name, self.subdata_length, len(data)))
        try:
            self.binary_data[y].shape = self.shape
        except ValueError as e:
            a = list(e.args)
            a[0] += '%s %s: Required: %s, got: %s'%(a[0], self.name, self.shape, self.binary_data[y].shape)
            e.args = tuple(a)
            raise e
        self.destination[:, :, y * 16:16 + (y * 16)] = self.binary_data[y][:, :, :]
        if y not in self.subchunks:
            self.subchunks.append(y)

    def update_subchunks(self):
        """Auto-updates the existing subchunks data using the 'destination' one."""
        for y in range(16):
            sub = self.destination[:, :, y * 16:16 + (y * 16)]
            if self.destination[:, :, y * 16:].any() or self.binary_data[y] is not None or y in self.subchunks:
                self.binary_data[y] = sub
                if y not in self.subchunks:
                    self.subchunks.append(y)
        self.subchunks.sort()


# =====================================================================
class PocketLeveldbChunk1Plus(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    Height = 256

    _Entities = nbt.TAG_List()
    _TileEntities = nbt.TAG_List()
    dirty = False
    chunk_version = "\x03"

    def __init__(self, cx, cz, world, data=None, create=False, world_version=None, chunk_version=None):
        """
        cx, cz: int: coordinates of the chunk.
        world: PocketLeveldbWorld object: instance of the world the chunk belongs too.
        data: list of str: terrain, entities and tile entities data. Defaults to 'None'.
            Unused, but kept for compatibility.
        create: bool: wether to create the chunk. Defaults to 'False'.
            Unused, but kept for compatibility.
        world_version: str: used to track if the 'world' is a pre 1.0 or 1.0+ PE one. Defaults to 'None'.

        Initialize the subchunbk containers.
        """
        self.world_version = world_version  # For info and tracking
        if chunk_version:
            self.chunk_version = chunk_version
        self.chunkPosition = (cx, cz)
        self.world = world
        self.subchunks = []
        self.subchunks_versions = {}

        possible_dtypes = [2 ** x for x in range(3, 8)]
        max_blocks_dtype = int(ceil(log(max([i for i,x in enumerate(pocketMaterials.idStr) if x]), 2)))
        max_blocks_dtype = next(possible_dtype for possible_dtype in possible_dtypes if possible_dtype >= max_blocks_dtype)
        max_data_dtype = int(ceil(log(max([x[1] for x in pocketMaterials.blocksByID.keys()]), 2)))
        max_data_dtype = next(possible_dtype for possible_dtype in possible_dtypes if possible_dtype >= max_data_dtype)

        self._Blocks = PE1PlusDataContainer(4096, 'uint'+str(max_blocks_dtype), name='Blocks', chunk_height=self.Height)
        self.Blocks = self._Blocks.destination
        self._Data = PE1PlusDataContainer(4096, 'uint'+str(max_data_dtype), name='Data')
        self.Data = self._Data.destination
        self._SkyLight = PE1PlusDataContainer(4096, 'uint8', name='SkyLight')
        self.SkyLight = self._SkyLight.destination
        self.SkyLight[:] = 15
        self._BlockLight = PE1PlusDataContainer(4096, 'uint8', name='BlockLight')
        self.BlockLight = self._BlockLight.destination

        self.TileEntities = nbt.TAG_List(list_type=nbt.TAG_COMPOUND)
        self.Entities = nbt.TAG_List(list_type=nbt.TAG_COMPOUND)

        self.Biomes = numpy.zeros((16, 16), 'uint8')
        self.data2d = None

        self._extra_blocks = PE1PlusDataContainer(4096, 'uint' + str(max_blocks_dtype), name='extra_blocks', chunk_height=self.Height)
        self.extra_blocks = self._extra_blocks.destination
        self._extra_blocks_data = PE1PlusDataContainer(4096, 'uint' + str(max_data_dtype), name='extra_blocks_data')
        self.extra_blocks_data = self._extra_blocks_data.destination

    def _read_block_storage(self, storage):
        bits_per_block, storage = ord(storage[0]) >> 1, storage[1:]
        blocks_per_word = int(floor(32 / bits_per_block))
        word_count = int(ceil(4096 / float(blocks_per_word)))
        raw_blocks, storage = storage[:word_count * 4], storage[word_count * 4:]
        word_size = 32
        bin_arr = numpy.unpackbits(numpy.frombuffer(bytearray(raw_blocks), dtype='uint8')).astype(bool)

        # cut redundant bits
        word_arr = bin_arr.reshape(-1, word_size/8, 8)
        word_arr = word_arr[:, ::-1, :]
        word_arr = word_arr.reshape(-1, word_size)
        redundant_bits = word_size % bits_per_block
        clean_word_arr = word_arr[:, redundant_bits:]

        # convert blocks to uint
        clean_word_arr = clean_word_arr.reshape(-1, word_size / bits_per_block, bits_per_block)[:, ::-1]
        block_arr = clean_word_arr.reshape(-1, bits_per_block)
        block_size = max(bits_per_block, 8)
        blocks_before_palette = block_arr.dot(2**numpy.arange(block_arr.shape[1]-1, -1, -1))[:4096]
        blocks_before_palette = blocks_before_palette.astype("uint"+str(block_size))

        # This might be varint and not just 4 bytes, need to make sure
        palette_size, palette = struct.unpack("<i", storage[:4])[0], storage[4:]
        palette_nbt, storage = loadNBTCompoundList(palette, partNBT=True, count=palette_size)
        if not hasattr(pocketMaterials, 'tempBlockID'):
            pocketMaterials.tempBlockID = max([numID for numID, item in enumerate(pocketMaterials.idStr) if item]) + 1
        ids = []
        data = []
        for item in palette_nbt:
            idStr = item["name"].value.split(':',1)[-1]
            if idStr == '':
                idStr = 'air'
                item["val"] = nbt.TAG_Short(0)
            if idStr != 'air' and idStr not in pocketMaterials.idStr:
                pocketMaterials.addJSONBlock({"id": pocketMaterials.tempBlockID, "name": idStr, "idStr": idStr, "mapcolor": [214, 127, 255], "data": {n: {"name": idStr} for n in range(16)}})
                pocketMaterials.tempBlockID += 1
            if idStr == 'air':
                ids.append(0)
            elif idStr in pocketMaterials.idStr:
                ids.append(pocketMaterials.idStr.index(idStr))
            else:
                ids.append(255)
            data.append(item["val"].value)
        blocks = numpy.asarray(ids, dtype=self._Blocks.bin_type)[blocks_before_palette]
        data = numpy.asarray(data, dtype=self._Data.bin_type)[blocks_before_palette]
        return blocks, data, storage

    def add_data(self, terrain=None, tile_entities=None, entities=None, subchunk=None):
        """Add terrain to chunk.

        terrain, tile_entities, entities: str: 4096 long string. Defaults to 'None'.
        subchunk: int: subchunk 'height'; generaly 0 to 15 number.
        """
        if type(subchunk) != int:
            raise TypeError("Bad subchunk type. Must be an int, got %s (%s)"%(type(subchunk), subchunk))
        if terrain:
            self.subchunks.append(subchunk)

            subchunk_version, terrain = ord(terrain[0]), terrain[1:]
            if subchunk_version in [0, 2, 3, 4, 5, 6, 7]:
                blocks, terrain = terrain[:4096], terrain[4096:]
                data, terrain = terrain[:2048], terrain[2048:]
                skyLight, terrain = terrain[:2048], terrain[2048:]
                blockLight, terrain = terrain[:2048], terrain[2048:]
                # 'Computing' data is needed before sending it to the data holders.
                self._Blocks.add_data(subchunk, numpy.fromstring(blocks, "uint8").astype(self._Blocks.bin_type))

                #             for k, v in ((self._Data, data), (self._SkyLight, skyLight), (self._BlockLight, blockLight)):
                #                 a = numpy.fromstring(v, k.bin_type)
                #                 a.shape = (16, 16, len(v) / 256)
                #                 k.add_data(subchunk, unpackNibbleArray(a).tostring())

                a = numpy.fromstring(data, "uint8")
                a.shape = (16, 16, len(data) / 256)
                self._Data.add_data(subchunk, numpy.fromstring(unpackNibbleArray(a).tostring(), "uint8").astype(self._Data.bin_type))

                if self.chunk_version == "\x03":
                    for k, v in ((self._SkyLight, skyLight), (self._BlockLight, blockLight)):
                        a = numpy.fromstring(v, "uint8")
                        a.shape = (16, 16, len(v) / 256)
                        k.add_data(subchunk,
                                   numpy.fromstring(unpackNibbleArray(a).tostring(), "uint8").astype(k.bin_type))
            elif subchunk_version == 1:
                blocks, data, terrain = self._read_block_storage(terrain)
                self._Blocks.add_data(subchunk, blocks)
                self._Data.add_data(subchunk, data)
            elif subchunk_version == 8:
                num_of_storages, terrain = ord(terrain[0]), terrain[1:]
                blocks, data, terrain = self._read_block_storage(terrain)
                self._Blocks.add_data(subchunk, blocks)
                self._Data.add_data(subchunk, data)
                if num_of_storages > 1:
                    extraBlocks, extraData, ignored_data = self._read_block_storage(terrain)
                    self._extra_blocks.add_data(subchunk, extraBlocks)
                    self._extra_blocks_data.add_data(subchunk, extraData)
                    # Only support for one layer of extra blocks is in place
            else:
                raise NotImplementedError("Not implemented this new type of world format yet")

            self.subchunks_versions[subchunk] = subchunk_version

#             if DEBUG_PE:
#                 write_dump("--- sub-chunk (%s, %s, %s) version: %s\n" % (self.chunkPosition[0], self.chunkPosition[1], subchunk, version))
#                 write_dump("--- sub-chunk (%s, %s, %s) blocks: %s\n    length: %s\n" % (self.chunkPosition[0], self.chunkPosition[1], subchunk, repr(blocks), len(blocks)))

        else:
            if subchunk == 0 and DEBUG_PE:
                write_dump("!!! No terrain for sub-chunk (%s, %s, %s)\n" % (self.chunkPosition[0], self.chunkPosition[1], subchunk))

        if tile_entities:
            if DEBUG_PE:
                write_dump(('/' * 80) + '\nParsing TileEntities in chunk %s,%s\n' % (self.chunkPosition[0], self.chunkPosition[1]))
            if DEBUG_PE == 2:
                write_dump("+ begin tile_entities raw data\n%s\n- end tile_entities raw data\n" % nbt.hexdump(tile_entities, length=16))
            for tile_entity in loadNBTCompoundList(tile_entities):
                self.TileEntities.insert(-1, tile_entity)
        if entities:
            mcedit_defs = self.world.defsIds.mcedit_defs
            defs_get = mcedit_defs.get
            ids_get = self.world.defsIds.mcedit_ids.get
            if DEBUG_PE:
                write_dump(('\\' * 80) + '\nParsing Entities in chunk %s,%s\n' % (self.chunkPosition[0], self.chunkPosition[1]))
            try:
                Entities = loadNBTCompoundList(entities)
            except Exception as exc:
                logger.error("The entities data for chunk %s:%s may be corrupted. The error is:\n%s" % (self.chunkPosition[0], self.chunkPosition[1], exc))
                Entities = nbt.TAG_List()

            # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
            # Whenever we save an entity, we need to make sure to swap back.
#             invertEntities = {v: k for k, v in entity.PocketEntity.entityList.items()}
            for ent in Entities:
                try:
                    v = ent["id"].value
                    if DEBUG_PE:
                        _v = int(v)
                    v = int(v) & 0xFF
                except Exception as e:
                    logger.warning("An error occured while getting entity ID:")
                    logger.warning(e)
                    logger.warning("Default 'Unknown' ID is used...")
                    v = 'Unknown'
                # !
#                 id = invertEntities.get(v, "Entity %s"%v)
                # Add the built one to the entities
#                 if id not in entity.PocketEntity.entityList.keys():
#                     logger.warning("Found unknown entity '%s'"%v)
#                     entity.PocketEntity.entityList[id] = v

                id = defs_get(ids_get(v, 'Unknown'),
                                     {'name': 'Unknown Entity %s' % v,
                                      'idStr': 'Unknown Entity %s' % v,
                                      'id': -1,
                                      'type': 'Unknown'}
                                     )['name']
                if DEBUG_PE:
                    ent_def = defs_get(ids_get(v, 'Unknown'),
                                     {'name': 'Unknown Entity %s' % v,
                                      'idStr': 'Unknown Entity %s' % v,
                                      'id': -1,
                                      'type': 'Unknown'}
                                     )
                    _tn = ent_def.get('type', 'Unknown')
                    _tv = mcedit_defs['entity_types'].get(_tn, 'Unknown')
                    write_dump("* Internal ID: {id}, raw ID: {_v}, filtered ID: {_fid}, filter: {_f1} ({_f2}), type name {_tn}, type value: {_tv}\n".format(
                                                    id=id,
                                                    _v=_v,
                                                    _fid= _v & 0xff,
                                                    _f1= _v & 0xff00,
                                                    _f2= _v - (_v & 0xff),
                                                    _tn=_tn,
                                                    _tv=_tv)
                                                )

                ent["id"] = nbt.TAG_String(id)

                self.Entities.insert(-1, ent)

    def savedData(self):
        """Unused, raises NotImplementedError()."""
        # Not used for PE 1+ worlds... May change :)
        raise NotImplementedError()

    def genFastLights(self):
        pass

    # -- Entities and TileEntities

    @property
    def Entities(self):
        return self._Entities

    @Entities.setter
    def Entities(self, Entities):
        """
        :param Entities: list
        :return:
        """
        self._Entities = Entities

    @property
    def TileEntities(self):
        return self._TileEntities

    @TileEntities.setter
    def TileEntities(self, TileEntities):
        """
        :param TileEntities: list
        :return:
        """
        self._TileEntities = TileEntities

    @property
    def TileTicks(self):
        return nbt.TAG_List()
