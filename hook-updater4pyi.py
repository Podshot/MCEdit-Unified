# hook for pyinstaller

import updater4pyi
import updater4pyi.util
import os.path


def locpath(x):
    return os.path.realpath(os.path.join(os.path.dirname(updater4pyi.__file__), x))


datas = [
    (locpath('cacert.pem'), 'updater4pyi'),
]

if updater4pyi.util.is_linux() or updater4pyi.util.is_macosx():
    datas += [
        (locpath('installers/unix/do_install.sh'), 'updater4pyi/installers/unix'),
    ]
elif updater4pyi.util.is_win():
    datas += [
        (locpath('installers/win/do_install.exe.zip'), 'updater4pyi/installers/win'),
    ]

# from hookutils import collect_data_files
#datas = collect_data_files('updater4pyi')
print "DATAS IS\n\t%r" % datas
