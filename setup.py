# from esky import bdist_esky
from setuptools import setup

import os
import sys
import glob
import subprocess
import platform

sys.path.append('C:\\WINDOWS\\WinSxS\\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.30729.4148_none_5090ab56bcba71c2')
sys.path.append("C:\\Program Files\\Microsoft Visual Studio 9.0\\VC\\redist\\x86\\Microsoft.VC90.CRT")

LONG_DESC = '''
World / Saved Game Editor for the popular game Minecraft

Import and export creations from saved games. Brush tools allow modifying
terrain on a larger scale. Create, remove, and regenerate chunks in modern
'infinite' Minecraft levels.

Works with saved games from Minecraft Classic, Indev, Infdev, Alpha, Beta,
Release, and Pocket Edition.
'''

'''if "--stable" in sys.argv:
    DEVELOP = False
    sys.argv.remove('--stable')
else:
    DEVELOP = True

def get_git_version():
    """
    Get the version from git.
    """
    if DEVELOP:
        match = '--match=*.*.*build*'
    else:
        match = '--match=*.*.*'

    try:
        version = subprocess.check_output('git describe --abbrev=4 --tags'.split() + [match]).strip()
    except:
        version = 'unknown'
    fout = open('RELEASE-VERSION', 'wb')
    fout.write(version)
    fout.write('\n')
    fout.close()
    fout = open('GIT-COMMIT', 'wb')

    try:
        commit = subprocess.check_output('git rev-parse HEAD'.split()).strip()
    except:
        commit = 'unknown'
    fout.write(commit)
    fout.write('\n')
    fout.close()

    return version
'''

# setup() options that are common on all platforms.
SETUP_COMMON = {
    # General fields,
    'name': 'MCEdit',  #if DEVELOP else 'MCEdit',
    'version': 'V1.0.0 Dev',
    'description': 'Minecraft World Editor',
    'long_description': LONG_DESC,

    'author': 'David Vierra and the minecraft community',
    'author_email': 'codewarrior0@gmail.com',

    'url': 'http://www.mcedit.net/',

    # PyPi,
    'keywords': 'minecraft world editor',
    'classifiers': [
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
    ],

    # Building,
    'packages': [
        'pymclevel',
    ],
    'package_data': {
        'pymclevel': [
            '*.yaml',
            '*.txt',
            '_nbt.*'
        ],
        'filters': [
            'stock-filters/**'
        ],
        'stock-schematics': [
            'stock-schematics/**'
        ]
    },
    'scripts': [
        'mcedit.py'
    ]
}

ESKY_OPTIONS = {
    'bdist_esky': {
        'includes': [
            'ctypes',
            'logging',
            'OpenGL.arrays.*',
            'OpenGL.platform',
            'OpenGL.platform.win32',
            'encodings'
        ],
        'excludes': [
            'Tkconstants',
            'Tkinter',
            'tcl',
            'Cython'
        ],
        'freezer_options': {
            # py2exe extras
            'optimize': 2,
            'compressed': True,
            'bundle_files': 3,
            'dll_excludes': [
                'mswsock.dll',
                'powrprof.dll'
            ],
            # py2app extras
            'iconfile': 'mcedit.icns',
            'plist': {
                'CFBundleIdentifier': 'net.mcedit.mcedit'
            }
        }
    }
}


def build_nbt():
    """
    Builds _nbt.py.
    """
    os.chdir('pymclevel')
    os.system(sys.executable + ' setup.py build_ext --inplace --force')
    os.chdir('..')


def setup_win32():
    """
    Packing setup for Windows 32/64.
    """
    import py2exe

    # This little ditty makes sure the font module is available
    origIsSystemDLL = py2exe.build_exe.isSystemDLL

    def isSystemDLL(pathname):
        if os.path.basename(pathname).lower() in ['sdl_ttf.dll']:
            return 0
        return origIsSystemDLL(pathname)

    py2exe.build_exe.isSystemDLL = isSystemDLL


def get_data_files(dirs):
    """
    Recursively include data directories.
    """
    results = []
    for directory in dirs:
        for root, dirs, files in os.walk(directory):
            files = [os.path.join(root, file_) for file_ in files]
            results.append((root, files))
    return results


def main():
    build_nbt()
    if platform.system() == 'Windows':
        setup_win32()

    include_dirs = ['fonts', 'toolicons', 'stock-schematics', 'filters']
    data_files = get_data_files(include_dirs) + [
        ('', [
            'README.md',
            'favicon.png',
            'terrain-classic.png',
            'terrain-pocket.png',
            'char.png',
            'gui.png',
            'terrain.png',
            'TRANSLATION.txt',
            #'RELEASE-VERSION',
            #'GIT-COMMIT',
        ])
    ]

    setup(
        data_files=data_files,
        # options=ESKY_OPTIONS,
        # **SETUP_COMMON
        windows=['mcedit.py'],
        options={
            "py2exe": {
                "includes": ["ctypes", "logging", "OpenGL"],
                # "excludes": ["OpenGL"]
                "excludes": []
            }
        }
    )

    #os.unlink('RELEASE-VERSION')
    #os.unlink('GIT-COMMIT')


if __name__ == '__main__':
    main()
