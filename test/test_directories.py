import logging
import sys

logger = logging.getLogger(__name__)

import os
import unittest
import time
t = time.time()
import directories
t = time.time() - t


class MyTestCase(unittest.TestCase):
    RESET_TO_OLD_DIRS = True

    """
    Tests basic behavior of directories.py
    Since directories can technically be empty, some tests may fail
    while they do in fact work.
    """
    def test_import_speed(self):
        self.assertTrue(t < 0.1)

    def test_get_data_dir(self):
        folder = directories.getDataDirectory()
        files = os.listdir(folder)
        if not(all([f in files for f in ["terrain.png", "bo3.def", "mcedit.ico"]])):
            self.fail("Unable to identify data directory at %s." % folder)

    def test_get_minecraft_launcher_directory(self):
        folder = directories.getMinecraftLauncherDirectory()
        if os.path.isdir(folder):
            if not ("versions" in os.listdir(folder) and "assets" in os.listdir(folder)):
                self.fail("Unable to identify minecraft launcher directory at %s." % folder)

    def test_get_minecraft_profile_json(self):
        json = directories.getMinecraftProfileJSON()
        assert (json is not None or not os.path.isfile(os.path.join(directories.getMinecraftLauncherDirectory(),
                                                       "launcher_profiles.json")))

    def test_get_selected_profile(self):
        profile = directories.getSelectedProfile()
        assert(profile in directories.getMinecraftProfileJSON()['profiles'])

    def test_minecraft_save_file_directory(self):
        folder = directories.getMinecraftSaveFileDirectory()
        a = False
        for d in os.listdir(folder):
            if os.path.isdir(os.path.join(folder, d)):
                for f in os.listdir(os.path.join(folder, d)):
                    if f == 'level.dat':
                        a = True
                        break
        if not a:
            self.fail("Unable to identify minecraft save directory at %s" % folder)

    def test_minecraft_profile_directory(self):
        folder = directories.getMinecraftProfileDirectory(directories.getSelectedProfile())
        assert (folder == directories.getMinecraftLauncherDirectory())

    def test_rename_legacy(self):
        u = os.path.expanduser
        if sys.platform == 'win32':
            self.skipTest("Can't rename legacy dirs on windows.")
        elif sys.platform == 'darwin':
            if not os.path.exists(u(u"~/Library/Application Support/pymclevel")):
                if not os.path.exists(u(u"~/Library/Application Support/MCEdit")):
                    self.skipTest("Can't found any MCEdit data files")
                else:
                    self.skipTest("MCEdit data files already renamed.")
            else:
                directories._mceditdirs._renameLegacyDirs()
                assert not os.path.exists(u(u"~/Library/Application Support/pymclevel"))
                assert os.path.exists(u(u"~/Library/Application Support/MCEdit"))
        else:  # Linux etc.
            if not os.path.exists(u(u"~/.pymclevel")):
                if not os.path.exists(u"~/.mcedit"):
                    self.skipTest("Can't found any MCEdit data files")
                else:
                    self.skipTest("MCEdit data files already renamed.")
            else:
                directories._mceditdirs._renameLegacyDirs()
                assert not os.path.exists(u(u"~/.pymclevel"))
                assert os.path.exists(u(u"~/.mcedit"))

    def test_config_files(self):
        folders = (directories.getFiltersDirectory(),
                   directories.getSchematicsDirectory(),
                   directories.getJarStorageDirectory(),
                   directories.getBrushesDirectory(),
                   directories.getUserCacheFilePath())
        folder_list = map(os.path.dirname, folders)
        assert all(folder_list[0] == folder for folder in folder_list)

    def test_portable_non_portable(self):
        if directories.isPortable():
            directories.goFixed()
            assert not directories.isPortable()
            directories.goPortable()
            assert directories.isPortable()
        else:
            directories.goPortable()
            assert directories.isPortable()
            directories.goFixed()
            assert not directories.isPortable()

    @classmethod
    def tearDownClass(cls):
        if cls.RESET_TO_OLD_DIRS:
            u = os.path.expanduser
            if sys.platform == 'darwin':
                if os.path.exists(u(u"~/Library/Application Support/MCEdit")):
                    os.rename(u(u"~/Library/Application Support/MCEdit"),
                              u(u"~/Library/Application Support/pymclevel"))
            elif sys.platform != 'win32':  # Linux etc.
                if os.path.exists(u(u"~/.mcedit")):
                    os.rename(u(u"~/.mcedit"),
                              u(u"~/.pymclevel"))


if __name__ == '__main__':
    unittest.main()
