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


it = db.NewIterator(rop)

it.SeekToFirst()
while it.Valid():
    print it.key() + ": " + it.value()
    it.Next()

it.status()  # Possible errors are handled by C++ side
del it
print "it deleted"





if exceptions > 0:
    print " {0} tests failed".format(exceptions)
else:
    print "Successfully completed test."

del db
print 'db deleted'
