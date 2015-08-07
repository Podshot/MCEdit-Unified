# -*- mode: python -*-
# Build script for pyinstaller. Run using:
# $ pyinstaller mcedit.spec

import fnmatch
import os
import itertools

everything = []
for root, _, filenames in os.walk("."):
    for filename in fnmatch.filter(filenames, "*.py"):
        filepath = root if filename == "__init__.py" else os.path.join(root, filename)  # No .py

        components = filepath.split(os.path.sep)

        if "test" or "env" in components:
            continue

        modulename = ".".join(components)  # dotted modulename
        everything.append(modulename)

a = Analysis(['mcedit.py'],
             hiddenimports=everything,
             hookspath=['.'],
             runtime_hooks=None,
             excludes=None
             )

# Suppress pyconfig.h warning
# for d in a.datas:
#     if 'pyconfig' in d[0]:
#         a.datas.remove(d)
#         break

# a.binaries = a.binaries - TOC([
#     ('sqlite3.dll', '', ''),
#     ('_sqlite3', '', ''),
#     ('tcl85.dll', '', ''),
#     ('tk85.dll', '', ''),
#     ('_tkinter', '', ''),
# ])

data_extensions = [".yaml", ".json", ".png", ".trn", ".def", ".ttf"]

for root, __, filenames in os.walk("."):
    for filename in filenames:
        if "ENV" in root:
            continue
        for d in data_extensions:
            if filename.endswith(d):
                f = os.path.join(root, filename)
                a.datas.append([f, f, 'DATA'])
                break

print a.datas

pyz = PYZ(a.pure)

onefile = True

# Remove IPython html assets, saving 1.5MB.
# Disables using the embedded IPython for notebooks
# Anyone who wants this can run from source!

# a.datas = [(filename, path, filetype)
#            for filename, path, filetype in a.datas
#            if ipy_filter(filename)]

if onefile:
    a.scripts += a.binaries + a.zipfiles + a.datas

exe = EXE(pyz,
          a.scripts + [('i', '', 'OPTION')],
          exclude_binaries=not onefile,
          name='MCEdit Unified.exe',
          debug=True,
          strip=None,
          upx=False,
          console=True,
          icon="mcedit.ico")

if not onefile:
    coll = COLLECT(exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   strip=None,
                   upx=True,
                   name='MCEdit Unified')
