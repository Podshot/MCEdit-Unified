from setuptools import setup
from distutils.extension import Extension
import os.path
import sys

extra_compile_args = ["-DDLLX="]
extra_link_args = []

if sys.platform == "win32":
    print "Building windows application 'leveldb_mcpe'"
    include_dirs = ["C:/boost_1_55_0","./leveldb-mcpe/include"]
    library_dirs=["C:/boost_1_55_0/stage/lib","."]
    libraries=["leveldb-mcpe","shell32"]
    extra_compile_args += ["/EHs","/MDd"]
    extra_link_args += ["/MACHINE:x64"]

elif sys.platform == "darwin":
  include_dirs = ["/usr/local/include/boost", "./leveldb-mcpe/include", "."]
  library_dirs = ["/usr/local/lib", ".", "./leveldb-mcpe"]
  libraries = ["boost_python", "leveldb"]

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
      define_macros=[("WIN32", None),("_DEBUG", None),("_WINDOWS", None),("LEVELDB_PLATFORM_WINDOWS", None),("OS_WIN", None)],
      extra_compile_args=extra_compile_args,
      extra_link_args=extra_link_args)
    ]
)
