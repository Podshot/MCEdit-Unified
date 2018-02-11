# MCEdit-Unified

MCEdit-Unified is an updated fork of the original MCEdit by Codewarrior. The previous license still applies. MCEdit-Unified is an open-source, BSD-licensed world editor for the viral indie hit [Minecraft](http://www.minecraft.net/). For downloads and update info, visit the official website at [khroki.github.io/MCEdit-Unified](http://khroki.github.io/MCEdit-Unified/). The rest of this file is intended for computer programmers, Linux/Mac users, and those who wish to run from source.

## Localisation

This version implements localisation functions.
The resource files are located in the 'lang' folder for MCEdit UI.

Custom brushes and filters can be also translated, provided a folder named like the base name of the brush/filter file (without the '.py' extension) can be found alongside the file and contains the resources.
These resources have to be built with the same rules than MCEdit ones.

The UI fixed character strings can appear in users native language by simply editing translation files.
It is also possible to (re)build the language template and files and to use custom fonts.

See TRANSLATION.txt for further details.

Developers don't have to tweak their code so much.
The only modifications concern strings which need text formatting or concatenation.
See README.txt in `albow` subfolder for further information.

-- D.C.-G. (LaChal)

## Random splash screens

MCEdit now displays random splash screens at startup.

You can make your own and add it in the `splashes` folder. The name of the file does not matter. Just pay attention it is a PNG image.

There isn't any MCEdit setting to enable or disable this feature for now.
The `splash` file in the MCEdit install folder handles it. It is a plain text file, and it contains the name of an image to be used as a splash screen.

To unactivate the random splash screens, edit the `splash` file and delete its content.
If you delete the file, it will be generated again, and the feature will be activated.

## Running from source

### Requirements

These programs and packages are required:

**General**

* git
* Python 2.7+ (Python 3 is unsupported)
* virtualenv (not strictly required, but highly recommended)

**Python packages**

* [pygame](http://pygame.org/install.html)
* PyOpenGL
* numpy 1.13.3
* Pillow 4.2.1
* ftputil (Optional, but FTP server support will be disabled without it)
* python-yaml
* python-xlib 0.14

On Windows, these are also required:

* pywin32
* pypiwin32

### 1. Clone repo

Clone the repo (recursively, to also clone submodules):

```sh
git clone --recursive https://github.com/Khroki/MCEdit-Unified
```

### 2. Install dependencies

#### Linux

On Linux, these may be installed at the system level with your distro package manager.

If they are not available, you can install them using `pip install --user PACKAGE`.  In this case, you should set up the virtualenv first, like this:

```sh
cd MCEdit-Unified  # Enter the repo directory
virtualenv virtualenv  # Create new virtualenv in "virtualenv" directory
source virtualenv/bin/activate  # Deactivate by running "deactivate" when done
```

**Note about python-xlib:** Some Linux distros do not have version 0.14 of python-xlib.  In this case, you should install it with `pip` (either in a virtualenv, or after removing the system package).

#### Debian/Ubuntu

On Debian and Ubuntu, the Python packages may be installed from distro repositories like this:

```sh
sudo apt-get install python-opengl python-pygame python-yaml python-numpy python-xlib
```

#### Mac OS X and Windows

The Python packages may be installed using `pip install --user PACKAGE`.

### 3. Run

#### Linux

Run `mcedit.sh`.

#### Windows

Run `python mcedit.py`.

## BUILDING NBT AND PNG SUPPORT

__Please, mind to adapt the following information according to your operating system!__

### DEPENDENCIES

To build these libaries, you'll need _Cython 0.21_ and _setuptools_.

First, install or update _setuptools_:

* Download [get-pypi.py](https://bootstrap.pypa.io/get-pip.py)
* Run it: `python pypi.py`

Then, install Cython:

`pip install cython==0.21.2`


### SETUP SCRIPT

This script is intended to be run in a shell opened in MCEdit-Unified folder.

It takes arguments on the command line to work correctly.
Invoke it like this:

`python setup.py <argument> [argument [argument [...]]]`

Without argument, it will fail. (And let you know...)


Use the `all` argument to build all the libraries the script can handle.  
The `nbt` one will build only the NBT support.  
The `png` one will build only the PNG support.  
The `help` one can, ehhh, help...

After the NBT support is built, you can run a very simple test:

`python setuptest.py`


### Pocket Edition Support

MCPE support requires a special library. MCEdit will run without it, but you will not be able to edit Pocket worlds.

This library is embeded in the packages for OSX and Windows, and will mostly work.

On Linux systems, it is necessary to compile the library, because it requires to be linked to `zlib` one on the system.
It may be necessary to compile `zlib` specifically for the PE support if the one on the system is not compatible. (It may also happen this library is not on the system...)

The Python script `setup_leveldb.py` in the `pymclevel` directory wuill build the PE support, and the `zlib` library when needed.
Read `INSTALL_LEVELDB` in the `pymclevel` directory for more information.

Note that, if you use the installer for Linux, this script is used during installation to build the library.

([[Compilation on Windows and OSX part to be written.]])

It is possible to enable a debug mode for PE support by running MCEdit with the `--debug-pe` option on the command line.
Some messages will be displayed in the console. A lot of information will be stored in a `dump_pe.txt` file. This file can be very big, so be carefull with this debug mode!
You can use this option several times to get more information in the file. Currently, using this option more than 2 times will have no effect.

## New features test mode

Some unfinished features and fixes may be included in future MCEdit-Unified releases, this inactive code can be activated using the process below. Use at your own risk.

To use:

* Open your operating system's command console.
* Go to the directory where MCEdit is installed (Mac users need to open their .app file).
* Create a text file named `new_features.def`
* In this file, add a feature per line. (Unfinished features/fixes are available on request from the developers))
* Run MCEdit-Unified with the command line option `--new-features`

These 'new features' will change during the program development. Features may be added or removed at will and may not work at all, most will eventually end up in a release as a normal feature. No documentation is provided for them, except in the code source itself.

We recommend you to use this only if you have at least some familiarity with programming and source code, or if requested by a developer.
We highly recommend backing up your worlds (and even the whole game) before using this function, even if requested by the devs.
