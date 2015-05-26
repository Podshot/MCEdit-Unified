from leveldb_mcpe import DB, Options, ReadOptions, WriteOptions, WriteBatch
import os
import struct

op = Options()
op.create_if_missing = True
wop = WriteOptions()
rop = ReadOptions()
db = DB(op, os.path.sep.join(["Testdb", "db"]))

with open('test.txt', 'w') as f:
    it = db.NewIterator(rop)
    it.SeekToFirst()
    while it.Valid():
        a = it.key()
        xraw = a[0:4]
        zraw = a[4:8]
        chunkType = a[8]
        x = struct.unpack('<i', xraw)[0]
        z = struct.unpack('<i', zraw)[0]
        f.write(str(x) + ", " + str(z) + "| " + str(chunkType))
        f.write("\n")
        it.Next()
    it.status()
del it
del db
