import numpy
import imp
from setuptools import setup
from Cython.Build import cythonize
from Cython.Distutils import build_ext

# Output annotated .html
import Cython.Compiler.Options
import sys

Cython.Compiler.Options.annotate = True

ext_modules = cythonize("MCWorldLibrary/_nbt.pyx")
install_requires = ['numpy', 'Cython']

PE = "--include_leveldb_mcpe" in sys.argv


def load_module(name):
    names = name.split(".")
    path = None
    for name in names:
        f, path, info = imp.find_module(name, path)
        path = [path]
    return imp.load_module(name, f, path[0], info)

if PE:
    sys.argv.remove("--include_leveldb_mcpe")
    ext = load_module("MCWorldLibrary.pyleveldb_mcpe.extension")
    ext_modules.append(ext.get_extension())

setup(
    name='MCEdit-Unified',
    description='Minecraft World Editor',
    long_description=open("./README.md", 'r').read(),
    keywords='minecraft',
    author='David Vierra, MCEdit-Unified contributors',
    author_email='',
    url='https://github.com/Khroki/MCEdit-Unified/',
    license='MIT License',
    package_dir={'mcedit': '.'},
    packages=['mcedit'],
    ext_modules=ext_modules,
    include_dirs=numpy.get_include(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['numpy', 'Cython'],
    cmdclass={'build_ext': build_ext},
    entry_points={"console_scripts": ["mcedit = mcedit.py:main", ]},
)
