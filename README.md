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
See README.txt in albow subfolder for further information.


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

`>git clone --recursive https://github.com/Khroki/MCEdit-Unified`

Or, if you've already cloned MCEdit in the past and need to update, go to the existing source folder then run:

`>git pull`

Optionally (but highly recommended), setup and activate [virtualenv](http://pypi.python.org/pypi/virtualenv). virtualenv will simplify development by creating an isolated and barebones Python environment. Anything you install while virtualenv is active won't affect your system-wide Python installation, for example.

`>cd mcedit`
`>easy_install virtualenv`
`>virtualenv ENV`
`>. ENV/bin/activate`

Install various dependencies. This may take a bit (especially numpy). If installing pygame errors, try installing from a [binary packages](http://pygame.org/install.html) or following one of the guides from that page to install from source. On Windows, `easy_install` is preferred because it installs prebuilt binary packages. On Linux and Mac OS X, you may want to use `pip install` instead.

`>easy_install PyOpenGL`
`>easy_install numpy`
`>easy_install pygame`
`>easy_install pyyaml`
`>easy_install Pillow`
`>easy_install ftputil`
`>easy_install pywin32 (Windows only, needed for compiling)`

For windows users if `easy_install` cannot find a library you need, or you can't get `easy_install` working, all needed libraries can be downloaded as precompiled binaries on the internet in both 32bit and 64bit. pywin32 is available in 64bit despite it's name.

Debian and Ubuntu Linux users can install the following packages via apt-get to grab all the dependencies easily and install them into the system python. This also downloads all libraries required to build these modules using `pip install`

`$sudo apt-get install python-opengl python-pygame python-yaml python-numpy python-xlib`

You should now be able to run MCEdit-Unified with `python mcedit.py` assuming you've installed all the dependencies correctly.

## INSTALLING _nbt.pyx:
pymclevel contains a cython version of _nbt. This one is a lot faster, but has to be build manually.
It requires cython 0.21.2 (there are issues with 0.22:
' > pip install cython==0.21.2'
It's also worth upgrading setuptools:
' > pip install setuptools --upgrade'

With cython you should be able to build the file.
python setup.py develop

If no errors occured, only thing left to do is see if it worked correctly:
python setuptest.py


## INSTALLING leveldb_mcpe:
MCPE support requires a special library. MCEdit will run without it, but to have MCPE support you need to build it yourself.
For mac and/or windows users:
This requires a boost.python installation.
Get boost: http://www.boost.org/ and make sure to build the python libs.

Next step is to get leveldb-mcpe from Mojang:
https://github.com/Mojang/leveldb-mcpe

Build the thing using something like cmake, and copy the created leveldb-mcpe.lib to ./leveldb_mcpe

After those steps, you should be able to build the required .pyx:
' > cd ./leveldb_mcpe'
python setup.py build
Head into the build folder and look for the folder containing the .pyx. Copy it to ./leveldb_mcpe, and test:
' > python test.py'

If no errors occured, move the .pyx to ../pymclevel, and you should be good to go.

For linux users:
Navigate to the leveldb_mcpe folder
'> python setup.py build'
'> python test.py'
And you should be good to go.
