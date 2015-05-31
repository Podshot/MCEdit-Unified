import itertools
import time
from level import FakeChunk, MCLevel
import logging
from materials import pocketMaterials

import os

from mclevelbase import ChunkNotPresent, ChunkMalformed
import nbt
import numpy
import struct
from infiniteworld import ChunkedLevelMixin, SessionLockLost
from level import LightedChunk
from contextlib import contextmanager
from pymclevel import entity, BoundingBox, Entity, TileEntity

logger = logging.getLogger(__name__)

leveldb_available = True
try:
    import leveldb_mcpe
except ImportError, e:
    leveldb_available = False
    logger.info("Error while trying to import leveldb_mcpe, starting without PE support ({0})".format(e))

"""
TODO add these things:
Add player support.
Add a way of creating new levels
"""

# SELECT
# TODO Fix export

# NBT
# TODO make it not crash on startup

# CHUNK CONTROL
# TODO Fix up Create Chunks and Extract Chunks



# noinspection PyUnresolvedReferences
@contextmanager
def littleEndianNBT():
    """
    Pocket edition NBT files are encoded in little endian, instead of big endian.
    This sets all the required paramaters to read little endian NBT, and makes sure they get set back after usage.
    :return: None
    """

    # We need to override the function to access the hard-coded endianness.
    def override_write_string(string, buf):
        encoded = string.encode('utf-8')
        buf.write(struct.pack("<h%ds" % (len(encoded),), len(encoded), encoded))

    def reset_write_string(string, buf):
        encoded = string.encode('utf-8')
        buf.write(struct.pack(">h%ds" % (len(encoded),), len(encoded), encoded))

    def override_byte_array_write_value(self, buf):
        value_str = self.value.tostring()
        buf.write(struct.pack("<I%ds" % (len(value_str),), self.value.size, value_str))

    def reset_byte_array_write_value(self, buf):
        value_str = self.value.tostring()
        buf.write(struct.pack("<I%ds" % (len(value_str),), self.value.size, value_str))

    nbt.string_len_fmt = struct.Struct("<H")
    nbt.TAG_Byte.fmt = struct.Struct("<b")
    nbt.TAG_Short.fmt = struct.Struct("<h")
    nbt.TAG_Int.fmt = struct.Struct("<i")
    nbt.TAG_Long.fmt = struct.Struct("<q")
    nbt.TAG_Float.fmt = struct.Struct("<f")
    nbt.TAG_Double.fmt = struct.Struct("<d")
    nbt.TAG_Int_Array.dtype = numpy.dtype("<u4")
    nbt.TAG_Short_Array.dtype = numpy.dtype("<u2")
    nbt.write_string = override_write_string
    nbt.TAG_Byte_Array.write_value = override_byte_array_write_value
    yield
    nbt.string_len_fmt = struct.Struct(">H")
    nbt.TAG_Byte.fmt = struct.Struct(">b")
    nbt.TAG_Short.fmt = struct.Struct(">h")
    nbt.TAG_Int.fmt = struct.Struct(">i")
    nbt.TAG_Long.fmt = struct.Struct(">q")
    nbt.TAG_Float.fmt = struct.Struct(">f")
    nbt.TAG_Double.fmt = struct.Struct(">d")
    nbt.TAG_Int_Array.dtype = numpy.dtype(">u4")
    nbt.TAG_Short_Array.dtype = numpy.dtype(">u2")
    nbt.write_string = reset_write_string
    nbt.TAG_Byte_Array.write_value = reset_byte_array_write_value


def loadNBTCompoundList(data, littleEndian=True):
    """
    Loads a list of NBT Compound tags from a bunch of data.
    Uses sep to determine where the next Compound tag starts.
    :param data: str, the NBT to load from
    :param littleEndian: bool. Determines endianness
    :return: list of TAG_Compounds
    """

    def load(_data):
        sep = "\x00\x00\x00\x00\n"
        sep_data = _data.split(sep)
        compounds = []
        for d in sep_data:
            if len(d) != 0:
                if not d.startswith("\n"):
                    d = "\n" + d
                tag = (nbt.load(buf=(d + '\x00\x00\x00\x00')))
                compounds.append(tag)
        return compounds

    if littleEndian:
        with littleEndianNBT():
            return load(data)
    else:
        return load(data)


def TagProperty(tagName, tagType, default_or_func=None):
    """
    Copied from infiniteworld.py. Custom property object to handle NBT-tag properties.
    :param tagName: str, Name of the NBT-tag
    :param tagType: int, (nbt.TAG_TYPE) Type of the NBT-tag
    :param default_or_func: function or default value. If function, function should return the default.
    :return: property
    """
    def getter(self):
        if tagName not in self.root_tag:
            if hasattr(default_or_func, "__call__"):
                default = default_or_func(self)
            else:
                default = default_or_func

            self.root_tag[tagName] = tagType(default)
        return self.root_tag[tagName].value

    def setter(self, val):
        self.root_tag[tagName] = tagType(value=val)

    return property(getter, setter)


class PocketLeveldbDatabase(object):
    """
    Not to be confused with leveldb_mcpe.DB
    A PocketLeveldbDatabase is an interface around leveldb_mcpe.DB, providing various functions
    to load/write chunk data, and access the level.dat file.
    The leveldb_mcpe.DB object handles the actual leveldb database.
    To access the actual database, world_db() should be called.
    """
    holdDatabaseOpen = True
    _world_db = None

    @contextmanager
    def world_db(self):
        """
        Opens a leveldb and keeps it open until editing finished.
        :yield: DB
        """
        if PocketLeveldbDatabase.holdDatabaseOpen:
            if self._world_db is None:
                self._world_db = leveldb_mcpe.DB(self.options, os.path.join(str(self.path), 'db'))
            yield self._world_db
            pass
        else:
            db = leveldb_mcpe.DB(self.options, os.path.join(str(self.path), 'db'))
            yield db
            del db

    def __init__(self, path, create=False):
        """
        :param path: string, path to file
        :return: None
        """
        self.path = path

        if not os.path.exists(path):
            file(path, 'w').close()

        self.options = leveldb_mcpe.Options()
        self.writeOptions = leveldb_mcpe.WriteOptions()
        self.readOptions = leveldb_mcpe.ReadOptions()

        if create:
            self.options.create_if_missing = True  # The database will be created once needed first.
            return

        needsRepair = False
        try:
            with self.world_db() as db:
                it = db.NewIterator(self.readOptions)
                it.SeekToFirst()
                if not db.Get(self.readOptions, it.key()) == it.value():
                    needsRepair = True
                del it

        except RuntimeError, e:
            logger.error("Error while opening world database from %s (%s)" % path, e)
            needsRepair = True

        if needsRepair:
            logger.info("Trying to repair world %s", path)
            try:
                leveldb_mcpe.RepairWrapper(os.path.join(path, 'db'))
            except RuntimeError, e:
                logger.error("Error while repairing world %s %s" % path, e)

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

    def _readChunk(self, cx, cz, readOptions=None):
        """
        :param cx, cz: int Coordinates of the chunk
        :param readOptions: ReadOptions
        :return: None
        """
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

        logger.debug("CHUNK LOAD %s %s", cx, cz)
        return terrain, tile_entities, entities

    def saveChunk(self, chunk, batch=None, writeOptions=None):
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
                db.Put(key + "0", data[0], wop)
                if data[1] is not None:
                    db.Put(key + "1", data[1], wop)
                if data[2] is not None:
                    db.Put(key + "2", data[2], wop)
        else:
            batch.Put(key + "0", data[0])
            if data[1] is not None:
                batch.Put(key + "1", data[1])
            if data[2] is not None:
                batch.Put(key + "2", data[2])

    def loadChunk(self, cx, cz, world):
        """
        :param cx, cz: int Coordinates of the chunk
        :param world: PocketLeveldbWorld
        :return: PocketLeveldbChunk
        """
        data = self._readChunk(cx, cz)
        if data is None:
            raise ChunkNotPresent((cx, cz, self))

        chunk = PocketLeveldbChunk(cx, cz, world, data)
        return chunk

    _allChunks = None

    def deleteChunk(self, cx, cz, batch=None, writeOptions=None):
        if batch is None:
            with self.world_db() as db:
                key = struct.pack('<i', cx) + struct.pack('<i', cz) + "0"
                wop = self.writeOptions if writeOptions is None else writeOptions
                db.Delete(wop, key)
        else:
            key = struct.pack('<i', cx) + struct.pack('<i', cz) + "0"
            batch.Delete(key)

        logger.debug("DELETED CHUNK %s %s", cx, cz)

    def getAllChunks(self, readOptions=None):
        """
        Returns a list of all chunks that have terrain data in the database.
        Chunks with only Entities or TileEntities are ignored.
        :param readOptions: ReadOptions
        :return: list
        """
        with self.world_db() as db:
            allChunks = []
            rop = self.readOptions if readOptions is None else readOptions

            it = db.NewIterator(rop)
            it.SeekToFirst()
            while it.Valid():
                key = it.key()
                raw_x = key[0:4]
                raw_z = key[4:8]
                t = key[8]

                if t == "0":
                    cx, cz = struct.unpack('<i', raw_x), struct.unpack('<i', raw_z)
                    allChunks.append((cx[0], cz[0]))
                it.Next()
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

            it = db.NewIterator(rop)
            it.SeekToFirst()
            while it.Valid():
                key = it.key()
                if key == "~local_player":  # Singleplayer
                    allPlayers[key] = it.value()
                elif key.startswith('player_'):  # Multiplayer player
                    allPlayers[key] = it.value()
                it.Next()
            it.status()
            del it
            return allPlayers


class InvalidPocketLevelDBWorldException(Exception):
    pass


class PocketLeveldbWorld(ChunkedLevelMixin, MCLevel):
    Height = 128
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
    _players = {}
    _playerList = None

    @property
    def allChunks(self):
        """
        :return: list with all chunks in the world.
        """
        if self._allChunks is None:
            self._allChunks = self.worldFile.getAllChunks()
        return self._allChunks

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

    def __init__(self, filename=None, create=False, random_seed=None, last_played=None, readonly=False):
        """
        :param filename: path to the root dir of the level
        :return:
        """
        if not os.path.isdir(filename):
            filename = os.path.dirname(filename)
        self.filename = filename

        self.worldFile = PocketLeveldbDatabase(filename, create=create)
        self.readonly = readonly
        self.loadLevelDat(create, random_seed, last_played)

    def _createLevelDat(self, random_seed, last_played):
        """
        Creates a new level.dat root_tag, and puts it in self.root_tag.
        To write it to the disk, self.save() should be called.
        :param random_seed: long
        :param last_played: long
        :return: None
        """
        with littleEndianNBT():
            root_tag = nbt.TAG_Compound()
            root_tag["SpawnX"] = nbt.TAG_Int(0)
            root_tag["SpawnY"] = nbt.TAG_Int(2)
            root_tag["SpawnZ"] = nbt.TAG_Int(0)

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
            root_tag_buf = open(filename).read()
            magic, length, root_tag_buf = root_tag_buf[:4], root_tag_buf[4:8], root_tag_buf[8:]
            if nbt.TAG_Int.fmt.unpack(magic)[0] < 3:
                logger.info("Found an old level.dat file. Aborting world load")
                raise InvalidPocketLevelDBWorldException()  # TODO Maybe try convert/load old PE world?
            if len(root_tag_buf) != nbt.TAG_Int.fmt.unpack(length)[0]:
                print len(root_tag_buf), nbt.TAG_Int.fmt.unpack(length)[0]
                raise nbt.NBTFormatError()
            self.root_tag = nbt.load(buf=root_tag_buf)

        if create:
            self._createLevelDat(random_seed, last_played)
            return
        try:
            with littleEndianNBT():
                _loadLevelDat(os.path.join(self.worldFile.path, "level.dat"))
            return
        except nbt.NBTFormatError, e:
            logger.info("Failed to load level.dat, trying to load level.dat_old ({0})".format(e))
        except IOError, e:
            logger.info("Failed to load level.dat, trying to load level.dat_old ({0})".format(e))
        try:
            with littleEndianNBT():
                _loadLevelDat(os.path.join(self.worldFile.path, "level.dat_old"))
            return
        except nbt.NBTFormatError, e:
            logger.info("Failed to load level.dat_old, creating new level.dat ({0})".format(e))
        except IOError, e:
            logger.info("Failed to load level.dat_old, creating new level.dat ({0})".format(e))
        self._createLevelDat(random_seed, last_played)
        print self.root_tag['SpawnX']

    # --- NBT Tag variables ---

    SizeOnDisk = TagProperty('SizeOnDisk', nbt.TAG_Int, 0)
    RandomSeed = TagProperty('RandomSeed', nbt.TAG_Long, 0)

    # TODO PE worlds have a different day length, this has to be changed to that.
    Time = TagProperty('Time', nbt.TAG_Long, 0)
    LastPlayed = TagProperty('LastPlayed', nbt.TAG_Long, lambda self: long(time.time() * 1000))

    LevelName = TagProperty('LevelName', nbt.TAG_String, lambda self: self.defaultDisplayName)
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
        c = self._loadedChunks.get((cx, cz))
        if c is None:
            c = self.worldFile.loadChunk(cx, cz, self)
            self._loadedChunks[(cx, cz)] = c
        return c

    def unload(self):
        """
        Unload all chunks and close all open file-handlers.
        """
        self._loadedChunks.clear()
        self._allChunks = None
        self.worldFile.close()
        print 'test'
        path = os.path.join(self.worldFile.path, 'level.dat')
        print self.root_tag['SpawnX']
        with littleEndianNBT():
            rootTagData = self.root_tag.save(compressed=False)
            rootTagData = nbt.TAG_Int.fmt.pack(4) + nbt.TAG_Int.fmt.pack(len(rootTagData)) + rootTagData
            with open(path, 'w') as f:
                f.write(rootTagData)

    def close(self):
        """
        Unload all chunks and close all open file-handlers. Discard any unsaved data.
        """
        self.unload()
        try:
            pass  # Setup a way to close a work-folder?
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
        if len(self.allChunks) == 0:
            return BoundingBox((0, 0, 0), (0, 0, 0))

        allChunks = numpy.array(list(self.allChunks))
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
        self.saving = True
        batch = leveldb_mcpe.WriteBatch()
        dirtyChunkCount = 0
        for chunk in self._loadedChunks.itervalues():
            if chunk.dirty:
                dirtyChunkCount += 1
                self.worldFile.saveChunk(chunk, batch=batch)
                chunk.dirty = False
            yield

        with self.worldFile.world_db() as db:
            wop = self.worldFile.writeOptions
            db.Write(wop, batch)

        with littleEndianNBT():
            self.root_tag.save(os.path.join(self.worldFile.path, "level.dat"))
        self.saving = False
        logger.info(u"Saved {0} chunks to the database".format(dirtyChunkCount))

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
            self.allChunks.append((cx, cz))

        self._loadedChunks[(cx, cz)] = PocketLeveldbChunk(cx, cz, self, create=True)
        self._bounds = None

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
        x, y, z = map(lambda p: int(numpy.floor(p)), Entity.pos(entityTag))

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
        Retrieves a tile tick at given x, y, z coordinates
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
        dataTag = self.root_tag
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
            playerSpawnTag = self.root_tag
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
        if player == 'Player':
            player = '~local_player'
        _player = self._players.get(player)
        if _player is not None:
            return _player
        playerData = self.playerData[player]
        with littleEndianNBT():
            _player = nbt.load(buf=playerData)
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
        posList = nbt.TAG_List([nbt.TAG_Double(p) for p in (x, y - 1.75, z)])
        playerTag = self.getPlayerTag(player)

        playerTag["Pos"] = posList

    def getPlayerPosition(self, player="Player"):
        """
        Gets the players position
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: tuple int (x, y, z): Coordinates of the player.
        """
        playerTag = self.getPlayerTag(player)
        posList = playerTag["Pos"]
        x, y, z = map(lambda x: x.value, posList)
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

    def setPlayerAbilities(self, gametype, player="Player"):
        """
        This method is currently unimplemented. Research needs to be done if MCPE players have abilities.
        It should set the right abilities for given gametype.
        :param player: string of the name of the player. "Player" for SSP player, player_<client-id> for SMP player.
        :return: bool
        """
        # TODO implement this or remove it.
        return gametype, player

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



class PocketLeveldbChunk(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    _Entities = _TileEntities = nbt.TAG_List()
    dirty = False

    def __init__(self, cx, cz, world, data=None, create=False):
        """
        :param cx, cz int, int Coordinates of the chunk
        :param data List of 3 strings. (83200 bytes of terrain data, tile-entity data, entity data)
        :param world PocketLeveldbWorld, instance of the world the chunk belongs too
        """
        self.chunkPosition = (cx, cz)
        self.world = world

        if create:
            self.Blocks = numpy.zeros(32768, 'uint8')
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
                TileEntities = loadNBTCompoundList(data[1])
                self.TileEntities = nbt.TAG_List(TileEntities, list_type=nbt.TAG_COMPOUND)

            if data[2] is not None:
                Entities = loadNBTCompoundList(data[2])
                # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
                # Whenever we save an entity, we need to make sure to swap back.
                invertEntities = {v: k for k, v in entity.PocketEntity.entityList.items()}
                for ent in Entities:
                    ent["id"] = nbt.TAG_String(invertEntities[ent["id"].value])
                self.Entities = nbt.TAG_List(Entities, list_type=nbt.TAG_COMPOUND)

            self.Blocks, terrain = terrain[:32768], terrain[32768:]
            self.Data, terrain = terrain[:16384], terrain[16384:]
            self.SkyLight, terrain = terrain[:16384], terrain[16384:]
            self.BlockLight, terrain = terrain[:16384], terrain[16384:]
            self.DirtyColumns, terrain = terrain[:256], terrain[256:]

            # Unused at the moment. Might need a special editor? Maybe hooked up to biomes?
            self.GrassColors = terrain[:1024]

        self.unpackChunkData()
        self.shapeChunkData()

    def unpackChunkData(self):
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
        self.Blocks.shape = (chunkSize, chunkSize, self.world.Height)
        self.SkyLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.BlockLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.Data.shape = (chunkSize, chunkSize, self.world.Height)
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
            assert dataArray.shape[2] == self.world.Height

            data = numpy.array(dataArray).reshape(16, 16, self.world.Height / 2, 2)
            data[..., 1] <<= 4
            data[..., 1] |= data[..., 0]
            return numpy.array(data[:, :, :, 1])

        if self.dirty:
            # elements of DirtyColumns are bitfields. Each bit corresponds to a
            # 16-block segment of the column. We set all of the bits because
            # we only track modifications at the chunk level.
            self.DirtyColumns[:] = 255

        with littleEndianNBT():
            entityData = ""
            tileEntityData = ""

            for ent in self.TileEntities:
                tileEntityData += ent.save(compressed=False)

            for ent in self.Entities:
                v = ent["id"].value
                ent["id"] = nbt.TAG_Int(entity.PocketEntity.entityList[v])
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