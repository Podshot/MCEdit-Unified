import random
import traceback
import unittest
import leveldb_mcpe
import shutil


class TestLeveldbImpl(unittest.TestCase):
    db = None

    @classmethod
    def setUpClass(cls):
        op = leveldb_mcpe.Options()
        op.create_if_missing = True
        cls.db = leveldb_mcpe.DB(op, "test")

    @classmethod
    def tearDownClass(cls):
        del cls.db
        shutil.rmtree("test")

    def test_options(self):
        op = leveldb_mcpe.Options()
        op.create_if_missing = True
        self.assertTrue(op.create_if_missing)
        op.create_if_missing = False
        self.assertFalse(op.create_if_missing)

    def test_put_get(self):
        rop = leveldb_mcpe.ReadOptions()
        wop = leveldb_mcpe.WriteOptions()
        inputs = [{str(i), str(random.random())} for i in range(10)]
        for key, value in inputs:
            self.db.Put(wop, key, value)
        for key, value in inputs:
            self.assertTrue(self.db.Get(rop, key) == value)

    def test_db_delete(self):
        rop = leveldb_mcpe.ReadOptions()
        wop = leveldb_mcpe.WriteOptions()
        self.db.Put(wop, "ToDelete", "SomeString")
        self.db.Delete(wop, "ToDelete")
        with self.assertRaises(RuntimeError):
            self.db.Get(rop, "ToDelete")

    def test_write_batch(self):
        rop = leveldb_mcpe.ReadOptions()
        wop = leveldb_mcpe.WriteOptions()
        inputs = [{str(i), str(random.random())} for i in range(10)]

        batch = leveldb_mcpe.WriteBatch()
        for key, value in inputs:
            batch.Put(key, value)
        self.db.Write(wop, batch)
        del batch

        self.assertTrue(all([self.db.Get(rop, key) == value for key, value in inputs]))

    def test_iterator(self):
        rop = leveldb_mcpe.ReadOptions()
        wop = leveldb_mcpe.WriteOptions()
        inputs = [{str(i), str(random.random())} for i in range(10)]
        for key, value in inputs:
            self.db.Put(wop, key, value)
        it = self.db.NewIterator(rop)
        it.SeekToFirst()
        while it.Valid():
            it.Next()

        it.status()  # Possible errors are handled by C++ side
        del it

    def test_snapshot(self):
        rop = leveldb_mcpe.ReadOptions()
        wop = leveldb_mcpe.WriteOptions()
        self.db.Put(wop, "a", "old")
        self.db.Put(wop, "b", "old")

        snapshot = self.db.GetSnapshot()
        ropSnapshot = leveldb_mcpe.ReadOptions()
        ropSnapshot.snapshot = snapshot

        self.db.Put(wop, "a", "new")
        self.db.Put(wop, "b", "new")

        snapIt = self.db.NewIterator(ropSnapshot)
        newIt = self.db.NewIterator(rop)
        snapIt.SeekToFirst()
        newIt.SeekToFirst()

        while snapIt.Valid():
            self.assertTrue(snapIt.value() == "old" or snapIt.key() not in ("a", "b"))
            snapIt.Next()

        while newIt.Valid():
            self.assertTrue(newIt.value() == "new" or newIt.key() not in ("a", "b"))
            newIt.Next()

        del newIt, snapIt

    @unittest.expectedFailure
    def test_repair(self):
        try:
            rop = leveldb_mcpe.ReadOptions()
            wop = leveldb_mcpe.WriteOptions()
            op = leveldb_mcpe.Options()
            inputs = [{str(i), str(random.random())} for i in range(10)]
            for key, value in inputs:
                self.db.Put(wop, key, value)
            TestLeveldbImpl.db = None
            leveldb_mcpe.RepairWrapper("test", op)
            TestLeveldbImpl.db = leveldb_mcpe.DB(op, "test")
            for key, value in inputs:
                self.assertTrue(self.db.Get(rop, key) == value)
        except RuntimeError as err:
            print err
            traceback.print_exc()
            self.fail()

if __name__ == '__main__':
    unittest.main()
