from setuptools import setup
from distutils.extension import Extension
import os.path
import sys
 
if sys.platform == "win32":
    print "Building windows application 'leveldb_mcpe'"
    include_dirs = ["C:/boost_1_55_0","./leveldb-mcpe/include"]
    library_dirs=["C:/boost_1_55_0/stage/lib","."]
    libraries=["leveldb-mcpe","shell32"]

else:
	pass
	
files = ["leveldb_mcpe.cpp"]
 
setup(name="leveldb_python_wrapper",
      ext_modules=[
                    Extension("leveldb_mcpe",files,
                    library_dirs=library_dirs,
                    libraries=libraries,
                    include_dirs=include_dirs,
                    depends=[],
					define_macros=[("WIN32", None),("_DEBUG", None),("_WINDOWS", None),("LEVELDB_PLATFORM_WINDOWS", None),("OS_WIN", None)],
                    extra_compile_args=["/EHs","-DDLLX=","/MDd"],
                    extra_link_args=["/MACHINE:x64"]						
					)
                    ]
     )
