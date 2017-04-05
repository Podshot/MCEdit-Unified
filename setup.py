from setuptools import setup
from Cython.Build import cythonize

# Output annotated .html
import Cython.Compiler.Options
Cython.Compiler.Options.annotate = True
import numpy
import sys

extensions = ["cpngfilters.pyx", "pymclevel/_nbt.pyx"]
if '--renderer' in sys.argv:
    extensions.append("cy_renderer.pyx")
ext_modules = cythonize(extensions)

setup(
    ext_modules=ext_modules,
    include_dirs=[numpy.get_include()]
)
