# MCEdit-Unified

MCEdit-Unified is an updated fork of the original MCEdit by Codewarrior. The previous license still applies. MCEdit-Unified is an open-source, BSD-licensed world editor for the viral indie hit [Minecraft](http://www.minecraft.net/). For downloads and update info, visit the official website at [khroki.github.io/MCEdit-Unified](http://khroki.github.io/MCEdit-Unified/). The rest of this file is intended for computer programmers, Linux/Mac users, and those who wish to run from source.

## Localisation

This version implements localisation functions.
The resource files are located in the 'lang' folder for MCEdit UI.

Custom brushes and filters can be also translated, provided a folder named like the base name of the brush/filter file (ithout the '.py' extension) can be found alongside the file and contains the resources.
These resources have to be built with the same rules than MCEdit ones.

The UI fixed character strings can appear in users native language by simply editing translation files.
It is also possible to (re)build the language template and files and to use custom fonts.

See TRANSLATION.txt for further details.

Devolopers don't have to tweak their code so much.
The only modifications concern strings which need text formating or concatenation.
See README.txt in albow subfolder for further information.


-- D.C.-G. (LaChal)

## Running from source

MCEdit-Unified is written in Python using a variety of open source modules. When developing it is recommended to use virtualenv to keep dependencies sane and for easy deployment. You'll need Python 2.7 (Python 3 is not supported) at a minimum before getting started. Easy_install / pip is reccommended.

Clone MCEdit-Unified using your github client of choice:

`>git clone https://github.com/Khroki/MCEdit-Unified`

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
`>easy_install pywin32 (Windows only, needed for compiling)`

For windows users if `easy_install` cannot find a library you need, or you can't get `easy_install` working, all needed libraries can be downloaded as precompiled binaries on the internet in both 32bit and 64bit. pywin32 is available in 64bit despite it's name.

Debian and Ubuntu Linux users can install the following packages via apt-get to grab all the dependencies easily and install them into the system python. This also downloads all libraries required to build these modules using `pip install`

`$sudo apt-get install python-opengl python-pygame python-yaml python-numpy python-xlib`

You should now be able to run MCEdit-Unified with `python mcedit.py` assuming you've installed all the dependencies correctly.

