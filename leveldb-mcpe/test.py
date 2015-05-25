exceptions = 0
from leveldb_mcpe import DB, Options, ReadOptions, WriteOptions, WriteBatch

op = Options()
op.create_if_missing = True
wop = WriteOptions()
rop = ReadOptions()
db = DB(op, "test")
db.Put(wop, "1", "5")
db.Put(wop, "2", "6")

if db.Get(rop, "1") != "5":
    print "Failed to retrieve correct value for key '1'. Expected '5', got: '{0}'".format(db.Get(rop, "1"))
    exceptions += 1

db.Delete(wop, "2")
try:
    db.Get(rop, "2")
    print "Failed to delete a value from the database"
    exceptions += 1
except:  # Maybe add a test for just the NoValue exception?
    pass

db.Put(wop, "3", "5")
db.Put(wop, "4", "6")

value1 = db.Get(rop, "3")
batch = WriteBatch()
batch.Delete("3")
batch.Put("4", "5")
db.Write(wop, batch)

del batch

try:
    db.Get(rop, "3")
    print "Failed to delete a value using WriteBatch"
    exceptions += 1
except:
    pass
if db.Get(rop, "4") != "5":
    print "Failed to write a value using WriteBatch"
    exceptions += 1

try:
    it = db.NewIterator(rop)
    it.SeekToFirst()
    while it.Valid():
        it.Next()

    it.status()  # Possible errors are handled by C++ side
    del it
except:
    print "Failed to iterate over database"
    exceptions += 1

try:
    db.Put(wop, "a", "old")
    db.Put(wop, "b", "old")

    snapshot = db.GetSnapshot()
    ropSnapshot = ReadOptions()
    ropSnapshot.snapshot = snapshot

    db.Put(wop, "a", "new")
    db.Put(wop, "b", "new")

    snapIt = db.NewIterator(ropSnapshot)
    newIt = db.NewIterator(rop)
    snapIt.SeekToFirst()
    newIt.SeekToFirst()

    while snapIt.Valid():
        if snapIt.key() in ("a", "b") and snapIt.value() != "old":
            print "Failed to retrieve correct value from database after creating a snapshot."
            exceptions += 1
        snapIt.Next()

    while newIt.Valid():
        if newIt.key() in ("a", "b") and newIt.value() != "new":
            print "Failed to retrieve correct value from database after creating a snapshot."
            exceptions += 1
        newIt.Next()
    del newIt, snapIt
except:
    print "Failed to test snapshots"
    exceptions += 1

db.ReleaseSnapshot(snapshot)

del db

if exceptions > 0:
    print " {0} tests failed".format(exceptions)
else:
    print "Successfully completed test."
