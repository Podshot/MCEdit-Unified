# -*- mode: python -*-

import os
import sys
sys.modules['FixTk'] = None

import subprocess
import shutil
import glob
import json

try:
    from PyInstaller.utils.hooks import collect_data_files, remove_prefix
except ImportError:
    from PyInstaller.hooks.hookutils import collect_data_files, remove_prefix

def walk(directory):
    files = []
    for path, subdirs, ffiles in os.walk(directory):
        for name in ffiles:
            src = os.path.abspath(os.path.join(path, name))
            dest = remove_prefix(path, os.path.abspath(os.getcwdu()))
            files.append((src, dest.replace('./','')))
    return files

replace_map = {
    "mcedit.ini": "mcedit_testing.ini",
    "usercache.json": "usercache_testing.ini"
}

if os.environ.get('APPVEYOR_BUILD_VERSION'):
    VERSION = os.environ.get('APPVEYOR_BUILD_VERSION')
else:
    VERSION = "1.6.0.0-testing"

fp = open(os.path.join('.', 'RELEASE-VERSION.json'),'rb')
version_data = json.load(fp)
fp.close()

version_data["tag_name"] = VERSION

fp = open(os.path.join('.', 'RELEASE-VERSION.json'), 'wb')
json.dump(version_data, fp)
fp.close()

fp = open('directories.py', 'rb')
data = fp.read();
fp.close()

with open('directories.py', 'wb') as out:
    new_data = data
    for (key, value) in replace_map.iteritems():
        new_data = new_data.replace(key, value)
    out.write(new_data)

block_cipher = None


a = Analysis(['mcedit.py'],
             pathex=['/Users/travis/build/Podshot/Travis-Ci-OSX-Testing'],
             binaries=[],
             datas=[],
             hiddenimports=['pkg_resources', 'PyOpenGL', 'PyOpenGL_accelerate', 'OpenGL', 'OpenGL_accelerate'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['Tkinter', 'tkinter', '_tkinter', 'Tcl', 'tcl', 'Tk', 'tk', 'wx', 'FixTk'],
             cipher=block_cipher)

datas = []
base_files = glob.glob(r".\\*.json") + glob.glob(r'.\\*.png') + glob.glob(r'.\\*.fot') + glob.glob(r'.\\*.def') + [os.path.join('.', 'LICENSE.txt'),]
for f in base_files:
    datas.append((os.path.basename(f), os.path.abspath(f), 'DATA'))

pymclevel_files = collect_data_files('pymclevel')
pymclevel_files = [(os.path.join(dest, os.path.basename(src)), src, 'DATA') for src, dest in pymclevel_files]
datas += pymclevel_files

misc_files = walk('fonts') + walk('item-textures') + walk('Items') + walk('lang') + walk('mcver') + walk('stock-filters')
misc_files += walk('stock-brushes') + walk('stock-schematics') + walk('toolicons') + walk('splashes')
misc_files = set([(os.path.join(dest, os.path.basename(src)), src, 'DATA') for src, dest in misc_files])
datas += misc_files

a.datas.extend(datas)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
#          a.binaries,
#          a.zipfiles,
#          a.datas,
          exclude_binaries=True,
          name='mcedit',
          debug=True,
          strip=None,
          upx=False,
          runtime_tmpdir=None,
          console=True,
          icon='mcedit.icns')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='mcedit')

app = BUNDLE(coll,
             name='mcedit-unified.app',
             icon='mcedit.icns',
             bundle_identifier='net.mcedit-unified.mcedit-unified')