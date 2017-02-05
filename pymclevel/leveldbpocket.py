import itertools
import time
from math import floor
from level import FakeChunk, MCLevel
import logging
from materials import pocketMaterials

import os

from mclevelbase import ChunkNotPresent, ChunkMalformed
import nbt
import numpy
import struct
from infiniteworld import ChunkedLevelMixin, SessionLockLost, AnvilChunkData
from level import LightedChunk
from contextlib import contextmanager
from pymclevel import entity, BoundingBox, Entity, TileEntity
import id_definitions

logger = logging.getLogger(__name__)

leveldb_available = True
leveldb_mcpe = None
try:
    import leveldb_mcpe
    leveldb_mcpe.Options()
except Exception as e:
    leveldb_available = False
    logger.info("Error while trying to import leveldb_mcpe, starting without PE support ({0})".format(e))
    leveldb_mcpe = None

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

if DEBUG_PE:
    open(dump_fName, 'w').close()


# =====================================================================
# loadNBTCompoundList
#
# In the old version, the raw data is split in several parts then sent
# to the nNBT support for effective loading.
# This is not realy safe, since the split is made on a string object.
# It leads to malformed NBT data, and prevent some chunks to be loaded.
#
# The new method loads the raw data, and returns the NBT data
# encapsulated in a Puthon List object if the NBT is a compound object,
# or as is if it is a NBT list.
# This second method suppresses some of the missing chunks bugs.
def loadNBTCompoundList_old(data, littleEndian=True):
    """
    Loads a list of NBT Compound tags from a bunch of data.
    Uses sep to determine where the next Compound tag starts.
    :param data: str, the NBT to load from
    :param littleEndian: bool. Determines endianness
    :return: list of TAG_Compounds
    """
#     if type(data) is unicode:
#         data = str(data)

    if DEBUG_PE:
        global longest_complist_len
        global longest_complist
        global shortest_complist_len
        global shortest_complist
    
        open(dump_fName, 'a').write(("=" * 80) + "\n")

    def load(_data):
        if DEBUG_PE:
            global longest_complist_len
            global longest_complist
            global shortest_complist_len
            global shortest_complist

        sep = "\x00\x00\x00\x00\n"
        sep_data = _data.split(sep)
        compounds = []
        for d in sep_data:
            if len(d) != 0:
                if not d.startswith("\n"):
                    d = "\n" + d
                if DEBUG_PE:
                    if len(d) > longest_complist_len:
                        longest_complist = repr(d)
                        longest_complist_len = len(d)
                    if len(d) < shortest_complist_len:
                        shortest_complist = repr(d)
                        shortest_complist_len = len(d)
                tag = (nbt.load(buf=(d + '\x00\x00\x00\x00')))
                compounds.append(tag)

        if DEBUG_PE:
            try:
                open(dump_fName, 'a').write("**********\nLongest data length: %s\nData:\n%s\n"%(longest_complist_len, longest_complist))
                open(dump_fName, 'a').write("**********\nShortest data length: %s\nData:\n%s\n"%(shortest_complist_len, shortest_complist))
            except Exception, e:
                print "Could not write debug info:", e

        return compounds

    if littleEndian:
        with nbt.littleEndianNBT():
            return load(data)
    else:
        return load(data)

def loadNBTCompoundList_new(data, littleEndian=True):
    """
    Loads a list of NBT Compound tags from a bunch of data.
    Uses sep to determine where the next Compound tag starts.
    :param data: str, the NBT to load from
    :param littleEndian: bool. Determines endianness
    :return: list of TAG_Compounds
    """
    def load(_data):
        if len(_data):
            try:
                __data = nbt.load(buf=_data)
            except Exception, e:
                msg1 = "PE support could not read compound list data:"
                msg2 = "Data dump:"
                msg3 = "Data length: %s"
                logger.error(msg1)
                logger.error(e)
                if len(_data) > 80:
                    logger.error("Partial data dump:")
                    logger.error("%s [...] %s", repr(_data[:40]), repr(_data[-40:]))
                else:
                    logger.error(msg2)
                    logger.error(repr(_data))
                logger.error(msg3, len(data))
                if DEBUG_PE:
                    try:
                        dump_line = len(open(dump_fName).read().splitlines()) + 1
                        dump_msg = "**********\n{m1}\n{e}\n{m2}\n{d}\n{m3} {l}".format(m1=msg1,
                                   e=e, m2=msg2, d=repr(_data), m3=msg3, l=len(data))
                        msg_len = len(dump_msg.splitlines())
                        open(dump_fName, 'a').write(dump_msg)
                        logger.warn("Error info and data dumped to %s at line %s (%s lines long)", dump_fName, dump_line, msg_len)
                    except Exception, _e:
                        logger.error("Could not dump PE debug info:")
                        logger.error(_e)
                raise e
            if __data.isCompound():
                return [__data]
            return __data
        else:
            return []

    if littleEndian:
        with nbt.littleEndianNBT():
            return load(data)
    else:
        return load(data)

if __builtins__.get('mcenf_loadNBTCompoundList', False):
    loadNBTCompoundList = loadNBTCompoundList_new
else:
    loadNBTCompoundList = loadNBTCompoundList_old

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


class InvalidPocketLevelDBWorldException(Exception):
    pass


# =====================================================================
# Old (almost) working code for PE 0.9/less than 1.0.0
class PocketLeveldbDatabase_old(object):
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
                it.status()
                del it

        except RuntimeError as err:
            logger.error("Error while opening world database from %s (%s)"%(path, err))
            needsRepair = True

        if needsRepair:
            logger.info("Trying to repair world %s"%path)
            try:
                leveldb_mcpe.RepairWrapper(os.path.join(path, 'db'))
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

        logger.debug("CHUNK LOAD %s %s"%(cx, cz))
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

        logger.debug("DELETED CHUNK %s %s"%(cx, cz))

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

                if len(key) != 9:  # Bad. Hardcode since nether has length 13. Someone go fix nether.
                    it.Next()
                    continue
                    
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

    def savePlayer(self, player, playerData, batch=None, writeOptions=None):
        if writeOptions is None:
            writeOptions = self.writeOptions
        if batch is None:
            with self.world_db() as db:
                db.Put(writeOptions, player, playerData)
        else:
            batch.Put(player, playerData)


class PocketLeveldbWorld_old(ChunkedLevelMixin, MCLevel):
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
    playerTagCache = {}
    _playerList = None

    entityClass = entity.PocketEntity

    @property
    def LevelName(self):
        if "LevelName" not in self.root_tag:
            with open(os.path.join(self.worldFile.path, "levelname.txt"), 'r') as f:
                name = f.read()
            if name is None:
                name = os.path.basename(self.worldFile.path)
            self.root_tag["LevelName"] = name
        return self.root_tag["LevelName"].value

    @LevelName.setter
    def LevelName(self, name):
        self.root_tag["LevelName"] = nbt.TAG_String(value=name)
        with open(os.path.join(self.worldFile.path, "levelname.txt"), 'w') as f:
            f.write(name)

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
        with nbt.littleEndianNBT():
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
            root_tag_buf = open(filename, 'rb').read()
            magic, length, root_tag_buf = root_tag_buf[:4], root_tag_buf[4:8], root_tag_buf[8:]
            if struct.Struct('<i').unpack(magic)[0] < 3:
                logger.info("Found an old level.dat file. Aborting world load")
                raise InvalidPocketLevelDBWorldException()  # Maybe try convert/load old PE world?
            if len(root_tag_buf) != struct.Struct('<i').unpack(length)[0]:
                raise nbt.NBTFormatError()
            self.root_tag = nbt.load(buf=root_tag_buf)

        self.__gameVersion = 'PE'
        id_definitions.ids_loader('PE')
        if create:
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
            open(dump_fName, 'a').write("*** Getting chunk %s,%s\n"%(cx, cz))
        c = self._loadedChunks.get((cx, cz))
        if c is None:
            if DEBUG_PE:
                open(dump_fName, 'a').write("    Not loaded, loading\n")
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
        if DEBUG_PE:
            print "*** saveInPlaceGen"
            open(dump_fName ,'a').write("*** saveInPlaceGen\n")
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
                playerData = self.playerTagCache[p]
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
            rootTagData = self.root_tag.save(compressed=False)
            rootTagData = struct.Struct('<i').pack(4) + struct.Struct('<i').pack(len(rootTagData)) + rootTagData
            with open(path, 'w') as f:
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
            self.allChunks.append((cx, cz))

        self._loadedChunks[(cx, cz)] = PocketLeveldbChunk(cx, cz, self, create=True)
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


class PocketLeveldbChunk_old(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    # _Entities = _TileEntities = nbt.TAG_List()
    _Entities = nbt.TAG_List()
    _TileEntities = nbt.TAG_List()
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
                    open(dump_fName, 'a').write(('/' * 80) + '\nParsing TileEntities in chunk %s,%s\n'%(cx, cz))
                TileEntities = loadNBTCompoundList(data[1])
                self.TileEntities = nbt.TAG_List(TileEntities, list_type=nbt.TAG_COMPOUND)

            if data[2] is not None:
                if DEBUG_PE:
                    open(dump_fName, 'a').write(('\\' * 80) + '\nParsing Entities in chunk %s,%s\n'%(cx, cz))
                Entities = loadNBTCompoundList(data[2])
                # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
                # Whenever we save an entity, we need to make sure to swap back.
                invertEntities = {v: k for k, v in entity.PocketEntity.entityList.items()}
                for ent in Entities:
                    # Get the string id, or a build one
                    # ! For PE debugging
                    try:
                        v = ent["id"].value
                    except Exception, e:
                        logger.warning("An error occured while getting entity ID:")
                        logger.warning(e)
                        logger.warning("Default 'Unknown' ID is used...")
                        v = 'Unknown'
                    # !
                    id = invertEntities.get(v, "Entity %s"%v)
                    # Add the built one to the entities
                    if id not in entity.PocketEntity.entityList.keys():
                        logger.warning("Found unknown entity '%s'"%v)
                        entity.PocketEntity.entityList[id] = v
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

        with nbt.littleEndianNBT():
            entityData = ""
            tileEntityData = ""

            for ent in self.TileEntities:
                tileEntityData += ent.save(compressed=False)

            for ent in self.Entities:
                v = ent["id"].value
#                 ent["id"] = nbt.TAG_Int(entity.PocketEntity.entityList[v])
                id = entity.PocketEntity.getNumId(v)
#                 print id
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

# =====================================================================
# New code for PE 1.0.0
class PocketLeveldbDatabase_new(object):
    """
    Not to be confused with leveldb_mcpe.DB
    A PocketLeveldbDatabase is an interface around leveldb_mcpe.DB, providing various functions
    to load/write chunk data, and access the level.dat file.
    The leveldb_mcpe.DB object handles the actual leveldb database.
    To access the actual database, world_db() should be called.
    """
    holdDatabaseOpen = True
    _world_db = None
    world_version = None # to be set to 'pre1.0' or '1.plus'

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

    def __init__(self, path, create=False, world_version=None):
        """
        :param path: string, path to file
        :return: None
        """
        if not world_version:
            raise TypeError("Wrong world version sent: %s"%world_version)
        self.world_version = world_version
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
                it.status()
                del it

        except RuntimeError as err:
            logger.error("Error while opening world database from %s (%s)"%(path, err))
            needsRepair = True

        if needsRepair:
            logger.info("Trying to repair world %s"%path)
            try:
                leveldb_mcpe.RepairWrapper(os.path.join(path, 'db'))
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

    def _readChunk_old(self, cx, cz, readOptions=None):
        # Not used...
        """
        :param cx, cz: int Coordinates of the chunk
        :param readOptions: ReadOptions
        :return: None
        """
        if self.world_version == 'pre1.0' or True:
            key = struct.pack('<i', cx) + struct.pack('<i', cz)
        else:
            key = struct.pack('<i', cx) + struct.pack('<i', cz) + "\x2f" + "\x00"

        with self.world_db() as db:
            rop = self.readOptions if readOptions is None else readOptions

            # In pre 1.0 PE, we add 'numbers' to the key, but not in 1.plus
            if self.world_version == 'pre1.0':
                tr = '0'
                te = '1'
                en = '2'
            else:
                tr = '\x2f\x00'
                te = '\x31\x00'
                en = '\x32\x00'

            # Only way to see if value exists is by failing db.Get()
            try:
                terrain = db.Get(rop, key + tr)
#                 print type(terrain)
            except RuntimeError:
                return None

            try:
                tile_entities = db.Get(rop, key + te)
            except RuntimeError:
                tile_entities = None

            try:
                entities = db.Get(rop, key + en)
            except RuntimeError:
                entities = None

#         print 'terrain is None', terrain is None
#         print "self.world_version == 'pre1.0' and len(terrain) != 83200", self.world_version == 'pre1.0' and len(terrain) != 83200
#         print "self.world_version == '1.plus' and len(terrain) != 10241", self.world_version == '1.plus' and len(terrain) != 10241
#         print "(self.world_version == 'pre1.0' and len(terrain) != 83200) or (self.world_version == '1.plus' and len(terrain) != 10241)", (self.world_version == 'pre1.0' and len(terrain) != 83200) or (self.world_version == '1.plus' and len(terrain) != 10241)
#         print "terrain is None or ((self.world_version == 'pre1.0' and len(terrain) != 83200) or (self.world_version == '1.plus' and len(terrain) != 10241))", terrain is None or ((self.world_version == 'pre1.0' and len(terrain) != 83200) or (self.world_version == '1.plus' and len(terrain) != 10241))

        if terrain is None or ((self.world_version == 'pre1.0' and len(terrain) != 83200) or (self.world_version == '1.plus' and len(terrain) != 10241)):
            raise ChunkMalformed(str(len(terrain)))

        logger.debug("CHUNK LOAD %s %s"%(cx, cz))
        return terrain, tile_entities, entities

    def _readChunk_pre1_0(self, cx, cz, readOptions=None):
        # Put that in the chunk classes
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

#         logger.debug("CHUNK LOAD %s %s"%(cx, cz))
        return terrain, tile_entities, entities

    def _readChunk_1plus(self, cx, cz, y, readOptions=None):
        # Put that in the chunk classes
        key = struct.pack('<i', cx) + struct.pack('<i', cz)
        with self.world_db() as db:
#             print "--- Loading subchunk %s in chunk %s %s"%(y, cx, cz)
            rop = self.readOptions if readOptions is None else readOptions
            c = chr(y)
#             print '"\x2f" + c', "\x2f" + repr(c).strip("'")

            try:
                terrain = db.Get(rop, key + "\x2f" + c)
            except RuntimeError:
                return None

            try:
                tile_entities = db.Get(rop, key + "\x31" + c)
            except RuntimeError:
                tile_entities = None

            try:
                entities = db.Get(rop, key + "\x32" + c)
            except RuntimeError:
                entities = None

        return terrain, tile_entities, entities

    def _readChunk(self, cx, cz, world, readOptions=None):
        # Put this in the chunks classes
        """
        :param cx, cz: int Coordinates of the chunk
        :param readOptions: ReadOptions
        :return: chunk data in a tuple: (terrain, tile_entities, entities)
        """
        if self.world_version == 'pre1.0':
            data = self._readChunk_pre1_0(cx, cz, readOptions)
            if data is None:
                raise ChunkNotPresent((cx, cz, self))
            PocketLeveldbChunk
            chunk = PocketLeveldbChunkPre1(cx, cz, world, data, world_version=self.world_version)
        else:
            # Iterate through the subchunks to rebuild the whole data
            chunk = PocketLeveldbChunk1Plus(cx, cz, world, world_version=self.world_version, create=True)
            for i in range(16):
                r = self._readChunk_1plus(cx, cz, i, readOptions)
                if type(r) == tuple:
                    tr, te, en = r
#                     print 'etetetetete'
                    terrain = tr
                    tile_entities = te
                    entities  = en
                    chunk.add_data(terrain=terrain, tile_entities=tile_entities, entities=entities, subchunk=i)
        logger.debug("CHUNK LOAD %s %s"%(cx, cz))
        return chunk

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

    def loadChunk(self, cx, cz, world):
        """
        :param cx, cz: int Coordinates of the chunk
        :param world: PocketLeveldbWorld
        :return: PocketLeveldbChunk
        """
#         print 'DB load chunk', cx, cz
#         data = self._readChunk(cx, cz)
#         if data is None:
#             raise ChunkNotPresent((cx, cz, self))
# 
#         chunk = PocketLeveldbChunk(cx, cz, world, data, world_version=self.world_version)

        chunk = self._readChunk(cx, cz, world)
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

        logger.debug("DELETED CHUNK %s %s"%(cx, cz))

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

                # This version check may be useless...
                if self.world_version == 'pre1.0':
                    if len(key) != 9:  # Bad. Hardcode since nether has length 13. Someone go fix nether.
                        it.Next()
                        continue
                else:
                    if len(key) < 9:  # Bad. Hardcode since nether has length 13. Someone go fix nether.
                        it.Next()
                        continue

                raw_x = key[0:4]
                raw_z = key[4:8]
                if self.world_version == 'pre1.0':
                    t = key[8]
                else:
                    t = ord(key[8])

                if (self.world_version == 'pre1.0' and t == "0") or (self.world_version == '1.plus' and t == 47):
                    cx, cz = struct.unpack('<i', raw_x), struct.unpack('<i', raw_z)
                    allChunks.append((cx[0], cz[0]))
                it.Next()
            if self.world_version == 'pre1.0':
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
            if self.world_version == 'pre1.0':
                it.status()
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


class PocketLeveldbWorld_new(ChunkedLevelMixin, MCLevel):
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
    playerTagCache = {}
    _playerList = None

    entityClass = entity.PocketEntity

    world_version = None # to be set to 'pre1.0' or '1.plus'
    gameVersion = 'PE'

    @property
    def LevelName(self):
        if "LevelName" not in self.root_tag:
            with open(os.path.join(self.worldFile.path, "levelname.txt"), 'r') as f:
                name = f.read()
            if name is None:
                name = os.path.basename(self.worldFile.path)
            self.root_tag["LevelName"] = name
        return self.root_tag["LevelName"].value

    @LevelName.setter
    def LevelName(self, name):
        self.root_tag["LevelName"] = nbt.TAG_String(value=name)
        with open(os.path.join(self.worldFile.path, "levelname.txt"), 'w') as f:
            f.write(name)

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

    def __init__(self, filename=None, create=False, random_seed=None, last_played=None, readonly=False):
        """
        :param filename: path to the root dir of the level
        :return:
        """
        if not os.path.isdir(filename):
            filename = os.path.dirname(filename)

        # Can we rely on this to know which version of PE was used to create the world?
        if open(os.path.join(filename, 'level.dat')).read(1) == '\x05':
            self.world_version = '1.plus'
        else:
            self.world_version = 'pre1.0'

#         print '**** world_version', self.world_version

        self.filename = filename
        self.worldFile = PocketLeveldbDatabase(filename, create=create, world_version=self.world_version)
        self.world_version = self.worldFile.world_version
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
        with nbt.littleEndianNBT():
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
            root_tag_buf = open(filename, 'rb').read()
            magic, length, root_tag_buf = root_tag_buf[:4], root_tag_buf[4:8], root_tag_buf[8:]
            if struct.Struct('<i').unpack(magic)[0] < 3:
                logger.info("Found an old level.dat file. Aborting world load")
                raise InvalidPocketLevelDBWorldException()  # Maybe try convert/load old PE world?
            if len(root_tag_buf) != struct.Struct('<i').unpack(length)[0]:
                raise nbt.NBTFormatError()
            self.root_tag = nbt.load(buf=root_tag_buf)

        self.__gameVersion = 'PE'
        id_definitions.ids_loader('PE')
        if create:
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
            open(dump_fName, 'a').write("*** Getting chunk %s,%s\n"%(cx, cz))
        c = self._loadedChunks.get((cx, cz))
        if c is None:
            if DEBUG_PE:
                open(dump_fName, 'a').write("    Not loaded, loading\n")
#             print "PE world loading chunk", cx, cz
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
        if DEBUG_PE:
#             print "*** saveInPlaceGen"
            open(dump_fName ,'a').write("*** saveInPlaceGen\n")
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
                playerData = self.playerTagCache[p]
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
            rootTagData = self.root_tag.save(compressed=False)
            rootTagData = struct.Struct('<i').pack(4) + struct.Struct('<i').pack(len(rootTagData)) + rootTagData
            with open(path, 'w') as f:
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
            self.allChunks.append((cx, cz))

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


class PocketLeveldbChunk_new(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    # _Entities = _TileEntities = nbt.TAG_List()
    _Entities = nbt.TAG_List()
    _TileEntities = nbt.TAG_List()
    dirty = False

    def __init__(self, cx, cz, world, data=None, create=False, world_version=None):
        """
        :param cx, cz int, int Coordinates of the chunk
        :param data List of 3 strings. (83200 bytes of terrain data, tile-entity data, entity data)
        :param world PocketLeveldbWorld, instance of the world the chunk belongs too
        """
        if not world_version:
            raise TypeError("Wrong world version sent: %s"%world_version)
        self.world_version = world_version
#         print 'chunk world version', self.world_version
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
#                 print 'loading tile entities in chunk', cx, cz
                if DEBUG_PE:
                    open(dump_fName, 'a').write(('/' * 80) + '\nParsing TileEntities in chunk %s,%s\n'%(cx, cz))
                TileEntities = loadNBTCompoundList(data[1])
                self.TileEntities = nbt.TAG_List(TileEntities, list_type=nbt.TAG_COMPOUND)

            if data[2] is not None:
#                 print 'loading entities in chunk', cx, cz
                if DEBUG_PE:
                    open(dump_fName, 'a').write(('\\' * 80) + '\nParsing Entities in chunk %s,%s\n'%(cx, cz))
                Entities = loadNBTCompoundList(data[2])
                # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
                # Whenever we save an entity, we need to make sure to swap back.
                invertEntities = {v: k for k, v in entity.PocketEntity.entityList.items()}
                for ent in Entities:
                    # Get the string id, or a build one
                    # ! For PE debugging
                    try:
                        v = ent["id"].value
                    except Exception, e:
                        logger.warning("An error occured while getting entity ID:")
                        logger.warning(e)
                        logger.warning("Default 'Unknown' ID is used...")
                        v = 'Unknown'
                    # !
                    id = invertEntities.get(v, "Entity %s"%v)
                    # Add the built one to the entities
                    if id not in entity.PocketEntity.entityList.keys():
                        logger.warning("Found unknown entity '%s'"%v)
                        entity.PocketEntity.entityList[id] = v
                    ent["id"] = nbt.TAG_String(id)
                self.Entities = nbt.TAG_List(Entities, list_type=nbt.TAG_COMPOUND)

            if self.world_version == 'pre1.0':
                self.Blocks, terrain = terrain[:32768], terrain[32768:]
                self.Data, terrain = terrain[:16384], terrain[16384:]
                self.SkyLight, terrain = terrain[:16384], terrain[16384:]
                self.BlockLight, terrain = terrain[:16384], terrain[16384:]
                self.DirtyColumns, terrain = terrain[:256], terrain[256:]
    
                # Unused at the moment. Might need a special editor? Maybe hooked up to biomes?
                self.GrassColors = terrain[:1024]
            else:
                self.version, terrain = terrain[:1], terrain[1:]
                self.Blocks, terrain = terrain[:4096], terrain[4096:]
                self.Data, terrain = terrain[:2048], terrain[2048:]
                self.SkyLight, terrain = terrain[:2048], terrain[2048:]
                self.BlockLight, terrain = terrain[:2048], terrain[2048:]

        self._unpackChunkData()
        self.shapeChunkData()

    def _unpackChunkData(self):
        """
        Unpacks the terrain data to match mcedit's formatting.
        """
        for key in ('SkyLight', 'BlockLight', 'Data'):
#             print key
            dataArray = getattr(self, key)
#             print 'dataArray.shape', dataArray.shape
            if self.world_version == 'pre1.0':
                dataArray.shape = (16, 16, 64)
            else:
                if len(dataArray.data):
                    dataArray.shape = (16, 16, 8)
                else:
                    dataArray.shape = (0, 0, 0)
#             print 'dataArray.shape', dataArray.shape
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
        if self.world_version == 'pre1.0':
            blocksHeight = worldHeight = self.world.Height
        else:
            blocksHeight = 16
            worldHeight = 16
#         print 'self.Blocks.shape', self.Blocks.shape, len(self.Blocks.data)
#         print 'self.SkyLight.shape', self.SkyLight.shape, len(self.SkyLight.data)
#         print 'self.BlockLight.shape', self.BlockLight.shape, len(self.BlockLight.data)
#         print 'self.Data.shape', self.Data.shape, len(self.Data.data)
        if len(self.Blocks.data):
            self.Blocks.shape = (chunkSize, chunkSize, blocksHeight)
#         print 1
        if len(self.SkyLight.data):
            self.SkyLight.shape = (chunkSize, chunkSize, worldHeight)
#         print 2
        if len(self.BlockLight.data):
            self.BlockLight.shape = (chunkSize, chunkSize, worldHeight)
#         print 3
        if len(self.Data.data):
            self.Data.shape = (chunkSize, chunkSize, worldHeight)
#         print 4
        if self.world_version == 'pre1.0':
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

        with nbt.littleEndianNBT():
            entityData = ""
            tileEntityData = ""

            for ent in self.TileEntities:
                tileEntityData += ent.save(compressed=False)

            for ent in self.Entities:
                v = ent["id"].value
#                 ent["id"] = nbt.TAG_Int(entity.PocketEntity.entityList[v])
                id = entity.PocketEntity.getNumId(v)
#                 print id
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

class PocketLeveldbChunkPre1(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    # _Entities = _TileEntities = nbt.TAG_List()
    _Entities = nbt.TAG_List()
    _TileEntities = nbt.TAG_List()
    dirty = False

    def __init__(self, cx, cz, world, data=None, create=False, world_version=None):
        """
        :param cx, cz int, int Coordinates of the chunk
        :param data List of 3 strings. (83200 bytes of terrain data, tile-entity data, entity data)
        :param world PocketLeveldbWorld, instance of the world the chunk belongs too
        """
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
                    open(dump_fName, 'a').write(('/' * 80) + '\nParsing TileEntities in chunk %s,%s\n'%(cx, cz))
                TileEntities = loadNBTCompoundList(data[1])
                self.TileEntities = nbt.TAG_List(TileEntities, list_type=nbt.TAG_COMPOUND)

            if data[2] is not None:
                if DEBUG_PE:
                    open(dump_fName, 'a').write(('\\' * 80) + '\nParsing Entities in chunk %s,%s\n'%(cx, cz))
                Entities = loadNBTCompoundList(data[2])
                # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
                # Whenever we save an entity, we need to make sure to swap back.
                invertEntities = {v: k for k, v in entity.PocketEntity.entityList.items()}
                for ent in Entities:
                    # Get the string id, or a build one
                    # ! For PE debugging
                    try:
                        v = ent["id"].value
                    except Exception, e:
                        logger.warning("An error occured while getting entity ID:")
                        logger.warning(e)
                        logger.warning("Default 'Unknown' ID is used...")
                        v = 'Unknown'
                    # !
                    id = invertEntities.get(v, "Entity %s"%v)
                    # Add the built one to the entities
                    if id not in entity.PocketEntity.entityList.keys():
                        logger.warning("Found unknown entity '%s'"%v)
                        entity.PocketEntity.entityList[id] = v
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

        with nbt.littleEndianNBT():
            entityData = ""
            tileEntityData = ""

            for ent in self.TileEntities:
                tileEntityData += ent.save(compressed=False)

            for ent in self.Entities:
                v = ent["id"].value
#                 ent["id"] = nbt.TAG_Int(entity.PocketEntity.entityList[v])
                id = entity.PocketEntity.getNumId(v)
#                 print id
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

class PE1PlusDataContainer:
    def __init__(self, subdata_length, bin_type, name='none'):
        # subdata_length: int: the length for the underlying numpy objects
        # bin_type: str: the binary data type, like uint8
        self.name = name
        self.subdata_length = subdata_length
        self.bin_type = bin_type
        # the first two argument for the shape always are 16
        self.shape = (16, 16, subdata_length / (16 * 16))
        self.subchunks = [] # Store here the valid subchunks as ints
        self.binary_data = [None] * 16 # Has to be a numpy arrays. This list is indexed using the subchunks content.

    def __repr__(self):
        return "PE1PlusDataContainer { subdata_length: %s, bin_type: %s, shape: %s, subchunks: %s }"%(self.subdata_length, self.bin_type, self.shape, self.subchunks)

    def __getitem__(self, x, z, y):
#         if y is None:
#             data = ''
#             for i in range(16):
#                 if i in 
#         else:
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
        # y: int: the subchunk to add data to
        # data: str: data to be added. Must be 4096 bytes long.
        # Does not raise an error if the subchunk already has data.
        # The old data is overriden.
        if len(data) != self.subdata_length:
            raise "Data does not match the required %s bytes length: %s bytes"%(self.subdata_length, len(data))
        self.binary_data[y] = numpy.fromstring(data, self.bin_type)
#         print self.name, self.shape, self.binary_data[y].shape, self.bin_type
        self.binary_data[y].shape = self.shape

class PocketLeveldbChunk1Plus(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    # _Entities = _TileEntities = nbt.TAG_List()
    _Entities = nbt.TAG_List()
    _TileEntities = nbt.TAG_List()
    dirty = False

    def __init__(self, cx, cz, world, data=None, create=False, world_version=None):
        """
        :param cx, cz int, int Coordinates of the chunk
        :param data List of 3 strings. (83200 bytes of terrain data, tile-entity data, entity data)
        :param world PocketLeveldbWorld, instance of the world the chunk belongs too
        """
        if not world_version:
            raise TypeError("Wrong world version sent: %s"%world_version)
        self.world_version = world_version
#         print 'chunk world version', self.world_version
        self.chunkPosition = (cx, cz)
        self.world = world

        if create:
            self.Blocks = PE1PlusDataContainer(4096, 'uint8', name='Blocks')
            self.Data = PE1PlusDataContainer(2048, 'uint8', name='Data')
            self.SkyLight = PE1PlusDataContainer(2048, 'uint8', name='SkyLight')
            self.BlockLight = PE1PlusDataContainer(2048, 'uint8', name='BlockLight')
            self.DirtyColumns = PE1PlusDataContainer(2048, 'uint8', name='DirtyColumns')
            # Is this one relevant?
            self.GrassColors = PE1PlusDataContainer(1024, 'uint8', name='GrassColor')

            self.TileEntities = nbt.TAG_List(list_type=nbt.TAG_COMPOUND)
            self.Entities = nbt.TAG_List(list_type=nbt.TAG_COMPOUND)

#         else:
#             terrain = numpy.fromstring(data[0], dtype='uint8')
#             if data[1] is not None:
# #                 print 'loading tile entities in chunk', cx, cz
#                 if DEBUG_PE:
#                     open(dump_fName, 'a').write(('/' * 80) + '\nParsing TileEntities in chunk %s,%s\n'%(cx, cz))
#                 TileEntities = loadNBTCompoundList(data[1])
#                 self.TileEntities = nbt.TAG_List(TileEntities, list_type=nbt.TAG_COMPOUND)
# 
#             if data[2] is not None:
# #                 print 'loading entities in chunk', cx, cz
#                 if DEBUG_PE:
#                     open(dump_fName, 'a').write(('\\' * 80) + '\nParsing Entities in chunk %s,%s\n'%(cx, cz))
#                 Entities = loadNBTCompoundList(data[2])
#                 # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
#                 # Whenever we save an entity, we need to make sure to swap back.
#                 invertEntities = {v: k for k, v in entity.PocketEntity.entityList.items()}
#                 for ent in Entities:
#                     # Get the string id, or a build one
#                     # ! For PE debugging
#                     try:
#                         v = ent["id"].value
#                     except Exception, e:
#                         logger.warning("An error occured while getting entity ID:")
#                         logger.warning(e)
#                         logger.warning("Default 'Unknown' ID is used...")
#                         v = 'Unknown'
#                     # !
#                     id = invertEntities.get(v, "Entity %s"%v)
#                     # Add the built one to the entities
#                     if id not in entity.PocketEntity.entityList.keys():
#                         logger.warning("Found unknown entity '%s'"%v)
#                         entity.PocketEntity.entityList[id] = v
#                     ent["id"] = nbt.TAG_String(id)
#                 self.Entities = nbt.TAG_List(Entities, list_type=nbt.TAG_COMPOUND)

#             if self.world_version == 'pre1.0':
#                 self.Blocks, terrain = terrain[:32768], terrain[32768:]
#                 self.Data, terrain = terrain[:16384], terrain[16384:]
#                 self.SkyLight, terrain = terrain[:16384], terrain[16384:]
#                 self.BlockLight, terrain = terrain[:16384], terrain[16384:]
#                 self.DirtyColumns, terrain = terrain[:256], terrain[256:]
#     
#                 # Unused at the moment. Might need a special editor? Maybe hooked up to biomes?
#                 self.GrassColors = terrain[:1024]
#             else:
#                 self.version, terrain = terrain[:1], terrain[1:]
#                 self.Blocks, terrain = terrain[:4096], terrain[4096:]
#                 self.Data, terrain = terrain[:2048], terrain[2048:]
#                 self.SkyLight, terrain = terrain[:2048], terrain[2048:]
#                 self.BlockLight, terrain = terrain[:2048], terrain[2048:]

#         self._unpackChunkData()
#         self.shapeChunkData()

    def add_data(self, terrain=None, tile_entities=None, entities=None, subchunk=None):
        if type(subchunk) != int:
            raise TypeError("Bad subchunk type. Must be an int, got %s (%s)"%(type(subchunk), subchunk))
        if terrain:
            self.version, terrain = terrain[:1], terrain[1:]
            blocks, terrain = terrain[:4096], terrain[4096:]
            data, terrain = terrain[:2048], terrain[2048:]
            skyLight, terrain = terrain[:2048], terrain[2048:]
            blockLight, terrain = terrain[:2048], terrain[2048:]
#             print "self.Blocks", self.Blocks
#             print "self.Data", self.Data
#             print "self.SkyLight", self.SkyLight
#             print "self.BlockLight", self.BlockLight
#             print len(blocks)
            self.Blocks.add_data(subchunk, blocks)
#             print 1
            self.Data.add_data(subchunk, data)
#             print 2
            self.SkyLight.add_data(subchunk, skyLight)
#             print 3
            self.BlockLight.add_data(subchunk, blockLight)
#             print 4
        if tile_entities:
            if DEBUG_PE:
                open(dump_fName, 'a').write(('/' * 80) + '\nParsing TileEntities in chunk %s,%s\n'%(cx, cz))
            for e in loadNBTCompoundList(tile_entities):
                self.TileEntities.insert(-1, e)
        if entities:
#             print 'loading entities in chunk', cx, cz
            if DEBUG_PE:
                open(dump_fName, 'a').write(('\\' * 80) + '\nParsing Entities in chunk %s,%s\n'%(cx, cz))
            Entities = loadNBTCompoundList(entities)
            # PE saves entities with their int ID instead of string name. We swap them to make it work in mcedit.
            # Whenever we save an entity, we need to make sure to swap back.
            invertEntities = {v: k for k, v in entity.PocketEntity.entityList.items()}
            for ent in Entities:
                # Get the string id, or a build one
                # ! For PE debugging
                try:
                    v = ent["id"].value
                except Exception, e:
                    logger.warning("An error occured while getting entity ID:")
                    logger.warning(e)
                    logger.warning("Default 'Unknown' ID is used...")
                    v = 'Unknown'
                # !
                id = invertEntities.get(v, "Entity %s"%v)
                # Add the built one to the entities
                if id not in entity.PocketEntity.entityList.keys():
                    logger.warning("Found unknown entity '%s'"%v)
                    entity.PocketEntity.entityList[id] = v
                ent["id"] = nbt.TAG_String(id)

                self.Entities.insert(-1, ent)

    def _unpackChunkData(self):
        """
        Unpacks the terrain data to match mcedit's formatting.
        """
        for key in ('SkyLight', 'BlockLight', 'Data'):
#             print key
            dataArray = getattr(self, key)
#             print 'dataArray.shape', dataArray.shape
            if self.world_version == 'pre1.0':
                dataArray.shape = (16, 16, 64)
            else:
                if len(dataArray.data):
                    dataArray.shape = (16, 16, 8)
                else:
                    dataArray.shape = (0, 0, 0)
#             print 'dataArray.shape', dataArray.shape
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
        if self.world_version == 'pre1.0':
            blocksHeight = worldHeight = self.world.Height
        else:
            blocksHeight = 16
            worldHeight = 16
#         print 'self.Blocks.shape', self.Blocks.shape, len(self.Blocks.data)
#         print 'self.SkyLight.shape', self.SkyLight.shape, len(self.SkyLight.data)
#         print 'self.BlockLight.shape', self.BlockLight.shape, len(self.BlockLight.data)
#         print 'self.Data.shape', self.Data.shape, len(self.Data.data)
        if len(self.Blocks.data):
            self.Blocks.shape = (chunkSize, chunkSize, blocksHeight)
#         print 1
        if len(self.SkyLight.data):
            self.SkyLight.shape = (chunkSize, chunkSize, worldHeight)
#         print 2
        if len(self.BlockLight.data):
            self.BlockLight.shape = (chunkSize, chunkSize, worldHeight)
#         print 3
        if len(self.Data.data):
            self.Data.shape = (chunkSize, chunkSize, worldHeight)
#         print 4
        if self.world_version == 'pre1.0':
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

        with nbt.littleEndianNBT():
            entityData = ""
            tileEntityData = ""

            for ent in self.TileEntities:
                tileEntityData += ent.save(compressed=False)

            for ent in self.Entities:
                v = ent["id"].value
#                 ent["id"] = nbt.TAG_Int(entity.PocketEntity.entityList[v])
                id = entity.PocketEntity.getNumId(v)
#                 print id
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



if __builtins__.get('mcenf_newPocketSupport', False):
    PocketLeveldbChunk = PocketLeveldbChunk_new
    PocketLeveldbDatabase = PocketLeveldbDatabase_new
    PocketLeveldbWorld = PocketLeveldbWorld_new # Irrelevant...
else:
    PocketLeveldbChunk = PocketLeveldbChunk_old
    PocketLeveldbDatabase = PocketLeveldbDatabase_old
    PocketLeveldbWorld = PocketLeveldbWorld_old
