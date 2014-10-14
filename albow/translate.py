# -*- encoding: utf8 -*-
#
# /usr/bin/python
#
# translate.py
#
# (c) D.C.-G. 2014
#
# Translation module for Python 2.7, especialy for Albow 2 and MCEdit 1.8 799
#
#-------------------------------------------------------------------------------
"""This module adds translation functionnalities to Albow.

It looks for locale files in a sub folder 'lang' according to the system
default, or user specified locale.

The locale files are text files where 'entries' are defined.

Syntax example:

o0 This is the first entry.
t0 Ceci est la première entrée.
o1 Here is the second one.
You can see it is splitted on two lines.
t1 Voici la deuxième.
Vous pouvez constater qu'elle est sur deux lignes.

The 'oN' markers on the begining of a line marks the original string;
the 'tN', the translations.
Strings can be splited on several lines and contain any sort of
characters (thus, be aware of unicode).

Files are named according to their language name, e.g. fr_FR.trn for
french.
The extension .trn is an arbitrary convention.
The file 'template.trn' is given to be used as a base for other ones. It
contains the strings used in Albow. They are not translated.

As convention, english is considered as the default language, and the
file en_EN.trn would never be present.

Usage:

You need, a least, these three function in your program:
* setLangPath to define the translations location;
* buildTranslation to build up the cache;
* _ function to translate strings.
"""

import os
import re
import locale
# enc = locale.getdefaultlocale()[-1]
enc = "utf8"

string_cache = {}
langPath = os.sep.join((".", "lang"))
lang = "en_US"

#-------------------------------------------------------------------------------
# Translation loading and mapping functions
#-------------------------------------------------------------------------------
def _(string, doNotTranslate=False):
    """Returns the translated 'string', or 'string' itself if no translation found."""
    if doNotTranslate:
        return string
    if type(string) not in (str, unicode):
        return string
    return string_cache.get(string, string.replace("\n", "\n\n"))

#-------------------------------------------------------------------------------
def setLangPath(path):
    """Changes the default 'lang' folder path. Retrun True if the path is valid, False otherwise."""
    path = os.path.normpath(os.path.abspath(path))
    if os.access(path, os.F_OK) and os.path.isdir(path) and os.access(path, os.R_OK):
        global langPath
        langPath = path
        return True
    else:
        return False


def getLangPath():
    """..."""
    return langPath

#-------------------------------------------------------------------------------
def getLang():
    return lang

def setLang(newlang):
    global lang
    if not lang == newlang:
        buildTranslation(newlang)
        lang = newlang

#-------------------------------------------------------------------------------
def correctEncoding(data, oldEnc="ascii", newEnc=enc):
    """Returns encoded/decoded data."""
    if type(data) == str:
        data = data.decode(newEnc)
    elif type(data) == unicode:
        data = data.encode(oldEnc)
    if "\n" in data:
        data = data.replace("\n", "\n\n")
    return data

#-------------------------------------------------------------------------------
def buildTranslation(lang):
    """Finds the file corresponding to 'lang' builds up string_cache.
    If the file is not valid, does nothing.
    Errors encountered during the process are silently ignored.
    Returns string_cache."""
    global string_cache
    fName = os.path.join(langPath, lang + ".trn")
    if os.access(fName, os.F_OK) and os.path.isfile(fName) and os.access(fName, os.R_OK):
        data = open(fName, "rb").read() + "\x00"
        trnPattern = re.compile(r"^o\d+[ ]|^t\d+[ ]", re.M|re.S)
        grps = re.finditer(trnPattern, data)
        oStart = -1
        oEnd = -1
        tStart = -1
        tEnd = -1
        org = None
        for grp in grps:
            g = grp.group()
            if g.startswith("o"):
                oStart = grp.end()
                tEnd = grp.start() -1
            elif g.startswith("t"):
                oEnd = grp.start() -1
                tStart = grp.end()
            if oStart > -1 and oEnd > -1 and tStart > tEnd:
                org = data[oStart:oEnd]
            if tStart > -1 and (tEnd > -1):
                if tEnd > tStart:
                    string_cache[org] = correctEncoding(data[tStart:tEnd])
                    tStart = -1
                    tEnd = -1
        string_cache[org] = correctEncoding(data[tStart:tEnd -1])
    return string_cache

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    ### FOR TEST
    import sys

    if setLangPath("."):
        for k, v in buildTranslation("template").items():
            print k, v
        sys.exit()
    ###

