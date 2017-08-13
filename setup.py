from setuptools import setup
from Cython.Build import cythonize

# Output annotated .html
import Cython.Compiler.Options
Cython.Compiler.Options.annotate = True

ext_modules = cythonize(["cpngfilters.pyx", "pymclevel/_nbt.pyx"])

setup(
    ext_modules=ext_modules
)
