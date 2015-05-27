import itertools
from level import FakeChunk, MCLevel
import logging
from materials import pocketMaterials
import leveldb_mcpe
from mclevelbase import ChunkNotPresent, ChunkMalformed, ChunkAccessDenied
from nbt import TAG_List
from numpy import array, fromstring, zeros
import os
import struct
from infiniteworld import ChunkedLevelMixin, SessionLockLost
from level import LightedChunk
from contextlib import contextmanager

logger = logging.getLogger(__name__)

"""
TODO
Add entity support.
Add player support.
Add a way to edit the level.dat file.
Add a way to test for broken world and repair them (use leveldbs repairer, it's been wrapped already)
Setup loggers
"""

class PocketLeveldbDatabase(object):
    holdFileOpen = True
    _world_db = None
    _file = None

    @contextmanager
    def world_db(self):
        """
        Opens a leveldb and keeps it open until editing finished.
        :yield: DB
        """
        if PocketLeveldbDatabase.holdFileOpen:
            if self._world_db is None:
                self._world_db = leveldb_mcpe.DB(self.options, os.path.join(str(self.path)))
            yield self._world_db
            pass
        else:
            db = leveldb_mcpe.DB(self.options, os.path.join(str(self.path)))
            yield db
            del db

    @contextmanager
    def levelfile(self):
        """
        Opens a file and keeps it open until editing finished.
        Usage:
        with file as f: do stuff
        :yield: file
        """
        if PocketLeveldbDatabase.holdFileOpen:
            if self._file is None:
                self._file = open(os.path.join(self.path, 'level.dat'))
            yield self._file
        else:
            with open(os.path.join(self.path, 'level.dat')) as f:
                yield f

    def __init__(self, path):
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

        needsRepair = False
        with self.world_db() as db:
            pass  # Setup tests to see if the world is broken

        if needsRepair:
            leveldb_mcpe.RepairWrapper(os.path.join(path, 'db'))
        # Maybe setup a logger message with number of chunks in the database etc.

    def close(self):
        """
        Should be called before deleting this instance of the level.
        Not calling this method may result in corrupted worlds
        :return: None
        """
        if PocketLeveldbDatabase.holdFileOpen:
            if self._world_db is not None:
                del self._world_db
                self._world_db = None
            if self._file is not None:
                self._file.close()
                self._file = None

    def _readChunk(self, cx, cz, readOptions=None):
        """
        :param cx, cz: int Coordinates of the chunk
        :param db: DB
        :param readOptions: ReadOptions
        :return: None
        """
        key = struct.pack('<i', cx) + struct.pack('<i', cz) + "0"
        # print key
        with self.world_db() as db:
            rop = self.readOptions if readOptions is None else readOptions
            try:
                data = db.Get(rop, key)
            except RuntimeError:
                return None

        if len(data) != 83200:
            raise ChunkMalformed(str(len(data)))

        logger.debug("CHUNK LOAD %s %s", cx, cz)
        return data

    def saveChunk(self, chunk, batch=None, writeOptions=None):
        """
        :param chunk: PocketLeveldbChunk
        :param db: DB or WriteBatch
        :param writeOptions: WriteOptions
        :return: None
        """
        cx, cz = chunk.chunkPosition
        data = chunk.savedData()
        key = struct.pack('<i', cx) + struct.pack('<i', cz) + "0"

        if batch is None:
            with self.world_db() as db:
                wop = self.writeOptions if writeOptions is None else writeOptions
                db.Put(key, data, wop)
        else:
            batch.Put(key, data)

    def loadChunk(self, cx, cz, world):
        """
        :param cx, cz: int Coordinates of the chunk
        :param world: PocketLeveldbWorld
        :param db: DB
        :return: PocketLeveldbChunk
        """
        data = self._readChunk(cx, cz)
        if data is None:
            raise ChunkNotPresent((cx, cz, self))

        chunk = PocketLeveldbChunk(cx, cz, data, world)
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
        :param db: DB
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
                rawx = key[0:4]
                rawz = key[4:8]
                t = key[8]

                if t == "0":
                    cx, cz = struct.unpack('<i', rawx), struct.unpack('<i', rawz)
                    allChunks.append((cx[0], cz[0]))
                it.Next()
            it.status()  # All this does is cause an exception if something went wrong. Might be unneeded?
            del it
            return allChunks

class PocketLeveldbWorld(ChunkedLevelMixin, MCLevel):
    Height = 128
    Width = 0
    Length = 0

    isInfinite = True
    materials = pocketMaterials

    _allChunks = None  # An array of cx, cz pairs.
    _loadedChunks = {}  # A dictionary of actual PocketLeveldbChunk objects mapped by (cx, cz)

    @property
    def allChunks(self):
        if self._allChunks is None:
            self._allChunks = self.chunkFile.getAllChunks()
        return self._allChunks

    def __init__(self, filename):
        if not os.path.isdir(filename):
            filename = os.path.dirname(filename)
        self.filename = filename

        self.chunkFile = PocketLeveldbDatabase(os.path.join(filename, 'db'))

    def getChunk(self, cx, cz):
        c = self._loadedChunks.get((cx, cz))
        if c is None:
            c = self.chunkFile.loadChunk(cx, cz, self)
            self._loadedChunks[(cx, cz)] = c
        return c

    def unload(self):
        """
        Unload all chunks and close all open file-handlers.
        """
        self._loadedChunks.clear()
        self._allChunks = None
        self.chunkFile.close()

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
        self.chunkFile.deleteChunk(cx, cz, batch=batch)
        if self._loadedChunks is not None and (cx, cz) in self._loadedChunks:  # Unnecessary check?
            del self._loadedChunks[(cx, cz)]
            self.allChunks.remove((cx, cz))

    def deleteChunksInBox(self, box):
        logger.info(u"Deleting {0} chunks in {1}".format((box.maxcx - box.mincx) * (box.maxcz - box.mincz),
                                                         ((box.mincx, box.mincz), (box.maxcx, box.maxcz))))
        i = 0
        ret = []
        batch = leveldb_mcpe.WriteBatch()
        print 'test'
        for cx, cz in itertools.product(xrange(box.mincx, box.maxcx), xrange(box.mincz, box.maxcz)):
            i += 1
            if self.containsChunk(cx, cz):
                self.deleteChunk(cx, cz, batch=batch)
                ret.append((cx, cz))

            assert not self.containsChunk(cx, cz), "Just deleted {0} but it didn't take".format((cx, cz))

            if i % 100 == 0:
                logger.info(u"Chunk {0}...".format(i))

        with self.chunkFile.world_db() as db:
            wop = self.chunkFile.writeOptions
            db.Write(wop, batch)

        del batch
        return ret

    @classmethod
    def _isLevel(cls, filename):
        clp = ("db", "level.dat")

        if not os.path.isdir(filename):
            f = os.path.basename(filename)
            if f not in clp:
                return False
            filename = os.path.dirname(filename)

        return all([os.path.exists(os.path.join(filename, fl)) for fl in clp])

    def saveInPlaceGen(self):
        batch = leveldb_mcpe.WriteBatch()
        for chunk in self._loadedChunks.itervalues():
            if chunk.dirty:
                self.chunkFile.saveChunk(chunk, batch=batch)
                chunk.dirty = False
            yield

        with self.chunkFile.world_db() as db:
            wop = self.chunkFile.writeOptions
            db.Write(wop, batch)

    def containsChunk(self, cx, cz):
        return (cx, cz) in self.allChunks

    @property
    def chunksNeedingLighting(self):
        for chunk in self._loadedChunks.itervalues():
            if chunk.needsLighting:
                yield chunk.chunkPosition


class PocketLeveldbChunk(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    Entities = TileEntities = property(lambda self: TAG_List())
    dirty = False

    def __init__(self, cx, cz, data, world):
        self.chunkPosition = (cx, cz)
        self.world = world
        data = fromstring(data, dtype='uint8')

        self.Blocks, data = data[:32768], data[32768:]
        self.Data, data = data[:16384], data[16384:]
        self.SkyLight, data = data[:16384], data[16384:]
        self.BlockLight, data = data[:16384], data[16384:]
        self.DirtyColumns, data = data[:256], data[256:]
        self.GrassColors = data[:1024]  # Unused at the moment. Might need a special editor? Maybe hooked up to biomes?

        self.unpackChunkData()
        self.shapeChunkData()

    """
    For the sake of testing purposes, the chunks get unpacked as old pocket-chunk data.
    Values may have changed, needs verification.
    """

    def unpackChunkData(self):
        for key in ('SkyLight', 'BlockLight', 'Data'):
            dataArray = getattr(self, key)
            dataArray.shape = (16, 16, 64)
            s = dataArray.shape

            unpackedData = zeros((s[0], s[1], s[2] * 2), dtype='uint8')

            unpackedData[:, :, ::2] = dataArray
            unpackedData[:, :, ::2] &= 0xf
            unpackedData[:, :, 1::2] = dataArray
            unpackedData[:, :, 1::2] >>= 4
            setattr(self, key, unpackedData)

    def shapeChunkData(self):
        chunkSize = 16
        self.Blocks.shape = (chunkSize, chunkSize, self.world.Height)
        self.SkyLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.BlockLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.Data.shape = (chunkSize, chunkSize, self.world.Height)
        self.DirtyColumns.shape = chunkSize, chunkSize

    def savedData(self):
        def packData(dataArray):
            assert dataArray.shape[2] == self.world.Height

            data = array(dataArray).reshape(16, 16, self.world.Height / 2, 2)
            data[..., 1] <<= 4
            data[..., 1] |= data[..., 0]
            return array(data[:, :, :, 1])

        if self.dirty:
            # elements of DirtyColumns are bitfields. Each bit corresponds to a
            # 16-block segment of the column. We set all of the bits because
            # we only track modifications at the chunk level.
            self.DirtyColumns[:] = 255

        return ''.join([self.Blocks.tostring(),
                        packData(self.Data).tostring(),
                        packData(self.SkyLight).tostring(),
                        packData(self.BlockLight).tostring(),
                        self.DirtyColumns.tostring(),
                        self.GrassColors.tostring(),
                        ])