from setuptools import setup
from Cython.Build import cythonize

# Output annotated .html
import Cython.Compiler.Options
Cython.Compiler.Options.annotate = True

pymclevel_ext_modules = cythonize("pymclevel/_nbt.pyx")

setup(
    ext_modules=pymclevel_ext_modules
)
