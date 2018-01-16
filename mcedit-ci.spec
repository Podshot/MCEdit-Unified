# -*- mode: python -*-

import sys
sys.modules['FixTk'] = None

import glob
import os
import shutil
import json
import subprocess

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

block_cipher = None

SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"

replace_map = {
    "mcedit.ini": "mcedit_testing.ini",
    "usercache.json": "usercache_testing.ini"
}

if os.environ.get('APPVEYOR_BUILD_VERSION'):
    VERSION = os.environ.get('APPVEYOR_BUILD_VERSION')
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
             binaries=[], # ('./ENV/Lib/site-packages/OpenGL/DLLS/freeglut64.vc9.dll', 'freeglut64.vc9.dll'),
             datas=[],
             hiddenimports=['pkg_resources', 'PyOpenGL', 'PyOpenGL_accelerate', 'OpenGL', 'OpenGL_accelerate', 'OpenGL.platform.win32'],
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['Tkinter', 'tkinter', '_tkinter', 'Tcl', 'tcl', 'Tk', 'tk', 'wx', 'FixTk'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

datas = []
base_files = glob.glob(r".\\*.json") + glob.glob(r'.\\*.png') + glob.glob(r'.\\*.fot') + glob.glob(r'.\\*.def') + [os.path.join('.', 'LICENSE.txt'),]
for f in base_files:
    datas.append((os.path.basename(f), os.path.abspath(f), 'DATA'))

pymclevel_files = collect_data_files('pymclevel')
pymclevel_files = [(os.path.join(dest, os.path.basename(src)), src, 'DATA') for src, dest in pymclevel_files]
datas += pymclevel_files

misc_files = walk('fonts') + walk('item-textures') + walk('Items') + walk('lang') + walk('mcver') + walk('stock-filters')
misc_files += walk('stock-brushes') + walk('stock-schematics') + walk('toolicons')
misc_files = set([(os.path.join(dest, os.path.basename(src)), src, 'DATA') for src, dest in misc_files])
datas += misc_files

a.datas.extend(datas)

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

fp = open(os.path.join('.', 'dist', 'mcedit', 'RELEASE-VERSION.json'),'rb')
version_data = json.load(fp)
fp.close()

version_data["tag_name"] = VERSION

fp = open(os.path.join('.', 'dist', 'mcedit', 'RELEASE-VERSION.json'), 'wb')
json.dump(version_data, fp)
fp.close()

with open('directories.py', 'wb') as out:
    out.write(data)

subprocess.check_call(['git', 'clone', 'https://github.com/Podshot/MCEdit-Unified-Preview.git'])

if str(os.environ.get('WHL_ARCH')) == '32' or not sys.maxsize > 2**32:
    shutil.copy(os.path.join('.', 'MCEdit-Unified-Preview', 'freeglut32.vc9.dll'), os.path.join('.', 'dist', 'mcedit', 'freeglut32.dll'))
    VERSION += '-win32'
elif str(os.environ.get('WHL_ARCH')) == '_amd64' or sys.maxsize > 2**32:
    shutil.copy(os.path.join('.', 'MCEdit-Unified-Preview', 'freeglut64.vc9.dll'), os.path.join('.', 'dist', 'mcedit', 'freeglut64.dll'))
    VERSION += '-win64'

subprocess.check_call([
    SEVENZIP,
    'a',
    'mcedit-unified-{}.zip'.format(VERSION),
    os.path.join('.', 'mcedit', '*')
    ],
    cwd='dist')
