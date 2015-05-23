from leveldb_mcpe import DB, Options, ReadOptions, WriteOptions


op = Options()
op.create_if_missing = True
wop = WriteOptions()
rop = ReadOptions()
db = DB(op, "test")
db.Put(wop, "5", "5")
db.Put(wop, "2", "6")

if db.Get(rop, "5") != "5":
    print "Failed to retrieve correct value for key '1'. Expected '5', got: '{0}'".format(db.Get(rop, "1"))

db.Delete(wop, "2")
