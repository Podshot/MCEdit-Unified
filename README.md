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

MCEdit-Unified is written in Python using a variety of open source modules. When developing it is recommended to use virtualenv to keep dependencies sane and for easy deployment. You'll need Python 2.7 (Python 3 is not supported) at a minimum before getting started. Easy_install / pip is reccommended.

Clone MCEdit-Unified using your github client of choice:

```sh
git clone --recursive https://github.com/Khroki/MCEdit-Unified
```

Or, if you've already cloned MCEdit in the past and need to update, go to the existing source folder then run:

```sh
git pull
```

Optionally (but highly recommended), setup and activate [virtualenv](http://pypi.python.org/pypi/virtualenv). virtualenv will simplify development by creating an isolated and barebones Python environment. Anything you install while virtualenv is active won't affect your system-wide Python installation, for example.

```sh
cd mcedit
easy_install virtualenv
virtualenv ENV
. ENV/bin/activate
```

Install various dependencies. This may take a bit (especially numpy). If installing pygame errors, try installing from a [binary packages](http://pygame.org/install.html) or following one of the guides from that page to install from source. On Windows, `easy_install` is preferred because it installs prebuilt binary packages. On Linux and Mac OS X, you may want to use `pip install` instead.
Linux users can also use the package manager to install the dependencies.

```sh
easy_install PyOpenGL
easy_install numpy==1.9.3
easy_install pygame
easy_install Pillow==2.9.0
easy_install ftputil
easy_install pywin32 (Windows only, needed for compiling)
```

For windows users if `easy_install` cannot find a library you need, or you can't get `easy_install` working, all needed libraries can be downloaded as precompiled binaries on the internet in both 32bit and 64bit. pywin32 is available in 64bit despite it's name.

Debian and Ubuntu Linux users can install the following packages via apt-get to grab all the dependencies easily and install them into the system python. This also downloads all libraries required to build these modules using `pip install`

```sh
sudo apt-get install python-opengl python-pygame python-yaml python-numpy python-xlib
```

Mac and Linux users need to install python-xlib. This can be done using `pip`:

```sh
pip install svn+https://svn.code.sf.net/p/python-xlib/code/trunk/
```

Linux users must install python-xlib 0.14 (or over). It may be possible that the pip repository install the wrong version. Google a bit to grab the right version archive, and install it manually. (It's a pure Python package and does not require C extension compilation.)

You should now be able to run MCEdit-Unified with `python mcedit.py` assuming you've installed all the dependencies correctly.
On Linux, it is recommended to use the `mcedit.sh` shell script.

## INSTALLING _nbt.pyx

pymclevel contains a cython version of _nbt. This one is a lot faster, but has to be build manually.
It requires cython 0.21.2 (Note: there are issues with 0.22)

```sh
pip install cython==0.21.2
```

It's also worth upgrading setuptools:

```sh
pip install setuptools --upgrade
```

With cython you should be able to build the file.

```sh
python setup.py develop
```

If no errors occured, only thing left to do is see if it worked correctly:

```sh
python setuptest.py
```

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
