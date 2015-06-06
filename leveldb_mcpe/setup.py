from setuptools import setup
from distutils.extension import Extension
import os.path
import sys

extra_compile_args = ["-DDLLX="]
extra_link_args = []
define_macros = []
runtime_library_dirs = []
library_dirs = []
libraries = []
include_dirs = []

if sys.platform == "win32":
    if sys.maxsize > 2 ** 32:  # 64-bit
        print "Building windows application 'leveldb_mcpe' x64"
        include_dirs = ["C:/Boost/include/boost-1_55", "./leveldb-mcpe/include"]
        library_dirs = ["C:/Boost/lib/x64", "."]
        libraries = ["leveldb-mcpe", "shell32", "zlib"]
        extra_compile_args += ["/EHs", "/MD"]
        extra_link_args += ["/MACHINE:x64", "/NODEFAULTLIB:LIBCMT"]
        define_macros = [("WIN32", None), ("_WINDOWS", None), ("LEVELDB_PLATFORM_WINDOWS", None), ("OS_WIN", None)]
    else:  # 32-bit
        print "Building windows application 'leveldb_mcpe' x32"
        include_dirs = ["C:/Boost/include/boost-1_55", "./leveldb-mcpe/include"]
        library_dirs = ["C:/Boost/lib/i386", "."]
        libraries = ["leveldb-mcpe", "shell32", "zlib"]
        extra_compile_args += ["/EHs", "/MD"]
        extra_link_args += ["/MACHINE:x86", "/NODEFAULTLIB:LIBCMT"]
        define_macros = [("WIN32", None), ("_WINDOWS", None), ("LEVELDB_PLATFORM_WINDOWS", None), ("OS_WIN", None)]


elif sys.platform == "darwin":
    include_dirs = ["/usr/local/include/boost", "./leveldb-mcpe/include", "."]
    library_dirs = ["/usr/local/lib", ".", "./leveldb-mcpe"]
    libraries = ["boost_python", "leveldb"]

elif sys.platform == "linux2":
    print "Building Linux application 'leveldb_mcpe'..."

    # TODO: add checks, warnings and recomandations if something fails...

    # First, unpack and build dependencies: boost and mojang's leveldb-mcpe
    # Need make, g++, tar, unzip, Python 2.7 header files
    # boost will be intalled there to avoid elevation problems

    curdir = os.getcwd()
    destpath = '../pymclevel'
    user_libdir = os.path.expanduser('~/.local/lib')
    if not os.path.exists(user_libdir):
        print 'Creating needed library folder: %s' % user_libdir
        os.makedirs(user_libdir)
        print 'Done'
    mcpeso_dir = os.path.join(user_libdir, 'leveldb-mcpe')
    boostRoot = os.path.expanduser('~/.local/lib/boost_1_55_0_mcpe')
    install_boost = None
    build_boost_python = None
    if not os.path.exists(boostRoot):
        install_boost = True
    else:
        print 'Boost found in %s. Skipping installation.' % boostRoot
        install_boost = False
    if not os.path.exists(os.path.join(boostRoot, 'stage', 'lib', 'libboost_python.a')):
        build_boost_python = True
    else:
        print 'Boost Python wrapper found in %s. Skipping build.' % os.path.join(boostRoot, 'stage', 'lib')
        build_boost_python = False

    if install_boost is None:  # Shall not happen...
        print 'Impossible to determine if Boost 1.55.0 is installed in your personnal library folder.'
        a = raw_input('Do you want to (re)install it [y/N] ?')
        if a and a in 'yY':
            install_boost = True
    if build_boost_python is None:  # Shall not happen...
        print 'Impossible to determine if Boost Python wrapper is installed in your personnal library folder.'
        a = raw_input('Do you want to (re)install it [y/N] ?')
        if a and a in 'yY':
            build_boost_python = True

    if install_boost:
        print "Extracting boost..."
        os.system('tar --bzip2 -xf boost_1_55_0.tar.bz2')
        os.system('mv boost_1_55_0 %s' % boostRoot)
        os.chdir(boostRoot)
        print "Installing boost..."
        os.system('sh ./bootstrap.sh --prefix=%s' % boostRoot)
        os.chdir(curdir)
        print 'Done.'
    if build_boost_python:
        print "Building boost_python..."
        os.chdir(boostRoot)
        os.system('./b2 --with-python --prefix=%s --build-dir=%s -a link=static cxxflags="-fPIC" linkflags="-fPIC"' % (
            boostRoot, boostRoot))
        os.chdir(curdir)
        print 'Done.'

    # Unpack and build leveldb-mcpe from mojang
    build_leveldb = None
    # if not os.path.exists('leveldb-mcpe/libleveldb.a') and not os.path.exists('leveldb-mcpe/libleveldb.so'):
    if not os.path.exists('libleveldb.so'):
        build_leveldb = True
    # elif os.path.exists('leveldb-mcpe/libleveldb.a') and os.path.exists('leveldb-mcpe/libleveldb.so'):
    elif os.path.exists('libleveldb.so'):
        a = raw_input("Mojang's leveldb is already built. Rebuild [y/N] ?")
        if a and a in 'yY':
            build_leveldb = True
        else:
            build_leveldb = False
    else:
        not_exists = [os.path.basename(a) for a in ('libeveldb.a', 'libleveldb.so') if not os.path.exists(a)]
        print "The file %s is missing. Building MCEdit one may not work." % not_exists[0]
        a = raw_input("Rebuild Mojang's leveldb-mcpe [y/N] ?")
        if a and a in 'yY':
            build_leveldb = True

    if build_leveldb is None:  # Shall not happen...
        print "Impossible to determine if Mojang's leveldb-mcpe is already built or not..."
        a = raw_input('Do you want to (re)build it [y/N] ?')
        if a and a in 'yY':
            build_leveldb = True

    if build_leveldb:
        extract = True
        if os.path.exists('leveldb-mcpe'):
            a = raw_input("Mojang's leveldb-mcpe already exists. Replace it (reextract) [y/N] ?")
            if not a or a not in 'yY':
                extract = False

        if extract:
            os.system('rm -R leveldb-mcpe')
            print "Extracting Mojang's leveldb-mcpe..."
            os.system('unzip -q leveldb-mcpe-master.zip')
            os.system('mv leveldb-mcpe-master leveldb-mcpe')
            os.chdir('leveldb-mcpe')
            os.system('unzip -q ../zlib.zip')
            os.chdir('..')
        os.chdir('leveldb-mcpe')
        print "Building Mojang's leveldb-mcpe..."
        os.system('make')
        os.chdir(curdir)
        print 'Done.'
    else:
        print "Skipping Mojang's leveldb-mcpe build."
    if not os.path.exists(os.path.join(mcpeso_dir, 'libleveldb.so.1.18')):
        print 'Copying library to %s.' % mcpeso_dir
        if not os.path.exists(mcpeso_dir):
            os.makedirs(mcpeso_dir)
        os.system('cp ./leveldb-mcpe/libleveldb.so.1.18 %s' % mcpeso_dir)
        os.system('ln -s %s/libleveldb.so.1.18  %s/libleveldb.so.1' % (mcpeso_dir, mcpeso_dir))
        os.system('ln -s %s/libleveldb.so.1.18  %s/libleveldb.so' % (mcpeso_dir, mcpeso_dir))
        print 'Done.'

    # #1# This form compiles dynamic shared library
    # include_dirs = [boosRoot, './leveldb-mcpe/include', '.']
    # library_dirs = [boostRoot, boostRoot + '/stage/lib', '/usr/local/lib', '.', './leveldb-mcpe']
    # libraries = ['boost_python', 'leveldb']
    # define_macros = [("LINUX", None),("_DEBUG", None),("_LINUX", None),("LEVELDB_PLATFORM_POSIX", None)]
    # extra_compile_args = ['-std=c++11'] + extra_compile_args
    # runtime_library_dirs = ['.', './leveldb-mcpe']
    # Need to copy libboost_python.so.1.55.0 in the current directory and link it
    # os.system('cp %s/stage/lib/libboost_python.so.1.55.0 .|ln -s '
    #           'libboost_python.so.1.55.0 libboost_python.so' % boostRoot)

    # 2# Static library build: need a boost python libs built with cxxflags"-fPIC" and linkflags="-fPIC"
    include_dirs = [boostRoot, './leveldb-mcpe/include', '.']
    library_dirs = [boostRoot, boostRoot + '/stage/lib', '/usr/local/lib', '.', mcpeso_dir]
    libraries = ['boost_python', 'leveldb']
    define_macros = [("LINUX", None), ("_DEBUG", None), ("_LINUX", None), ("LEVELDB_PLATFORM_POSIX", None),
                     ('OS_LINUX', None)]
    extra_compile_args = ['-std=c++11'] + extra_compile_args
    runtime_library_dirs = [mcpeso_dir]

files = ["leveldb_mcpe.cpp"]

setup(name="leveldb_python_wrapper",
      ext_modules=[
          Extension(
              "leveldb_mcpe",
              files,
              library_dirs=library_dirs,
              libraries=libraries,
              include_dirs=include_dirs,
              depends=[],
              define_macros=define_macros,
              extra_compile_args=extra_compile_args,
              extra_link_args=extra_link_args,
              runtime_library_dirs=runtime_library_dirs)
      ]
      )

# Need to copy leveldb_mcpe.so in the current directory
if sys.platform == 'linux2':
    os.system('cp $(ls -R build/*/leveldb_mcpe.so) %s' % destpath)




