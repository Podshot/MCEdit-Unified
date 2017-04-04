from setuptools import setup
from Cython.Build import cythonize

# Output annotated .html
import Cython.Compiler.Options
Cython.Compiler.Options.annotate = True
import numpy

ext_modules = cythonize(["cpngfilters.pyx", "pymclevel/_nbt.pyx", "cy_renderer.pyx"])

setup(
    ext_modules=ext_modules,
    include_dirs=[numpy.get_include()]
)
