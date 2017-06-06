#!/usr/bin/python2.7
#
# setup_leveldb.py
#
# Compiles and install Minecraft Pocket Edtition binary support.
#
__author__ = "D.C.-G. 2017"
__version__ = "0.2.0"

import sys
import os
import platform

if sys.platform != "linux2":
    print "This script can't run on other platforms than Linux ones..."
    sys.exit(1)

bin_deps = ('gcc', 'g++', 'unzip', 'wget')

mojang_sources_url = "https://codeload.github.com/Mojang/leveldb-mcpe/zip/a056ea7c18dfd7b806d6d693726ce79d75543904"
jocopa3_sources_url = "https://github.com/jocopa3/leveldb-mcpe/archive/56bdd1f38dde7074426d85eab01a5c1c0b5b1cfe.zip"
zlib_sources_url = "https://github.com/madler/zlib/archive/4a090adef8c773087ec8916ad3c2236ef560df27.zip"

zlib_ideal_version = "1.2.10"
zlib_minimal_version = "1.2.8"

def check_bins(bins):
    print 'Searching for the binaries needed %s...'%repr(bins).replace("'", '')
    missing_bin = False 
    for name in bins:
        if os.system('which %s > /dev/null'%name):
            print '*** WARNING: %s not found.'%name
            missing_bin = True
    if missing_bin:
        a = raw_input('The binary dependencies are not satisfied. The build may fail.\nContinue [y/N]?')
        if a and a in 'yY':
            pass
        else:
            sys.exit()
    else:
        print 'All the needed binaries were found.'

# Picked from another project to find the lib and adapted to the need
import re
ARCH = {'32bit': '32', '64bit': '64'}[platform.architecture()[0]]
default_paths = ['/lib', '/lib32', '/lib64', '/usr/lib', '/usr/lib32','/usr/lib64', 
                 '/usr/local/lib', os.path.expanduser('~/.local/lib'), '.']

# Gather the libraries paths.
def get_lib_paths(file_name):
    paths = []
    if os.path.isfile(file_name):
        lines = [a.strip() for a in open(file_name).readlines()]
        for i, line in enumerate(lines):
            if not line.startswith('#') and line.strip():
                if line.startswith('include'):
                    line = line.split(' ', 1)[1]
                    if '*' in line:
                        pat = r"%s"%line.split(os.path.sep)[-1].replace('.', '\.').replace('*', '.*')
                        d = os.path.split(line)[0]
                        if os.path.isdir(d):
                            for n in os.listdir(d):
                                r = re.findall(pat, n)
                                if r:
                                    paths += [a for a in get_lib_paths(os.path.join(d, n)) if a not in paths]
                    else:
                        paths += [a for a in get_lib_paths(line) if not a in paths]
                elif not line in paths and os.path.isdir(line):
                    paths.append(line)
    return paths

def find_lib(lib_name, input_file='/etc/ld.so.conf'):
    paths = default_paths + get_lib_paths(input_file)

    arch_paths = []
    other_paths = []

    while paths:
        path = paths.pop(0)
        if ARCH in path:
            arch_paths.append(path)
        elif path.endswith('/lib'):
            arch_paths.insert(-1, path)
        else:
            other_paths.append(path)

    paths = arch_paths + other_paths
    found = None
    r = None
    ver = None
    name = lib_name
    hash_list = name.split('.')
    hash_list.reverse()
    idx = hash_list.index('so')
    i = 0

    while i <= idx and not found:
        for path in paths:
            if os.path.exists(path):
                for path, dirnames, filenames in os.walk(path):
                    if name in filenames:
                        found = os.path.join(path, name)
                        break
            if found:
                break
        i += 1
        name = name.rsplit('.', 1)[0]

    cur_dir = os.getcwd()
    os.chdir(path)
    if found:
        base_path = os.path.split(found)[0]
        while os.path.islink(found):
            found = os.readlink(found)
        if not found.startswith("/"):
            found = os.path.abspath(os.path.join(base_path, found))
        # Verify the architecture of the library
        inp, outp = os.popen2('file %s | grep "ELF %s"'%(found, ARCH))
        r = bool(outp.read())
        inp.close()
        outp.close()
        # If the architecture could not be check with library internal data, rely on the folder name.
        if os.path.split(found)[0] in arch_paths:
            r = True
        v = found.rsplit('.so.', 1)
        if len(v) == 2:
            ver = v[1]
    os.chdir(cur_dir)

    return found, r, ver

def get_sources(name, url):
    print "Downloading sources for %s"%name
    print "URL: %s"%url
    os.system("wget --no-check-certificate -O %s.zip %s"%(name, url))
    print "Unpacking %s"%name
    os.system("unzip -q %s.zip"%name)
    os.system("mv $(ls -d1 */ | egrep '{n}-') {n}".format(n=name))
    print "Cleaning archive."
    os.remove("%s.zip"%name)

def build_zlib():
    print "Building zlib..."
    os.system("./configure; make")

def build_leveldb(zlib):
    print "Building leveldb..."
    # Looks like the '-lz' option has to be changed...
    if zlib:
        data = open('Makefile').read()
        data = data.replace("LIBS += $(PLATFORM_LIBS) -lz", "LIBS += $(PLATFORM_LIBS) %s"%zlib)
        open("Makefile", "w").write(data)
    os.system("make")

def main():
    print "=" * 72
    print "Building Linux Minecraft Pocket Edition for MCEdit..."
    print "-----------------------------------------------------"
    force_zlib = False
    leveldb_source_url = mojang_sources_url
    cur_dir = os.getcwd()
    if "--force-zlib" in sys.argv:
        force_zlib = True
        sys.argv.remove("--force-zlib")
    if "--alt-leveldb" in sys.argv:
        leveldb_source_url = jocopa3_sources_url
    check_bins(bin_deps)
    # Get the sources here.
    get_sources("leveldb", leveldb_source_url)
    os.chdir("leveldb")
#     os.rmdir("zlib")
    get_sources("zlib", zlib_sources_url)
    os.chdir(cur_dir)
    zlib = (None, None, None)
    # Check zlib
    if not force_zlib:
        print "Checking zlib."
        zlib = find_lib("libz.so.%s"%zlib_ideal_version)
        print zlib
        if zlib == (None, None, None):
            zlib = None
            print "*** WARNING: zlib not found!"
            print "             It is recommended you install zlib v%s on your system or"%zlib_ideal_version
            print "             let this script install it only for leveldb."
            print "             Enter 'b' to build zlib v1.2.10 only for leveldb."
            print "             Enter 'a' to quit now and install zlib on your yourself."
            print "             It is recomended to use your package manager to install zlib."
            a = ""
            while a.lower() not in "abc":
                a = raw_input("Build zlib [b] or abort [a]? ")
            if a == "b":
                force_zlib = True
            elif a == "a":
                sys.exit(1)
        else:
            err = False
            if zlib[2] == None:
                print "*** WARNING: zlib has been found, but the exact version could not be"
                print "             determined."
                print "             The sources for zlib v%s will be downloaded and the"%zlib_ideal_version
                print "             build will start."
                print "             If the build fails or the support does not work, install"
                print "             the version %s and retry. You may also install another"%zlib_ideal_version
                print "             version and retry with this one."
                err = True
            elif zlib[2] not in ("1.2.8", "1.2.10"):
                print "*** WARNING: zlib was found, but its version is %s."%zlib[2]
                print "             You can try to build with this version, but it may fail,"
                print "             or the generated libraries may not work..."
                err = True

            if zlib[1] == False:
                print "*** WARNING: zlib has been found on your system, but not for the"
                print "             current architecture."
                print "             You apparently run on a %s, and the found zlib is %s"%(ARCH, zlib[0])
                print "             Building the Pocket Edition support may fail. If not,"
                print "             the support may not work."
                print "             You can continue, but it is recommended to install zlib"
                print "             for your architecture."
                err = True

            if err:
                a = raw_input("Continue [y/N]? ")
                if a and a in "yY":
                    zlib = zlib[0]
                else:
                    sys.exit(1)
            else:
                print "Found compliant zlib v%s."%zlib[2]

    if force_zlib:
        os.chdir("leveldb/zlib")
        build_zlib()
        os.chdir(cur_dir)
        os.rename("leveldb/zlib/libz.so.1.2.10", "./libz.so.1.2.10")
        os.rename("leveldb/zlib/libz.so.1", "./libz.so.1")
        os.rename("leveldb/zlib/libz.so", "./libz.so")
        # Tweak the leveldb makefile to force the linker to use the built zlib
        data = open("leveldb/Makefile").read()
        data = data.replace("PLATFORM_SHARED_LDFLAGS", "PSL")
        data = data.replace("LDFLAGS += $(PLATFORM_LDFLAGS)",
                            "LDFLAGS += $(PLATFORM_LDFLAGS)\nPSL = -L{d} -lz -Wl,-R{d} $(PLATFORM_SHARED_LDFLAGS)".format(d=cur_dir))
        data = data.replace("LIBS += $(PLATFORM_LIBS) -lz", "LIBS += -L{d} -lz -Wl,-R{d} $(PLATFORM_LIBS)".format(d=cur_dir))
        open("leveldb/Makefile", "w").write(data)

    os.chdir("leveldb")
    build_leveldb(zlib[0])
    os.chdir(cur_dir)
    os.rename("leveldb/libleveldb.so.1.18", "./libleveldb.so.1.18")
    os.rename("leveldb/libleveldb.so.1", "./libleveldb.so.1")
    os.rename("leveldb/libleveldb.so", "./libleveldb.so")
    print "Setup script ended."

if __name__ == "__main__":
    main()
