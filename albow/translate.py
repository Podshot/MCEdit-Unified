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
import sys
import json
import directories

enc = "utf8"

string_cache = {}
langPath = os.path.join(directories.getDataDir(), "lang")
oldlang = "en_US" # en_US is the default language string, no exceptions.
try:
	oldlang = Settings.langCode.get()
except:
    pass

#-------------------------------------------------------------------------------
# Translation loading and mapping functions
#-------------------------------------------------------------------------------
def tr(string, doNotTranslate=False):
    """Returns the translated 'string', or 'string' itself if no translation found."""
    if doNotTranslate:
        return string
    if type(string) not in (str, unicode):
        return string
    return string_cache.get(string, string.replace("\n", "\n\n"))

#-------------------------------------------------------------------------------
def refreshLang(self=None,suppressAlert=False,build=True):
    """Refreshes and returns the current language string"""
    global oldlang
    import config
    import leveleditor
    from leveleditor import Settings

    try:
        cancel = False
        lang = Settings.langCode.get() #.langCode
        isRealLang = verifyLangCode(lang)
        if build:
            buildTranslation(lang)
        if not oldlang == lang and not suppressAlert and isRealLang:
            import albow
            if leveleditor.LevelEditor(self).unsavedEdits:
                result = albow.ask("You must restart MCEdit to see language changes", ["Save and Restart", "Restart", "Later"])
            else:
                result = albow.ask("You must restart MCEdit to see language changes", ["Restart", "Later"])
            if result == "Save and Restart":
                editor.saveFile()
                restart(self)
            elif result == "Restart":
                restart(self)
            elif result == "Later":
                pass
            else:
                isRealLang = False
                cancel = True
        elif not suppressAlert and not isRealLang:
            import albow
            albow.alert("{} is not a valid language ({})".format(lang,os.path.join(langPath, lang + ".json")))
        if not isRealLang:
            Settings.langCode.set(oldlang)
        else:
            oldlang = lang
        if cancel == True:
            return ""
        else:
            return lang
    except Exception as inst:
        print inst
        return ""

#-------------------------------------------------------------------------------
def restart(mcedit):
    import config
    import mcplatform
    from pygame import display
    from leveleditor import Settings
    if sys.platform == "win32" and Settings.setWindowPlacement.get():
        (flags, showCmd, ptMin, ptMax, rect) = mcplatform.win32gui.GetWindowPlacement(
            display.get_wm_info()['window'])
        X, Y, r, b = rect
        #w = r-X
        #h = b-Y
        if (showCmd == mcplatform.win32con.SW_MINIMIZE or
                    showCmd == mcplatform.win32con.SW_SHOWMINIMIZED):
            showCmd = mcplatform.win32con.SW_SHOWNORMAL

        Settings.windowX.set(X)
        Settings.windowY.set(Y)
        Settings.windowShowCmd.set(showCmd)

    config.saveConfig()
    mcedit.editor.renderer.discardAllChunks()
    mcedit.editor.deleteAllCopiedSchematics()
    python = sys.executable
    os.execl(python, python, * sys.argv)

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
def verifyLangCode(lang):
    fName = os.path.join(langPath, lang + ".json")
    if (os.access(fName, os.F_OK) and os.path.isfile(fName) and os.access(fName, os.R_OK)) or lang == "en_US":
        return True
    else:
        return False
#-------------------------------------------------------------------------------
def buildTranslation(lang,suppressAlert=False):
    """Finds the file corresponding to 'lang' builds up string_cache.
    If the file is not valid, does nothing.
    Errors encountered during the process are silently ignored.
    Returns string_cache."""
    global string_cache
    fName = os.path.join(langPath, lang + ".json")
    if verifyLangCode(lang) and not lang == "en_US":
        with open(fName) as jsonString:
            string_cache = json.load(jsonString)
    return string_cache

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    ### FOR TEST
    import sys

    for k, v in buildTranslation("template").items():
        print k, v
    sys.exit()
    ###

