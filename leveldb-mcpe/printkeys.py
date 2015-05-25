from leveldb_mcpe import DB, Options, ReadOptions, WriteOptions, WriteBatch

op = Options()
op.create_if_missing = True
wop = WriteOptions()
rop = ReadOptions()
db = DB(op, "Testdb\db")

with open('test.txt', 'w') as f:
    it = db.NewIterator(rop)
    it.SeekToFirst()
    while it.Valid():
        f.write(it.key())
        f.write("\n")
        it.Next()
    it.status()  # Possible errors are handled by C++ side

del it
del db
