import sys
from setuptools import setup
from Cython.Build import cythonize

# Output annotated .html
import Cython.Compiler.Options
Cython.Compiler.Options.annotate = True

modules_map = {
    "png": {"source": "cpngfilters.pyx",
            "description": "Build the accelerator to work with PNG images."},
    "nbt": {"source": "pymclevel/_nbt.pyx",
            "description": "Build the accelerator to work with NBT data."}
    }

__help__ = """setup.py
Build Cython extensions for MCEdit-Unified.

You have to use at least one argument on the command line to build extensions.

Valid arguments are:

help   Print this message.
all    Build all extensions.
""" + "\n".join(["%s    %s" % (k, v["description"]) for k, v in modules_map.items()])

# Let people choose what to build.
# If no argument is given on the command line, display help message.
# If a wrong argument is given, break.
if len(sys.argv) == 1:
    print __help__
    sys.exit(0)
else:
    ext_modules = []
    args = sys.argv[1:]
    msg = "Following extensions will be built: %s."
    ext_list = []
    for arg in args:
        if arg == 'help':
            print __help__
            sys.exit(0)
        elif arg == 'all':
            ext_list = list(modules_map.keys())
            ext_modules = [v["source"] for v in modules_map.values()]
        elif arg not in modules_map.keys():
            print "'%s' is not a valid argument. Use 'help' one for information." % arg
            sys.exit(1)
        else:
            src = modules_map[arg]["source"]
            if src not in ext_modules:
                ext_list.append(arg)
                ext_modules.append(src)
        sys.argv.remove(arg)
    print msg % ", ".join(ext_list)

sys.argv.append('build_ext')

setup(
    ext_modules=cythonize(ext_modules)
)
