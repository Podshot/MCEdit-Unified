# -*- encoding: utf_8 -*-
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

import logging
log = logging.getLogger(__name__)

import os
# import sys # useless, only called in 'restart' (to be moved to mcedit.py)
import re
import codecs
# import json # json isn't user friendly decause of its syntax and the use of escaped characters for new lines, tabs, etc.
# import directories # suppress this

#!# for debugging
import platform, locale
def getPlatInfo(**kwargs):
    """kwargs: dict: {"module_name": module,...}
    used to display version information about modules."""
    log.debug("*** Platform information")
    log.debug("    System: %s"%platform.system())
    log.debug("    Release: %s"%platform.release())
    log.debug("    Version: %s"%platform.version())
    log.debug("    Architecture: %s, %s"%platform.architecture())
    log.debug("    Dist: %s, %s, %s"%platform.dist())
    log.debug("    Machine: %s"%platform.machine())
    log.debug("    Processor: %s"%platform.processor())
    log.debug("    Locale: %s"%locale.getdefaultlocale()[0])
    log.debug("    Encoding: %s"%locale.getdefaultlocale()[1])
    reVer = re.compile(r"__version__|_version_|__version|_version|version|"
                       "__ver__|_ver_|__ver|_ver|ver", re.IGNORECASE)
    for name, mod in kwargs.items():
        s = "%s"%dir(mod)
        verObjNames = list(re.findall(reVer, s))
        if len(verObjNames) > 0:
            while verObjNames:
                verObjName = verObjNames.pop()
                verObj = getattr(mod, verObjName, None)
                if verObj:
                    if type(verObj) in (str, unicode, int, list, tuple):
                        ver = "%s"%verObj
                        break
                    elif "%s"%type(verObj) == "<type 'module'>":
                        verObjNames += ["%s.%s"%(verObjName, a) for a in re.findall(reVer, "%s"%dir(verObj))]
                    else:
                        ver = verObj()
                else:
                    ver = "%s"%type(verObj)
            log.debug("    %s version: %s"%(name, ver))
    log.debug("***")
#getPlatInfo()
#!#

#enc = "utf8"
enc = locale.getdefaultlocale()[1]

string_cache = {}
#langPath = os.path.join(directories.getDataDir(), "lang") # find another way to set this
#oldlang = "en_US" # en_US is the default language string, no exceptions. ## Nope, default language is the language used by the app programmer.
#try:
#	oldlang = Settings.langCode.get()
#except:
#    pass
langPath = os.sep.join((".", "lang"))
lang = "Default"

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
# Suppress this.
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
# Move this to mcedit.py. The GUI does not have to handle program start/stop.
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
def setLangPath(path):
    """Changes the default 'lang' folder path. Retrun True if the path is valid, False otherwise."""
    log.debug("setLangPath <<<")
    log.debug("Argument 'path': %s"%path)
    path = os.path.normpath(os.path.abspath(path))
    log.debug("   Norm and abs: %s"%path)
    log.debug("os.access(path, os.F_OK): %s; os.path.isdir(path): %s; os.access(path, os.R_OK): %s"%(os.access(path, os.F_OK), os.path.isdir(path), os.access(path, os.R_OK)))
    if os.access(path, os.F_OK) and os.path.isdir(path) and os.access(path, os.R_OK):
        log.debug("'path' is valid")
        global langPath
        langPath = path
        return True
    lg.debug("'path' is not valid")
    log.debug("setLangPath >>>")
    return False

#-------------------------------------------------------------------------------
def getLangPath():
    """..."""
    return langPath

#-------------------------------------------------------------------------------
def getLang():
    return lang

def setLang(newlang):
    """Set the actual language. Returns old and new languages and string_cache in a tulpe.

    newlang: str: new laguage to load in the format <language>_<country>"""
    global lang
    oldLang = "" + lang
#    sc = {}.update(string_cache)
    result = False
    if not lang == newlang:
        sc, result = buildTranslation(newlang)
        lang = newlang
    else:
        result = True
    return oldLang, lang, result


#-------------------------------------------------------------------------------
def correctEncoding(data, oldEnc="ascii", newEnc=enc):
    """Returns encoded/decoded data."""
    return data
    if type(data) == str:
        data = data.decode(newEnc)
    elif type(data) == unicode:
        data = data.encode(oldEnc)
    if "\n" in data:
        data = data.replace("\n", "\n\n")
    return data


#-------------------------------------------------------------------------------
# Supress this ?
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
    Returns string_cache (dict) and wether the file exists (bool)."""
    log.debug("buildTranslation <<<")
    global string_cache
    fileFound = False
    lang = "%s"%lang
    fName = os.path.join(langPath, lang + ".trn")
    log.debug("fName: %s"%fName)
    log.debug("os.access(fName, os.F_OK): %s; os.path.isfile(fName): %s; os.access(fName, os.R_OK): %s"%(os.access(fName, os.F_OK), os.path.isfile(fName), os.access(fName, os.R_OK)))
    if os.access(fName, os.F_OK) and os.path.isfile(fName) and os.access(fName, os.R_OK):
        fileFound = True
#        data = open(fName, "rb").read() + "\x00"
        data = codecs.open(fName, "r", "utf-8").read() + "\x00"
        log.debug("fName is valid and read.")
        log.debug("Type of file data is %s"%type(data))
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
    log.debug("buildTranslation >>>")
    return string_cache, fileFound

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    ### FOR TEST
    import sys

    if setLangPath("."):
        for k, v in buildTranslation("template").items():
            print k, v
        sys.exit()
    ###

