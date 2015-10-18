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
import re
import codecs
import json
import resource
import directories

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
    log.debug("    FS encoding: %s"%os.sys.getfilesystemencoding())
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


enc = locale.getdefaultlocale()[1]
if enc is None:
    enc = "UTF-8"

string_cache = {}
font_lang_cache = {}
langPath = directories.getDataDir("lang")
lang = "Default"

# template building
strNum = 0
template = {} # {"string": number}
buildTemplate = False
trnHeader = """# TRANSLATION BASICS
#
# This file works by mapping original English strings(o##) to the new translated strings(t##)
# As long as the numbers match, it will translate the specified English string to the new language.
# Any text formatting is preserved, so new lines, tabs, spaces, brackets, quotes and other special characters can be used.
#
# The space (' ') separating the strings from the numbers is mandatory.
# The file must also be encoded in UTF-8 or it won't work. Most editors should support this.
#
# See TRANSLATION.txt for more detailed information.
#"""

buildTemplateMarker = """
### THE FOLLOWING LINES HAS BEEN ADDED BY THE TEMPLATE UPDATE FUNCTION.
### Please, consider to analyze them and remove the entries referring
### to ones containing string formatting.
###
### For example, if you have a line already defined with this text:
### My %{animal} has %d legs.
### you may find lines like these below:
### My parrot has 2 legs.
### My dog has 4 legs.
###
### And, remove this paragraph too...
"""
#-------------------------------------------------------------------------------
# Translation loading and mapping functions
#-------------------------------------------------------------------------------

def _(string, doNotTranslate=False, hotKey=False):
    """Returns the translated 'string', or 'string' itself if no translation found."""
    if type(string) == str:
        string = unicode(string, enc)
    if doNotTranslate:
        return string
    if type(string) not in (str, unicode):
        return string
#     try:
#         trn = u"%s"%(string)
#     except Exception, e:
#         print "TRANSLATE ERROR", e
#         log.debug('TRANSLATE ERROR: %s'%e)
#         trn = string_cache.get(string, string)
#     if trn == string:
#         trn = string_cache.get(string, trn)
    trn = string_cache.get(string, string)
    if trn == string and '-' in string:
        # Support for hotkeys
        trn = '-'.join([_(a, hotKey=True) for a in string.split('-') if _(a, hotKey=True) != a or a])
        hotKey = True
    # We don't want hotkeys and blank strings.
    if buildTemplate and not hotKey and string.strip():
        global template
        global strNum
        if (string, None) not in [(a, None) for a, b in template.values()]:
            template[len(template.keys())] = (string, "")
            strNum += 1
    return trn or string

#-------------------------------------------------------------------------------

def loadTemplate(fName="template.trn"):
    """Load the template fName file in the global template variable.
    Returns the template."""
    global template
    global trnHeader
    global strNum
    fName = os.path.join(getLangPath(), fName)
    if os.access(fName, os.F_OK) and os.path.isfile(fName) and os.access(fName, os.R_OK):
        oldData = codecs.open(fName, "r", "utf-8").read() + buildTemplateMarker
        trnHeader = u""
        # find the first oXX
        start = re.search(ur"^o\d+[ ]", oldData, re.M|re.S)
        if start:
            start = start.start()
        else:
            print "*** %s malformed. Could not find entry point.\n    Template not loaded."%os.path.split(fName)[-1]
        trnHeader += oldData[:max(0, start - 1)]
        trnPattern = re.compile(ur"^o\d+[ ]|^t\d+[ ]", re.M|re.S)
        grps = re.finditer(trnPattern, oldData)
        oStart = -1
        oEnd = -1
        tStart = -1
        tEnd = -1
        org = None
        num = 0
        oNum = -1
        tNum = -1
        for grp in grps:
            g = grp.group()
            if g.startswith(u"o"):
                oStart = grp.end()
                tEnd = grp.start() -1
                oNum = int(g[1:])
            elif g.startswith(u"t"):
                oEnd = grp.start() -1
                tStart = grp.end()
                tNum = int(g[1:])
            if oNum == tNum:
                org = oldData[oStart:oEnd]
            if tStart > -1 and (tEnd > -1):
                if tEnd >= tStart:
                    template[num] = (org, oldData[tStart:tEnd])
                    num += 1
                    tStart = -1
                    tEnd = -1
        template[num] = (org, oldData[tStart:tEnd])
        strNum = num
    return template

#-------------------------------------------------------------------------------

def saveTemplate():
    if buildTemplate:
        fName = os.path.abspath(os.path.join(getLangPath(), "template.trn"))
        f = codecs.open(fName, "w", "utf-8")
        f.write(trnHeader)
        keys = template.keys()
        keys.sort()
        for key in keys:
            org, trn = template[key]
            f.write(u"\no%s %s\nt%s %s"%(key, org, key, trn))
        f.close()

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
    log.debug("'path' is not valid")
    log.debug("setLangPath >>>")
    return False

#-------------------------------------------------------------------------------

def getLangPath():
    """Return the actual 'lang' folder."""
    return langPath

#-------------------------------------------------------------------------------

def getLang():
    """Return the actual language."""
    return lang


def setLang(newlang):
    """Set the actual language. Returns old and new languages and string_cache in a tulpe.

    newlang: str: new laguage to load in the format <language>_<country>"""
    global lang
    oldLang = "" + lang
    if not lang == newlang:
        sc, result = buildTranslation(newlang)
        lang = newlang
        if newlang == 'en_US':
            result = True
            try:
                resource.setCurLang(u"English (US)")
            except:
                resource.__curLang = u"English (US)"
    else:
        result = True
    return oldLang, lang, result


#-------------------------------------------------------------------------------
def correctEncoding(data, oldEnc="ascii", newEnc=enc):
    """Returns encoded/decoded data.
    Disabled for now..."""
    return data  # disabled for now, but can be use full in the future
    if type(data) == str:
        data = data.decode(newEnc)
    elif type(data) == unicode:
        data = data.encode(oldEnc)
    if "\n" in data:
        data = data.replace("\n", "\n\n")
    return data


#-------------------------------------------------------------------------------
def getLangName(file, path=None):
    """Return the language name defined in the .trn file.
    If the name is not found, return the file base name."""
    if not path:
        path = langPath
    f = codecs.open(os.path.join(path, file), "r", "utf-8")
    line = f.readline()
    if "#-# " in line:
        name = line.split("#-# ")[1].strip()
    else:
        name = os.path.splitext(os.path.basename(file))[0]
    line = f.readline()
    regular = None
    if "#-# font regular: " in line:
        regular = line.split("#-# font regular: ")[1].strip()
    line = f.readline()
    bold = None
    if "#-# font bold: " in line:
        bold = line.split("#-# font bold: ")[1].strip()
    global font_lang_cache
    if regular and regular.lower() != "default":
        if not font_lang_cache.get("DejaVuSans-Regular.ttf", False):
            font_lang_cache["DejaVuSans-Regular.ttf"] = {name: regular}
        else:
            font_lang_cache["DejaVuSans-Regular.ttf"][name] = regular
    if bold and bold.lower() != "default":
        if not font_lang_cache.get("DejaVuSans-Bold.ttf", False):
            font_lang_cache["DejaVuSans-Bold.ttf"] = {name: bold}
        else:
            font_lang_cache["DejaVuSans-Bold.ttf"][name] = bold
    resource.font_lang_cache = font_lang_cache
    return name


from time import asctime, time
#-------------------------------------------------------------------------------


def buildTranslation(lang, extend=False, langPath=None):
    """Finds the file corresponding to 'lang' builds up string_cache.
    If the file is not valid, does nothing.
    Errors encountered during the process are silently ignored.
    Returns string_cache (dict) and wether the file exists (bool)."""
    log.debug("buildTranslation <<<")
    tm = time()
    if not langPath:
        langPath = getLangPath()
    str_cache = {}
    global string_cache
    fileFound = False
    lang = u"%s" % lang
    fName = os.path.join(langPath, lang + ".trn")
    log.debug("fName: %s" % fName)
    if os.access(fName, os.F_OK) and os.path.isfile(fName) and os.access(fName, os.R_OK):
        fileFound = True
        rawData = codecs.open(fName, "r", "utf-8").read()
        log.debug("fName is valid and read.")
        log.debug("Type of file data is %s"%("%s"%type(rawData)).strip("<type '").strip(">")[:-1])
        log.debug("Parsing file and building JSON resource.")
        log.debug("  * Start on %s"%tm)
        start = re.search(r"^o\d+[ ]", rawData, re.M|re.S)
        if start:
            start = start.start()
        else:
            log.warning("    *** %s malformed. Could not find entry point.\n    Translation not loaded.")
            # exiting without further operations
            return {}, False
        data = rawData[start:]
        trnPattern = re.compile(r"^o\d+[ ]|^t\d+[ ]", re.M|re.S)
        grps = re.findall(trnPattern, data)
        if len(grps) % 2 != 0:
            grps1 = re.findall(r"^o\d+[ ]", data, re.M|re.S)
            grps2 = re.findall(r"^t\d+[ ]", data, re.M|re.S)
            log.warning("    Unpaired original and translated strings. %s is longer (oXX: %s, tXX: %s)."%({True: "tXX", False: "oXX"}[len(grps1) < len(grps2)], len(grps1), len(grps2)))
            bugStrs = []

            def compLists(lst1, lst1N, lst2, lst2N, repl, bugStrs=bugStrs):
                bug = []
                for item in lst1:
                    itm = repl + item[1:]
                    if itm in lst2:
                        idx = lst2.index(itm)
                        lst2.pop(idx)
                    else:
                        bug.append(item)
                bugStrs += ["Not found in %s"%lst1N, bug]
                bugStrs += ["Not found in %s"%lst2N, lst2]
            if len(grps1) < len(grps2):
                compLists(grps1, "grps1", grps2, "grps2", u"t")
                log.warning("    Compared oXX tXX:")
                log.warning("    %s"%bugStrs)
            else:
                compLists(grps2, "grps2", grps1, "grps1", u"o")
                log.warning("    Compared tXX oXX:")
                log.warning("    %s"%bugStrs)
            return {}, False
        n1 = len(grps) / 2
        result = u""
        n = 1
        n2 = 0
        r = u"" + data.replace(u"\\", u"\\\\").replace(u"\"", u'\\"').replace(u"\r\n", u"\n").replace(u"\r", u"\n")
        log.debug("    Replacing oXX/tXX.")
        while n:
            r, n = re.subn(r"^o\d+[ ]|\no\d+[ ]", "\",\"", r, flags=re.M|re.S)
            r, n = re.subn(r"^t\d+[ ]|\nt\d+[ ]", "\":\"", r, flags=re.M|re.S)
            n2 += n
            if n2 == n1:
                n = 0
        log.debug("    Replaced %s occurences."%n2)
        result += r[2:]
        result = u"{" + result.replace(u"\r\n", u"\\n").replace(u"\n", u"\\n").replace(u"\t", u"\\t") + u"\"}"
        log.debug("    Conversion done. Loading JSON resource.")
        try:
            str_cache = json.loads(result)
            if extend:
                string_cache.update([(a, b) for (a, b) in str_cache.items() if a not in string_cache.keys()])
        except Exception, e:
            log.debug("Error while loading JSON resource:")
            log.debug("    %s"%e)
            log.debug("Dumping JSON data in %s.json"%lang)
            f = open('%s.json'%lang, 'w')
            f.write(result)
            f.close()
            return {}, False
#         log.debug("    Setting up font.") # Forgotten this here???
        if not extend:
            line = rawData.splitlines()[0]
            if "#-# " in line:
                lngNm = line.split("#-# ")[1].strip()
            else:
                lngNm = os.path.splitext(os.path.basename(fName))[0]
            try:
                resource.setCurLang(lngNm)
            except:
                resource.__curLang = lngNm
        tm1 = time()
        log.debug("  * End on %s duration %s"%(tm, tm1 - tm))
    else:
        log.debug("fName is not valid beacause:")
        if not os.access(fName, os.F_OK):
            log.debug("  * Can't access file.")
        if not os.path.isfile(fName):
            log.debug("  * It's not a file.")
        if not os.access(fName, os.R_OK):
            log.debug("  * Is not readable.")
        log.debug("Default strings will be used.")
        str_cache = {}
    if not extend:
        string_cache = str_cache
    log.debug("buildTranslation >>>")
    return string_cache, fileFound

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    ### FOR TEST
    import sys

    for k, v in buildTranslation("template").items():
        print k, v
    sys.exit()
    ###
