from leveldb_mcpe import DB, Options, ReadOptions, WriteOptions, WriteBatch
import os
import array

op = Options()
op.create_if_missing = True
wop = WriteOptions()
rop = ReadOptions()
db = DB(op, os.path.sep.join(["Testdb", "db"]))

with open('test.txt', 'w') as f:
    it = db.NewIterator(rop)
    it.SeekToFirst()
    while it.Valid():
        a = array.array("B", it.key())
        xraw = a[0:4]
        zraw = a[4:8]
        chunkType = a[8]
        x = sum(xraw[i] << (i*8) for i in range(len(xraw)))
        z = sum(zraw[i] << (i*8) for i in range(len(zraw)))
        f.write(str(zraw) + str(x) + ", " + str(z) + "| " + str(chunkType))
        f.write("\n")
        it.Next()
    it.status()  # Possible errors are handled by C++ side

del it
del db
