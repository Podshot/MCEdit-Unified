from setuptools import setup
from Cython.Build import cythonize

# Output annotated .html
import Cython.Compiler.Options
Cython.Compiler.Options.annotate = True
import numpy
import os

extensions = ["cpngfilters.pyx", "pymclevel/_nbt.pyx"]

if os.path.exists("_renderer.pyx"):
    extensions.append("_renderer.pyx")
ext_modules = cythonize(extensions)

setup(
    ext_modules=ext_modules,
    include_dirs=[numpy.get_include()]
)
