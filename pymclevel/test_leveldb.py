# !/usr/bin/env python
#
# Copyright (C) 2012 Space Monkey, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import os
import sys
import time
import shutil
import random
import leveldb
import argparse
import tempfile
import unittest


class LevelDBTestCasesMixIn(object):
    db_class = None

    def setUp(self):
        self.db_path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.db_path, ignore_errors=True)

    def testPutGet(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "key1", "val1")
        db.Put(leveldb.WriteOptions(), "key2", "val2", sync=True)
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key1"), "val1")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key2"), "val2")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key1", verify_checksums=True), "val1")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key2", verify_checksums=True), "val2")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key1", fill_cache=False), "val1")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key2", fill_cache=False), "val2")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key1", verify_checksums=True,
                                fill_cache=False), "val1")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key2", verify_checksums=True,
                                fill_cache=False), "val2")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key1"), "val1")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key2"), "val2")
        self.assertEqual(list(db.keys()), ["key1", "key2"])
        self.assertEqual(list(db.keys(prefix="key")), ["1", "2"])
        self.assertEqual(list(db.keys(prefix="key1")), [""])
        self.assertEqual(list(db.values()), ["val1", "val2"])
        self.assertEqual(list(db.values(prefix="key")), ["val1", "val2"])
        self.assertEqual(list(db.values(prefix="key1")), ["val1"])
        db.close()

    def testDelete(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        self.assertTrue(db.Get(leveldb.ReadOptions(), "key1") is None)
        self.assertTrue(db.Get(leveldb.ReadOptions(), "key2") is None)
        self.assertTrue(db.Get(leveldb.ReadOptions(), "key3") is None)
        db.Put(leveldb.WriteOptions(), "key1", "val1")
        db.Put(leveldb.WriteOptions(), "key2", "val2")
        db.Put(leveldb.WriteOptions(), "key3", "val3")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key1"), "val1")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key2"), "val2")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key3"), "val3")
        db.delete("key1")
        db.delete("key2", sync=True)
        self.assertTrue(db.Get(leveldb.ReadOptions(), "key1") is None)
        self.assertTrue(db.Get(leveldb.ReadOptions(), "key2") is None)
        self.assertEqual(db.Get(leveldb.ReadOptions(), "key3"), "val3")
        db.close()

    def testRange(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)

        def keys(alphabet, length=5):
            if length == 0:
                yield ""
                return
            for char in alphabet:
                for prefix in keys(alphabet, length - 1):
                    yield prefix + char

        for val, key in enumerate(keys(map(chr, xrange(ord('a'), ord('f'))))):
            db.Put(leveldb.WriteOptions(), key, str(val))

        self.assertEquals([row.key for row in db.range("bbbb", "bbcb")],
                          ['bbbba', 'bbbbb', 'bbbbc', 'bbbbd', 'bbbbe', 'bbbca', 'bbbcb',
                           'bbbcc', 'bbbcd', 'bbbce', 'bbbda', 'bbbdb', 'bbbdc', 'bbbdd',
                           'bbbde', 'bbbea', 'bbbeb', 'bbbec', 'bbbed', 'bbbee', 'bbcaa',
                           'bbcab', 'bbcac', 'bbcad', 'bbcae'])
        self.assertEquals([row.key for row in db.range("bbbbb", "bbcbb")],
                          ['bbbbb', 'bbbbc', 'bbbbd', 'bbbbe', 'bbbca', 'bbbcb', 'bbbcc',
                           'bbbcd', 'bbbce', 'bbbda', 'bbbdb', 'bbbdc', 'bbbdd', 'bbbde',
                           'bbbea', 'bbbeb', 'bbbec', 'bbbed', 'bbbee', 'bbcaa', 'bbcab',
                           'bbcac', 'bbcad', 'bbcae', 'bbcba'])
        self.assertEquals([r.key for r in db.scope("dd").range("bb", "cb")],
                          ['bba', 'bbb', 'bbc', 'bbd', 'bbe', 'bca', 'bcb', 'bcc', 'bcd',
                           'bce', 'bda', 'bdb', 'bdc', 'bdd', 'bde', 'bea', 'beb', 'bec',
                           'bed', 'bee', 'caa', 'cab', 'cac', 'cad', 'cae'])
        self.assertEquals([r.key for r in db.scope("dd").range("bbb", "cbb")],
                          ['bbb', 'bbc', 'bbd', 'bbe', 'bca', 'bcb', 'bcc', 'bcd', 'bce',
                           'bda', 'bdb', 'bdc', 'bdd', 'bde', 'bea', 'beb', 'bec', 'bed',
                           'bee', 'caa', 'cab', 'cac', 'cad', 'cae', 'cba'])

    def testRangeOptionalEndpoints(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "aa", "1")
        db.Put(leveldb.WriteOptions(), "bb", "2")
        db.Put(leveldb.WriteOptions(), "cc", "3")
        db.Put(leveldb.WriteOptions(), "dd", "4")
        db.Put(leveldb.WriteOptions(), "ee", "5")

        self.assertEquals([r.key for r in db.NewIterator().seek("d").range()],
                          ["aa", "bb", "cc", "dd", "ee"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb")], ["bb", "cc", "dd", "ee"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            end_key="cc")], ["aa", "bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb", end_key="cc")], ["bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b")], ["bb", "cc", "dd", "ee"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            end_key="c")], ["aa", "bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b", end_key="c")], ["bb"])

        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb", start_inclusive=True)],
                          ["bb", "cc", "dd", "ee"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb", start_inclusive=False)],
                          ["cc", "dd", "ee"])

        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            end_key="cc", end_inclusive=True)], ["aa", "bb", "cc"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            end_key="cc", end_inclusive=False)], ["aa", "bb"])

        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb", end_key="cc", start_inclusive=True,
            end_inclusive=True)], ["bb", "cc"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb", end_key="cc", start_inclusive=True,
            end_inclusive=False)], ["bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb", end_key="cc", start_inclusive=False,
            end_inclusive=True)], ["cc"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="bb", end_key="cc", start_inclusive=False,
            end_inclusive=False)], [])

        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b", start_inclusive=True)],
                          ["bb", "cc", "dd", "ee"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b", start_inclusive=False)],
                          ["bb", "cc", "dd", "ee"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            end_key="c", end_inclusive=True)], ["aa", "bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            end_key="c", end_inclusive=False)], ["aa", "bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b", end_key="c", start_inclusive=True,
            end_inclusive=True)], ["bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b", end_key="c", start_inclusive=False,
            end_inclusive=True)], ["bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b", end_key="c", start_inclusive=True,
            end_inclusive=False)], ["bb"])
        self.assertEquals([r.key for r in db.NewIterator().seek("d").range(
            start_key="b", end_key="c", start_inclusive=False,
            end_inclusive=False)], ["bb"])

    def testScopedDB(self, use_writebatch=False):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        scoped_db_1 = db.scope("prefix1_")
        scoped_db_2 = db.scope("prefix2_")
        scoped_db_2a = scoped_db_2.scope("a_")
        scoped_db_2b = scoped_db_2.scope("b_")
        scoped_db_3 = db.scope("prefix3_")
        w_opts = leveldb.WriteOptions()

        def mod(op, db, ops):
            if use_writebatch:
                batch = leveldb.WriteBatch()
                for args in ops:
                    getattr(batch, op)(*args)
                db.write(leveldb.WriteOptions(), batch)
            else:
                for args in ops:
                    if op != "delete":
                        args = list(args)
                        args.insert(0, w_opts)
                    getattr(db, op)(*args)

        mod("put", db, [("1", "2"), ("prefix2_a_13", "14")])
        mod("put", scoped_db_1, [("3", "4")])
        mod("put", scoped_db_2, [("5", "6")])
        mod("put", scoped_db_2a, [("7", "8")])
        mod("put", scoped_db_2b, [("9", "10")])
        mod("put", scoped_db_3, [("11", "12")])
        db_data = [("1", "2"), ("prefix1_3", "4"), ("prefix2_5", "6"),
                   ("prefix2_a_13", "14"), ("prefix2_a_7", "8"),
                   ("prefix2_b_9", "10"), ("prefix3_11", "12")]
        self.assertEquals(list(db), db_data)
        self.assertEquals(list(scoped_db_1), [("3", "4")])
        scoped_db_2_data = [("5", "6"), ("a_13", "14"), ("a_7", "8"),
                            ("b_9", "10")]
        self.assertEquals(list(scoped_db_2), scoped_db_2_data)
        self.assertEquals(list(scoped_db_2a), [("13", "14"), ("7", "8")])
        self.assertEquals(list(scoped_db_2b), [("9", "10")])
        self.assertEquals(list(scoped_db_3), [("11", "12")])
        for key, val in db_data:
            self.assertEquals(db.Get(leveldb.ReadOptions(), key), val)
        for key, val in scoped_db_2_data:
            self.assertEquals(scoped_db_2.Get(leveldb.ReadOptions(), key), val)
        self.assertEquals(scoped_db_1.Get(leveldb.ReadOptions(), "3"), "4")
        self.assertEquals(scoped_db_2a.Get(leveldb.ReadOptions(), "7"), "8")
        self.assertEquals(scoped_db_2b.Get(leveldb.ReadOptions(), "9"), "10")
        self.assertEquals(scoped_db_3.Get(leveldb.ReadOptions(), "11"), "12")
        self.assertEqual(scoped_db_2a.Get(leveldb.ReadOptions(), "13"), "14")
        mod("delete", db, [["1"], ["prefix2_a_7"]])
        mod("delete", scoped_db_1, [["3"]])
        mod("delete", scoped_db_2, [["5"]])
        mod("delete", scoped_db_2a, [["13"]])
        mod("delete", scoped_db_2b, [["9"]])
        mod("delete", scoped_db_3, [["11"]])
        self.assertEquals(list(db), [])
        self.assertEquals(list(scoped_db_1), [])
        self.assertEquals(list(scoped_db_2), [])
        self.assertEquals(list(scoped_db_2a), [])
        self.assertEquals(list(scoped_db_2b), [])
        self.assertEquals(list(scoped_db_3), [])
        for key, val in db_data:
            self.assertEquals(db.Get(leveldb.ReadOptions(), key), None)
        for key, val in scoped_db_2_data:
            self.assertEquals(scoped_db_2.Get(leveldb.ReadOptions(), key), None)
        self.assertEquals(scoped_db_1.Get(leveldb.ReadOptions(), "3"), None)
        self.assertEquals(scoped_db_2a.Get(leveldb.ReadOptions(), "7"), None)
        self.assertEquals(scoped_db_2b.Get(leveldb.ReadOptions(), "9"), None)
        self.assertEquals(scoped_db_3.Get(leveldb.ReadOptions(), "11"), None)
        self.assertEqual(scoped_db_2a.Get(leveldb.ReadOptions(), "13"), None)
        db.close()

    def testScopedDB_WriteBatch(self):
        self.testScopedDB(use_writebatch=True)

    def testOpaqueWriteBatch(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        scoped_db = db.scope("prefix2_")
        scopes = [db.scope("prefix1_"), scoped_db, scoped_db.scope("a_"),
                  scoped_db.scope("b_"), db.scope("prefix3_")]
        batch = db.newBatch()
        for i, scope in enumerate(scopes):
            scope.putTo(batch, str(i), str(i))
        db.write(leveldb.WriteOptions(), batch)
        for i, scope in enumerate(scopes):
            self.assertEquals(scope.Get(leveldb.ReadOptions(), str(i)), str(i))
        batch.clear()
        for i, scope in enumerate(scopes):
            scope.deleteFrom(batch, str(i))
        db.write(leveldb.WriteOptions(), batch)
        for i, scope in enumerate(scopes):
            self.assertEquals(scope.Get(leveldb.ReadOptions(), str(i)), None)
        # same effect when done through any scope
        batch = random.choice(scopes).newBatch()
        for i, scope in enumerate(scopes):
            scope.putTo(batch, str(i), str(2 * (i + 1)))
        random.choice(scopes).write(leveldb.WriteOptions(), batch)
        for i, scope in enumerate(scopes):
            self.assertEquals(scope.Get(leveldb.ReadOptions(), str(i)), str(2 * (i + 1)))
        batch.clear()
        for i, scope in enumerate(scopes):
            scope.deleteFrom(batch, str(i))
        random.choice(scopes).write(leveldb.WriteOptions(), batch)
        for i, scope in enumerate(scopes):
            self.assertEquals(scope.Get(leveldb.ReadOptions(), str(i)), None)

    def testKeysWithZeroBytes(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        key_with_zero_byte = "\x01\x00\x02\x03\x04"
        db.Put(leveldb.WriteOptions(), key_with_zero_byte, "hey")
        self.assertEqual(db.Get(leveldb.ReadOptions(), key_with_zero_byte), "hey")
        it = db.NewIterator().SeekToFirst()
        self.assertTrue(it.Valid())
        self.assertEqual(it.value(), "hey")
        self.assertEqual(it.key(), key_with_zero_byte)
        self.assertEqual(db.Get(leveldb.ReadOptions(), it.key()), "hey")
        db.close()

    def testValuesWithZeroBytes(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        value_with_zero_byte = "\x01\x00\x02\x03\x04"
        db.Put(leveldb.WriteOptions(), "hey", value_with_zero_byte)
        self.assertEqual(db.Get(leveldb.ReadOptions(), "hey"), value_with_zero_byte)
        it = db.NewIterator().SeekToFirst()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "hey")
        self.assertEqual(it.value(), value_with_zero_byte)
        db.close()

    def testKeyRewrite(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        self.assertEqual(db.Get(leveldb.ReadOptions(), "hey"), None)
        db.Put(leveldb.WriteOptions(), "hey", "1")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "hey"), "1")
        db.Put(leveldb.WriteOptions(), "hey", "2")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "hey"), "2")
        db.Put(leveldb.WriteOptions(), "hey", "2")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "hey"), "2")
        db.Put(leveldb.WriteOptions(), "hey", "3")
        self.assertEqual(db.Get(leveldb.ReadOptions(), "hey"), "3")

    def test__getsetitem__(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db["hey"] = "1"
        self.assertTrue("hey" in db)
        self.assertEqual(db["hey"], "1")
        db["hey"] = "2"
        self.assertEqual(db["hey"], "2")
        db["hey"] = "2"
        self.assertEqual(db["hey"], "2")
        db["hey"] = "3"
        self.assertEqual(db["hey"], "3")

    def test__contains__(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        self.assertTrue("hey" not in db)
        with self.assertRaises(KeyError):
            db["hey"]
        db["hey"] = "1"
        self.assertTrue("hey" in db)

    def test__delitem__(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        self.assertTrue("hey" not in db)
        db["hey"] = "1"
        self.assertTrue("hey" in db)
        del db["hey"]
        self.assertTrue("hey" not in db)

    def testSnapshots(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        snapshot = db.snapshot()
        db["hey"] = "1"
        db["there"] = "2"
        self.assertEqual(len(list(db)), 2)
        self.assertEqual(len(list(snapshot)), 0)
        snapshot = db.snapshot()
        self.assertEqual(len(list(snapshot)), 2)
        self.assertEqual(snapshot["hey"], "1")
        self.assertEqual(snapshot["there"], "2")
        self.assertEqual(db["hey"], "1")
        self.assertEqual(db["there"], "2")
        db["hey"] = "3"
        db["there"] = "4"
        self.assertEqual(snapshot["hey"], "1")
        self.assertEqual(snapshot["there"], "2")
        self.assertEqual(db["hey"], "3")
        self.assertEqual(db["there"], "4")


class LevelDBTestCases(LevelDBTestCasesMixIn, unittest.TestCase):
    db_class = staticmethod(leveldb.DB)

    def testInit(self):
        self.assertRaises(leveldb.Error, self.db_class, leveldb.Options(), self.db_path)
        self.db_class(leveldb.Options(), self.db_path, create_if_missing=True).close()
        self.db_class(leveldb.Options(), self.db_path, create_if_missing=True).close()
        self.db_class(leveldb.Options(), self.db_path).close()
        self.assertRaises(leveldb.Error, self.db_class, leveldb.Options(), self.db_path,
                          create_if_missing=True, error_if_exists=True)

    def testPutSync(self, size=100):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        for i in xrange(size):
            db.Put(leveldb.WriteOptions(), str(i), str(i + 1))
        start_sync_time = time.time()
        for i in xrange(size):
            db.Put(leveldb.WriteOptions(), str(i), str(i + 1), sync=True)
        start_unsync_time = time.time()
        for i in xrange(size):
            db.Put(leveldb.WriteOptions(), str(i), str(i + 1))
        end_time = time.time()
        sync_time = start_unsync_time - start_sync_time
        unsync_time = end_time - start_unsync_time
        self.assertTrue(sync_time > 10 * unsync_time)
        db.close()

    def testDeleteSync(self, size=100):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        for i in xrange(size):
            db.Put(leveldb.WriteOptions(), str(i), str(i + 1))
        start_sync_time = time.time()
        for i in xrange(size):
            db.delete(str(i), sync=True)
        end_sync_time = time.time()
        for i in xrange(size):
            db.Put(leveldb.WriteOptions(), str(i), str(i + 1))
        start_unsync_time = time.time()
        for i in xrange(size):
            db.delete(str(i))
        end_unsync_time = time.time()
        sync_time = end_sync_time - start_sync_time
        unsync_time = end_unsync_time - start_unsync_time
        self.assertTrue(sync_time > 10 * unsync_time)
        db.close()

    def testSegfaultFromIssue2(self, short_time=10):
        """https://code.google.com/p/leveldb-py/issues/detail?id=2"""
        # i assume the reporter meant opening a new db a bunch of times?
        paths = []
        dbs = []
        start_time = time.time()
        while time.time() - start_time < short_time:
            path = tempfile.mkdtemp()
            paths.append(path)
            db = self.db_class(leveldb.Options(), path, create_if_missing=True)
            batch = leveldb.WriteBatch()
            for x in xrange(10000):
                batch.Put(str(x), str(x))
            db.write(leveldb.WriteOptions(), batch)
            dbs.append(db)
        for db in dbs:
            db.close()

        # maybe the reporter meant opening the same db over and over?
        start_time = time.time()
        path = tempfile.mkdtemp()
        paths.append(path)
        while time.time() - start_time < short_time:
            db = self.db_class(leveldb.Options(), path, create_if_missing=True)
            batch = leveldb.WriteBatch()
            for x in xrange(10000):
                batch.Put(str(x), str(x))
            db.write(leveldb.WriteOptions(), batch)
            db.close()

        # or maybe the same db handle, but lots of write batches?
        start_time = time.time()
        path = tempfile.mkdtemp()
        paths.append(path)
        db = self.db_class(leveldb.Options(), path, create_if_missing=True)
        while time.time() - start_time < short_time:
            batch = leveldb.WriteBatch()
            for x in xrange(10000):
                batch.Put(str(x), str(x))
            db.write(leveldb.WriteOptions(), batch)
        db.close()

        # or maybe it was lots of batch puts?
        start_time = time.time()
        path = tempfile.mkdtemp()
        paths.append(path)
        db = self.db_class(leveldb.Options(), path, create_if_missing=True)
        batch = leveldb.WriteBatch()
        x = 0
        while time.time() - start_time < short_time:
            batch.Put(str(x), str(x))
            x += 1
        db.write(leveldb.WriteOptions(), batch)
        db.close()

        # if we got here, we haven't segfaulted, so, i dunno
        for path in paths:
            shutil.rmtree(path)


class MemLevelDBTestCases(LevelDBTestCasesMixIn, unittest.TestCase):
    db_class = staticmethod(leveldb.MemoryDB)


class LevelDBIteratorTestMixIn(object):
    db_class = None

    def setUp(self):
        self.db_path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.db_path)

    def test_iteration(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), 'a', 'b')
        db.Put(leveldb.WriteOptions(), 'c', 'd')
        iterator = iter(db)
        self.assertEqual(iterator.next(), ('a', 'b'))
        self.assertEqual(iterator.next(), ('c', 'd'))
        self.assertRaises(StopIteration, iterator.next)
        db.close()

    def test_iteration_keys_only(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), 'a', 'b')
        db.Put(leveldb.WriteOptions(), 'c', 'd')
        iterator = db.NewIterator(keys_only=True).SeekToFirst()
        self.assertEqual(iterator.next(), 'a')
        self.assertEqual(iterator.next(), 'c')
        self.assertRaises(StopIteration, iterator.next)
        db.close()

    def test_iteration_with_break(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), 'a', 'b')
        db.Put(leveldb.WriteOptions(), 'c', 'd')
        for key, value in db:
            self.assertEqual((key, value), ('a', 'b'))
            break
        db.close()

    def test_iteration_empty_db(self):
        """
        Test the null condition, no entries in the database.
        """
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        for _ in db:
            self.fail("shouldn't happen")
        db.close()

    def test_seek(self):
        """
        Test seeking forwards and backwards
        """
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), 'a', 'b')
        db.Put(leveldb.WriteOptions(), 'b', 'b')
        db.Put(leveldb.WriteOptions(), 'ca', 'a')
        db.Put(leveldb.WriteOptions(), 'cb', 'b')
        db.Put(leveldb.WriteOptions(), 'd', 'd')
        iterator = iter(db).seek("c")
        self.assertEqual(iterator.next(), ('ca', 'a'))
        self.assertEqual(iterator.next(), ('cb', 'b'))
        # seek backwards
        iterator.seek('a')
        self.assertEqual(iterator.next(), ('a', 'b'))
        db.close()

    def test_prefix(self):
        """
        Test iterator prefixes
        """
        batch = leveldb.WriteBatch()
        batch.Put('a', 'b')
        batch.Put('b', 'b')
        batch.Put('cd', 'a')
        batch.Put('ce', 'a')
        batch.Put('c', 'a')
        batch.Put('f', 'b')
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.write(leveldb.WriteOptions(), batch)
        iterator = db.NewIterator(prefix="c")
        iterator.SeekToFirst()
        self.assertEqual(iterator.next(), ('', 'a'))
        self.assertEqual(iterator.next(), ('d', 'a'))
        self.assertEqual(iterator.next(), ('e', 'a'))
        self.assertRaises(StopIteration, iterator.next)
        db.close()

    def test_multiple_iterators(self):
        """
        Make sure that things work with multiple iterator objects
        alive at one time.
        """
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        entries = [('a', 'b'), ('b', 'b')]
        db.Put(leveldb.WriteOptions(), *entries[0])
        db.Put(leveldb.WriteOptions(), *entries[1])
        iter1 = iter(db)
        iter2 = iter(db)
        self.assertEqual(iter1.next(), entries[0])
        # garbage collect iter1, seek iter2 past the end of the db. Make sure
        # everything works.
        del iter1
        iter2.seek('z')
        self.assertRaises(StopIteration, iter2.next)
        db.close()

    def test_prev(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), 'a', 'b')
        db.Put(leveldb.WriteOptions(), 'b', 'b')
        iterator = iter(db)
        entry = iterator.next()
        iterator.Prev()
        self.assertEqual(entry, iterator.next())
        # it's ok to call prev when the iterator is at position 0
        iterator.Prev()
        self.assertEqual(entry, iterator.next())
        db.close()

    def test_seek_first_last(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        db.Put(leveldb.WriteOptions(), 'a', 'b')
        db.Put(leveldb.WriteOptions(), 'b', 'b')
        iterator = iter(db)
        iterator.SeekToLast()
        self.assertEqual(iterator.next(), ('b', 'b'))
        iterator.SeekToFirst()
        self.assertEqual(iterator.next(), ('a', 'b'))
        db.close()

    def test_scoped_seek_first(self):
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "1"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "ba", "1")
        db.Put(leveldb.WriteOptions(), "bb", "2")
        db.Put(leveldb.WriteOptions(), "cc", "3")
        db.Put(leveldb.WriteOptions(), "cd", "4")
        db.Put(leveldb.WriteOptions(), "de", "5")
        db.Put(leveldb.WriteOptions(), "df", "6")
        it = db.scope("a").NewIterator().SeekToFirst()
        self.assertFalse(it.Valid())
        it = db.scope("b").NewIterator().SeekToFirst()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "a")
        it = db.scope("c").NewIterator().SeekToFirst()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "c")
        it = db.scope("d").NewIterator().SeekToFirst()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "e")
        it = db.scope("e").NewIterator().SeekToFirst()
        self.assertFalse(it.Valid())
        db.close()

    def test_scoped_seek_last(self):
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "1"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "ba", "1")
        db.Put(leveldb.WriteOptions(), "bb", "2")
        db.Put(leveldb.WriteOptions(), "cc", "3")
        db.Put(leveldb.WriteOptions(), "cd", "4")
        db.Put(leveldb.WriteOptions(), "de", "5")
        db.Put(leveldb.WriteOptions(), "df", "6")
        it = db.scope("a").NewIterator().SeekToLast()
        self.assertFalse(it.Valid())
        it = db.scope("b").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "b")
        it = db.scope("c").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "d")
        it = db.scope("d").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "f")
        it = db.scope("e").NewIterator().SeekToLast()
        self.assertFalse(it.Valid())
        db.close()
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "2"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "\xff\xff\xffab", "1")
        db.Put(leveldb.WriteOptions(), "\xff\xff\xffcd", "2")
        it = db.scope("\xff\xff\xff").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "cd")
        db.close()
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "3"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "\xff\xff\xfeab", "1")
        db.Put(leveldb.WriteOptions(), "\xff\xff\xfecd", "2")
        it = db.scope("\xff\xff\xff").NewIterator().SeekToLast()
        self.assertFalse(it.Valid())
        db.close()
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "4"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "\xff\xff\xfeab", "1")
        db.Put(leveldb.WriteOptions(), "\xff\xff\xfecd", "2")
        it = db.scope("\xff\xff\xfe").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "cd")
        db.close()
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "5"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "\xff\xff\xfeab", "1")
        db.Put(leveldb.WriteOptions(), "\xff\xff\xfecd", "2")
        db.Put(leveldb.WriteOptions(), "\xff\xff\xffef", "1")
        db.Put(leveldb.WriteOptions(), "\xff\xff\xffgh", "2")
        it = db.scope("\xff\xff\xfe").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "cd")
        db.close()
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "6"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "\x0f\xff\xfeab", "1")
        db.Put(leveldb.WriteOptions(), "\x0f\xff\xfecd", "2")
        db.Put(leveldb.WriteOptions(), "\x0f\xff\xffef", "1")
        db.Put(leveldb.WriteOptions(), "\x0f\xff\xffgh", "2")
        it = db.scope("\x0f\xff\xfe").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "cd")
        db.close()
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "7"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "\x10\xff", "1")
        db.Put(leveldb.WriteOptions(), "\x11", "2")
        it = db.scope("\x10\xff").NewIterator().SeekToLast()
        self.assertTrue(it.Valid())
        self.assertEqual(it.value(), "1")
        db.close()

    def test_seek_last_with_leading_zero_prefix(self):
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "1"),
                           create_if_missing=True)
        db.Put(leveldb.WriteOptions(), "\x00\x00\x00", "1")
        db.Put(leveldb.WriteOptions(), "\x00\x00\xff", "2")
        db.Put(leveldb.WriteOptions(), "\x00\x01\x00", "3")
        db.Put(leveldb.WriteOptions(), "\x01\x01\x00", "4")
        self.assertEqual(db.NewIterator(prefix="\x00\x00\x00").SeekToLast().value(),
                         "1")
        self.assertEqual(db.NewIterator(prefix="\x00\x00").SeekToLast().value(),
                         "2")
        self.assertEqual(db.NewIterator(prefix="\x00").SeekToLast().value(),
                         "3")
        db.close()

    def test_scoped_then_iterate(self):
        db = self.db_class(leveldb.Options(), os.path.join(self.db_path, "1"),
                           create_if_missing=True)
        for i in range(10):
            db.Put(leveldb.WriteOptions(), "%dfoo" % i, "bar%d" % i)
        it = db.NewIterator(prefix="5").SeekToFirst()
        self.assertTrue(it.Valid())
        self.assertEqual(it.key(), "foo")
        self.assertEqual(it.value(), "bar5")

        for id_, (k, v) in enumerate(it):
            self.assertEqual(id_, 0)
            self.assertEqual(k, "foo")
            self.assertEqual(v, "bar5")


class LevelDBIteratorTest(LevelDBIteratorTestMixIn, unittest.TestCase):
    db_class = staticmethod(leveldb.DB)

    def testApproximateSizes(self):
        db = self.db_class(leveldb.Options(), self.db_path, create_if_missing=True)
        self.assertEqual([0, 0, 0],
                         db.approximateDiskSizes(("a", "z"), ("0", "9"), ("A", "Z")))
        batch = leveldb.WriteBatch()
        for i in xrange(100):
            batch.Put("c%d" % i, os.urandom(4096))
        db.write(leveldb.WriteOptions(), batch, sync=True)
        db.close()
        db = self.db_class(leveldb.Options(), self.db_path)
        sizes = db.approximateDiskSizes(("0", "9"), ("A", "Z"), ("a", "z"))
        self.assertEqual(sizes[0], 0)
        self.assertEqual(sizes[1], 0)
        self.assertTrue(sizes[2] >= 4096 * 100)
        for i in xrange(10):
            db.Put(leveldb.WriteOptions(), "3%d" % i, os.urandom(10))
        db.close()
        db = self.db_class(leveldb.Options(), self.db_path)
        sizes = db.approximateDiskSizes(("A", "Z"), ("a", "z"), ("0", "9"))
        self.assertEqual(sizes[0], 0)
        self.assertTrue(sizes[1] >= 4096 * 100)
        self.assertTrue(sizes[2] < 4096 * 100)
        self.assertTrue(sizes[2] >= 10 * 10)
        db.close()


class MemLevelDBIteratorTest(LevelDBIteratorTestMixIn, unittest.TestCase):
    db_class = staticmethod(leveldb.MemoryDB)


def main():
    parser = argparse.ArgumentParser("run tests")
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()
    for _ in xrange(args.runs):
        unittest.main(argv=sys.argv[:1], exit=False)


if __name__ == "__main__":
    main()
