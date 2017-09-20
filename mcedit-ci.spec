# -*- mode: python -*-

import sys
import glob
import os
import shutil
import json
import subprocess

block_cipher = None

SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"

replace_map = {
    "mcedit.ini": "mcedit_testing.ini",
    "usercache.json": "usercache_testing.ini"
}

if os.environ.get('MCEDIT_BUILD_VERSION'):
    VERSION = os.environ.get('MCEDIT_BUILD_VERSION')
else:
    VERSION = "1.6.0.0-testing"

fp = open('directories.py', 'rb')
data = fp.read();
fp.close()

with open('directories.py', 'wb') as out:
    new_data = data
    for (key, value) in replace_map.iteritems():
        new_data = new_data.replace(key, value)
    out.write(new_data)

subprocess.check_call([sys.executable, 'setup.py', 'all'])

a = Analysis(['mcedit.py'],
             pathex=['C:\\Users\\gotharbg\\Documents\\Python Projects\\MCEdit-Unified'],
             binaries=[],
             datas=[],
             hiddenimports=['pkg_resources'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='mcedit',
          debug=False,
          strip=False,
          upx=True,
          console=True , icon='mcedit.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='mcedit')

files = glob.glob(r".\\*.json") + glob.glob(r'.\\*.png') + glob.glob(r'.\\*.fot') + glob.glob(r'.\\*.def')
for f in files:
    shutil.copy(f, os.path.join('.', 'dist', 'mcedit', f))

os.mkdir(os.path.join('.', 'dist', 'mcedit', 'pymclevel'))
pymclevel_files = glob.glob(os.path.join('.', 'pymclevel', '*.json'))
for f in pymclevel_files:
    shutil.copy(f, os.path.join('.', 'dist', 'mcedit', 'pymclevel', os.path.basename(f)))

shutil.copytree(os.path.join('.', 'Items'), os.path.join('.', 'dist', 'mcedit', 'Items'))
shutil.copytree(os.path.join('.', 'item-textures'), os.path.join('.', 'dist', 'mcedit', 'items-textures'))
shutil.copytree(os.path.join('.', 'toolicons'), os.path.join('.', 'dist', 'mcedit', 'toolicons'))
shutil.copytree(os.path.join('.', 'lang'), os.path.join('.', 'dist', 'mcedit', 'lang'))
shutil.copytree(os.path.join('.', 'mcver'), os.path.join('.', 'dist', 'mcedit', 'mcver'))
shutil.copytree(os.path.join('.', 'fonts'), os.path.join('.', 'dist', 'mcedit', 'fonts'))
shutil.copytree(os.path.join('.', 'stock-brushes'), os.path.join('.', 'dist', 'mcedit', 'stock-brushes'))
shutil.copytree(os.path.join('.', 'stock-filters'), os.path.join('.', 'dist', 'mcedit', 'stock-filters'))
shutil.copytree(os.path.join('.', 'stock-schematics'), os.path.join('.', 'dist', 'mcedit', 'stock-schematics'))

shutil.copy(os.path.join('.', 'pymclevel', 'LevelDB-MCPE.dll'), os.path.join('.', 'dist', 'mcedit', 'pymclevel', 'LevelDB-MCPE.dll'))

fp = open(os.path.join('.', 'dist', 'mcedit', 'RELEASE-VERSION.json'),'rb')
version_data = json.load(fp)
fp.close()

version_data["tag_name"] = VERSION

fp = open(os.path.join('.', 'dist', 'mcedit', 'RELEASE-VERSION.json'), 'wb')
json.dump(version_data, fp)
fp.close()

with open('directories.py', 'wb') as out:
    out.write(data)

subprocess.check_call([
    SEVENZIP,
    'a',
    'mcedit-unified-{}.zip'.format(VERSION),
    os.path.join('.', 'mcedit', '*')
    ],
    cwd='dist')
