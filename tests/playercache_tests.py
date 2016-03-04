import unittest
import os
import atexit
from version_utils import PlayerCache

ASSERT_CONTENTS = True

cache = PlayerCache()
cache.load(os.path.abspath(__file__).replace("playercache_tests", "new_cache").replace(".pyc", ".json").replace(".py", ".json"))
        
class NewPlayerDataTest(unittest.TestCase):
    
    def setUp(self):
        self.cache = cache
        print os.path.abspath(__file__).replace("playercache_tests", "new_cache").replace(".pyc", ".json").replace(".py", ".json")
        atexit.register(self.cache.save)
        
    def testGetPlayerDataWithName(self):
        result = self.cache.getPlayerInfo("Podshot", force=True)
        self.assertIsInstance(result, tuple)
        if ASSERT_CONTENTS:
            self.assertEqual(result, ("11d0102c-4178-4953-9175-09bbd7d46264", "Podshot", "11d0102c41784953917509bbd7d46264"))
        
    def testGetPlayerDataWithUUID(self):
        result = self.cache.getPlayerInfo("11d0102c-4178-4953-9175-09bbd7d46264", force=True)
        self.assertIsInstance(result, tuple)
        if ASSERT_CONTENTS:
            self.assertEqual(result, ("11d0102c-4178-4953-9175-09bbd7d46264", "Podshot", "11d0102c41784953917509bbd7d46264"))
        
    def testNameInCache(self):
        result = self.cache.nameInCache("Podshot")
        self.assertTrue(result)
    
    def testUUIDInCache(self):
        result = self.cache.UUIDInCache("11d0102c-4178-4953-9175-09bbd7d46264")
        self.assertTrue(result)
        
    def testPlayerSkinWithUUID(self):
        result = self.cache.getPlayerSkin("11d0102c-4178-4953-9175-09bbd7d46264", force_download=True)
        self.assertIsInstance(result, str)
        if ASSERT_CONTENTS:
            self.assertEqual(result, "player-skins\\11d0102c_4178_4953_9175_09bbd7d46264.png")
        
        # Should equal 'char.png' due to the download being forced and time between the requests being under than 1 minute
        result = self.cache.getPlayerSkin("11d0102c-4178-4953-9175-09bbd7d46264", force_download=True)
        self.assertIsInstance(result, str)
        if ASSERT_CONTENTS:
            self.assertEqual(result, "char.png")
        
        result = self.cache.getPlayerSkin("11d0102c-4178-4953-9175-09bbd7d46264", force_download=False)
        self.assertIsInstance(result, str)
        if ASSERT_CONTENTS:
            self.assertEqual(result, "player-skins\\11d0102c_4178_4953_9175_09bbd7d46264.png")
        