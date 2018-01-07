#!/usr/bin/python2.7
#
# setup_leveldb.py
#
# Compiles and installs Minecraft Pocket Edtition binary support.
#
__author__ = "D.C.-G. 2017"
__version__ = "0.4.0"

import sys
import os
import platform
import fnmatch
import re

if sys.platform != "linux2":
    print "This script can't run on other platforms than Linux ones..."
    sys.exit(1)

bin_deps = ('gcc', 'g++', 'unzip', 'wget|curl')

wget_curl = None
wget_cmd = "wget -q --no-check-certificate -O"
curl_cmd = "curl -LskS -o"

leveldb_mojang_sources_url = "https://codeload.github.com/Mojang/leveldb-mcpe/zip/"
leveldb_mojang_commit = "5722a489c0fabf70f7bb36f70adc2ac70ff90377"
# leveldb_other_sources_url = "https://codeload.github.com/jocopa3/leveldb-mcpe/zip/"
# leveldb_other_commit = "56bdd1f38dde7074426d85eab01a5c1c0b5b1cfe"
leveldb_other_sources_url = "https://codeload.github.com/LaChal/leveldb-mcpe/zip/"
leveldb_other_commit = "9191f0499cd6d71e4e08c513f3a331a1ffe24332"
zlib_sources_url = "https://codeload.github.com/madler/zlib/zip/"
zlib_commit = "4a090adef8c773087ec8916ad3c2236ef560df27"

zlib_ideal_version = "1.2.8"
zlib_minimum_version = "1.2.8"
zlib_supported_versions = (zlib_minimum_version, zlib_ideal_version, "1.2.10")

silent = False


def check_bins(bins):
    print 'Searching for the needed binaries %s...' % repr(bins).replace("'", '')
    missing_bin = False 
    for name in bins:
        names = []
        if '|' in name:
            names = name.split('|')
        if names:
            found = False
            for n in names:
                if not os.system('which %s > /dev/null' % n):
                    found = True
                    break
                else:
                    print "Could not find %s." % n
            if found:
                g_keys = globals().keys()
                g_name = name.replace('|', '_')
                print "g_name", g_name, g_name in g_keys
                if g_name in g_keys:
                    globals()[g_name] = globals()['%s_cmd' % n]
            else:
                print '*** WARNING: None of these binaries were found on your system: %s.'%', '.join(names)
        else:
            if os.system('which %s > /dev/null' % name):
                print '*** WARNING: %s not found.' % name
                missing_bin = True
    if missing_bin:
        if not silent:
            a = raw_input('The binary dependencies are not satisfied. The build may fail.\nContinue [y/N]?')
        else:
            a = 'n'
        if a and a in 'yY':
            pass
        else:
            sys.exit(1)
    else:
        print 'All the needed binaries were found.'


# Picked from another project to find the lib and adapted to the need
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
                        pat = r"%s" % line.split(os.path.sep)[-1].replace('.', '\.').replace('*', '.*')
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
            arch_paths.insert(0, path)
        elif path.endswith('/lib'):
            arch_paths.append(path)
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
            print "Scanning %s for %s" % (path, name)
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
        inp, outp = os.popen2('file %s | grep "ELF %s"' % (found, ARCH))
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
    print "Downloading sources for %s" % name
    print "URL: %s" % url
    os.system("%s %s.zip %s" % (wget_curl, name, url))
    print "Unpacking %s" % name
    os.system("unzip -q %s.zip" % name)
    os.system("mv $(ls -d1 */ | egrep '{n}-') {n}".format(n=name))
    print "Cleaning archive."
    os.remove("%s.zip" % name)


def build_zlib():
    print "Building zlib..."
    return os.WEXITSTATUS(os.system("./configure; make"))


# Bad and dirty, but working untill Mojang implement this (or like): code injection
# directly into the sources before compilation.
# As an alternative to this, you may prefer to run this script with the '--alt-leveldb'
# CLI option, since the other repository don't need this code injection.
before = 0
after = 1
c_inject = {
    "c.h": {
        # The hook to look for code injection.
        "hook": """
extern void leveldb_options_set_compression(leveldb_options_t*, int);
""",
        # The data to be injected.
        "data": """
extern void leveldb_options_set_compressor(leveldb_options_t*, int, int);
""",
        # Where to inject the data: after the "hook" or before it.
        "where": after
    },

    "c.cc": {
        "hook": """
void leveldb_options_set_compression(leveldb_options_t* opt, int t) {
""",
        "data": """
void leveldb_options_set_compressor(leveldb_options_t* opt, int i, int t) {
  switch(t) {
    case 0:
      opt->rep.compressors[i] = nullptr;
      break;
#ifdef SNAPPY
    case leveldb_snappy_compression:
      opt->rep.compressors[i] = new leveldb::SnappyCompressor();
      break;
#endif
    case leveldb_zlib_compression:
      opt->rep.compressors[i] = new leveldb::ZlibCompressor();
      break;
    case leveldb_zlib_raw_compression:
      opt->rep.compressors[i] = new leveldb::ZlibCompressorRaw();
      break;
  }
}
""",
        "where": before
    }
}

def build_leveldb(zlib):
    print "Building leveldb..."

    # Inject the needed code into the sources.
    for root, d_names, f_names in os.walk("."):
        for f_name in fnmatch.filter(f_names, "c.[ch]*"):
            if f_name in c_inject.keys():
                hook = c_inject[f_name]["hook"]
                data = c_inject[f_name]["data"]
                where = c_inject[f_name]["where"]
                with open(os.path.join(root, f_name), "r+") as fd:
                    f_data = fd.read()
                    if data not in f_data:
                        if where == before:
                            c_data = "\n".join((data, hook))
                        else:
                            c_data = "\n".join((hook, data))
                        fd.seek(0)
                        fd.write(f_data.replace(hook, c_data))

    if zlib:
        with open("Makefile", "r+") as f:
            # If '-lz' is specified, we *may* need to specify the full library path. Just force it to be sure.
            data = f.read().replace("LIBS += $(PLATFORM_LIBS) -lz", "LIBS += $(PLATFORM_LIBS) %s" % zlib)
            # All the same if a path is specified, we need the one we found here. (SuSE don't have a /lib/x64_86-linux-gnu directory.)
            data = data.replace("LIBS += $(PLATFORM_LIBS) /lib/x86_64-linux-gnu/libz.so.1.2.8", "LIBS += $(PLATFORM_LIBS) %s" % zlib)
            f.seek(0)
            f.write(data)
    cpath = os.environ.get("CPATH")
    if cpath:
        os.environ["CPATH"] = ":".join(("./zlib", cpath))
    else:
        os.environ["CPATH"] = "./zlib"
    return os.WEXITSTATUS(os.system("make"))

def request_zlib_build():
    print "             Enter 'b' to build zlib v%s only for leveldb." % zlib_ideal_version
    print "             Enter 'a' to quit now and install zlib yourself."
    print "             Enter 'c' to continue."
    a = ""
    if not silent:
        while a.lower() not in "abc":
            a = raw_input("Build zlib [b], abort [a] or continue [c]? ")
    else:
        a = "a"
    if a == "b":
        return True
    elif a == "a":
        sys.exit(1)
    elif a == "c":
        return None

def main():
    print "=" * 72
    print "Building Linux Minecraft Pocket Edition for MCEdit..."
    print "-----------------------------------------------------"
    global leveldb_commit
    global zlib_commit
    global zlib_sources_url
    global silent
    global zlib_ideal_version
    force_zlib = False
    leveldb_source_url = leveldb_mojang_sources_url
    leveldb_commit = leveldb_mojang_commit
    cur_dir = os.getcwd()
    if "--force-zlib" in sys.argv:
        force_zlib = True
        sys.argv.remove("--force-zlib")
    if "--alt-leveldb" in sys.argv:
        leveldb_source_url = leveldb_other_sources_url
        leveldb_commit = leveldb_other_commit
    for arg, var in (("--leveldb-source-url", "leveldb_source_url"),
                     ("--leveldb-commit", "leveldb_commit"),
                     ("--zlib-source-url", "zlib_source_url"),
                     ("--zlib-commit", "zlib_commit")):
        if arg in sys.argv:
            globals()[var] = sys.argv[sys.argv.index(arg) + 1]
    leveldb_source_url += leveldb_commit
    zlib_sources_url += zlib_commit
    if "--silent" in sys.argv:
        silent = True

    if "--debug-cenv" in sys.argv:
        print 'CPATH:', os.environ.get('CPATH', 'empty!')
        print 'PATH:', os.environ.get('PATH', 'empty!')
        print 'LD_LIBRARY_PATH', os.environ.get('LD_LIBRARY_PATH', 'empty!')
        print 'LIBRARY_PATH', os.environ.get('LIBRARY_PATH', 'empty!')

    check_bins(bin_deps)
    # Get the sources here.
    get_sources("leveldb", leveldb_source_url)
    os.chdir("leveldb")
    get_sources("zlib", zlib_sources_url)
    os.chdir(cur_dir)
    zlib = (None, None, None)
    # Check zlib
    if not force_zlib:
        print "Checking zlib."
        zlib = find_lib("libz.so.%s" % zlib_ideal_version)
        print zlib
        if zlib == (None, None, None):
            zlib = None
            print "*** WARNING: zlib not found!"
            print "             It is recommended you install zlib v%s on your system or" % zlib_ideal_version
            print "             let this script install it only for leveldb."
            force_zlib = request_zlib_build()
        else:
            if zlib[2] == None:
                print "*** WARNING: zlib has been found, but the exact version could not be"
                print "             determined."
                print "             It is recommended you install zlib v%s on your system or" % zlib_ideal_version
                print "             let this script install it only for leveldb."
                force_zlib = request_zlib_build()
            elif zlib[2] not in zlib_supported_versions:
                print "*** WARNING: zlib was found, but its version is %s." % zlib[2]
                print "             You can try to build with this version, but it may fail,"
                print "             or the generated libraries may not work..."
                force_zlib = request_zlib_build()

            if zlib[1] == False:
                print "*** WARNING: zlib has been found on your system, but not for the"
                print "             current architecture."
                print "             You apparently run on a %s, and the found zlib is %s" % (ARCH, zlib[0])
                print "             Building the Pocket Edition support may fail. If not,"
                print "             the support may not work."
                print "             You can continue, but it is recommended to install zlib."
                force_zlib = request_zlib_build()

            if force_zlib is None:
                print "Build continues with zlib v%s" % zlib[2]
            else:
                print "Found compliant zlib v%s." % zlib[2]
            zlib = zlib[0]

    if force_zlib:
        os.chdir("leveldb/zlib")
        r = build_zlib()
        if r:
            print "Zlib build failed."
            return r
        os.chdir(cur_dir)
        os.rename("leveldb/zlib/libz.so.1.2.10", "./libz.so.1.2.10")
        os.rename("leveldb/zlib/libz.so.1", "./libz.so.1")
        os.rename("leveldb/zlib/libz.so", "./libz.so")
        for root, d_names, f_names in os.walk("leveldb"):
            for f_name in fnmatch.filter(f_names, "libz.so*"):
                os.rename(os.path.join(root, f_name), os.path.join(".", f_name))

        # Tweak the leveldb makefile to force the linker to use the built zlib
        with open("leveldb/Makefile", "r+") as f:
            data = f.read()
            data = data.replace("PLATFORM_SHARED_LDFLAGS", "PSL")
            data = data.replace("LDFLAGS += $(PLATFORM_LDFLAGS)",
                                "LDFLAGS += $(PLATFORM_LDFLAGS)\nPSL = -L{d} -lz -Wl,-R{d} $(PLATFORM_SHARED_LDFLAGS)".format(d=cur_dir))
            data = data.replace("LIBS += $(PLATFORM_LIBS) -lz", "LIBS += -L{d} -lz -Wl,-R{d} $(PLATFORM_LIBS)".format(d=cur_dir))
            f.seek(0)
            f.write(data)
            
        zlib = None

    os.chdir("leveldb")
    r = build_leveldb(zlib)
    if r:
        print "PE support build failed."
        return r
    os.chdir(cur_dir)
    for root, d_names, f_names in os.walk("leveldb"):
        for f_name in fnmatch.filter(f_names, "libleveldb.so*"):
            os.rename(os.path.join(root, f_name), os.path.join(".", f_name))
    print "Setup script ended."

if __name__ == "__main__":
    sys.exit(main())
