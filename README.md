# MCEdit

MCEdit is an open-source, BSD-licenced world editor for the viral indie hit [Minecraft](http://www.minecraft.net/). For downloads and update info, visit the official website at [khroki.github.io/MCEdit-Unified](http://khroki.github.io/MCEdit-Unified/). The rest of this file is intended for computer programmers, Linux/Mac users, and those who wish to run from source.

## Note for localisation

This version implements localisation functions.

The UI fixed character strings can appear in users native language by simply editing translation files. Devolopers don't have to tweak their code.
The strings which need text formating or concatenation have to be translated with the '_()' function before being formated. This function must be imported from albow.translate.

See README.txt in albow subfolder for further details.

-- D.C.-G.

## Running from source

MCEdit is written in Python using a variety of open source modules. When developing it is recommended to use virtualenv to keep dependencies sane and for easy deployment. You'll need Python 2.7 (Python 3 is not supported) at a minimum before getting started. Easy_install / pip is reccommended.

Clone MCEdit using your github client of choice:

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
`>easy_install pywin32 (Windows only, needed for compiling)`
`>easy_install tkinter (Required for linux, should come with Win and Mac)`

For windows users if easy install cannot find a library you need, or you can't get easy install working, all needed libraries can be downloaded as precompiled binaries on the internet in both 32bit and 64bit. pywin32 is available in 64bit despite it's name.

Debian and Ubuntu Linux users can install the following packages via apt-get to grab all the dependencies easily and install them into the system python. This also downloads all libraries required to build these modules using `pip install`

`$sudo apt-get install python-opengl python-pygame python-yaml python-numpy python-tk`

You should now be able to run MCEdit with `python mcedit.py` assuming you've installed all the dependencies correctly.

