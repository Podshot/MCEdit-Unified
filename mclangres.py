# -*- coding: utf_8 -*-
#
# mclangres.py
#
# Collect the Minecraft internal translations.
#
'''
Uses `.minecraft/assets/indexes/[version].json`. The version is the highest
found by default.
'''

import re
import os
import codecs
from directories import getMinecraftLauncherDirectory, getDataDir
import logging
log = logging.getLogger(__name__)

indexesDirectory = os.path.join(getMinecraftLauncherDirectory(), 'assets', 'indexes')
objectsDirectory = os.path.join(getMinecraftLauncherDirectory(), 'assets', 'objects')

enRes = {}
serNe = {}
langRes = {}
serGnal = {}
enMisc = {}
csimNe = {}
langMisc = {}
csimGnal = {}

# Shall this be maintained in an external resource?
excludedEntries = ['tile.flower1.name',]

# Used to track untranslated and out dated MCEdit resources.
# Set it to true to generate/add entries to 'missingmclangres.txt' in MCEdit folder.
# Note that some strings may be falsely reported. (Especialy a '7 (Source)' one...)
# ! ! ! Please, pay attention to disable this befor releasing ! ! !
report_missing = False

def getResourceName(name, data):
    match = re.findall('"minecraft/lang/%s.lang":[ ]\{\b*.*?"hash":[ ]"(.*?)",'%name, data, re.DOTALL)
    if match:
        return match[0]
    else:
        log.debug('Could not find %s resource name.'%name)

def findResourceFile(name, basedir):
    for root, dirs, files in os.walk(basedir):
        if name in files:
            return os.path.join(basedir, root, name)

def buildResources(version=None, lang=None):
    """Loads the resource files and builds the resource dictionnaries.
    Four dictionnaries are built. Two for the refering language (English), and two for the language to be used.
    They are 'reversed' dictionnaries; the {foo: bar} pairs of one are the {bar: foo} of the other one."""
    log.debug('Building Minecraft language resources...')
    global enRes
    global serNe
    global langRes
    global serGnal
    global enMisc
    global csimEn
    global langMisc
    global csimGnal
    enRes = {}
    serNe = {}
    langRes = {}
    serGnal = {}
    enMisc = {}
    csimEn = {}
    langMisc = {}
    csimGnal = {}
    if not os.path.exists(indexesDirectory) or not os.path.exists(objectsDirectory):
        log.debug('Minecraft installation directory is not valid.')
        log.debug('Impossible to load the game language resources.')
        return
    versions = os.listdir(indexesDirectory)
    if 'legacy.json' in versions:
        versions.remove('legacy.json')
    if len(versions) == 0:
        log.debug("No valid versions found in minecraft install directory")
        return
    versions.sort()
    version = "%s.json"%version
    if version in versions:
        fName = os.path.join(indexesDirectory, version)
    else:
        fName = os.path.join(indexesDirectory, versions[-1])
    log.debug('Using %s'%fName)
    data = open(fName).read()
    name = getResourceName('en_GB', data)
    if name:
        fName = os.path.join(objectsDirectory, name[:2], name)
        if not os.path.exists(fName):
            fName = findResourceFile(name, objectsDirectory)
        if not fName:
            log.debug('Can\'t get the resource %s.'%name)
            log.debug('Nothing built. Aborted')
            return
        log.debug('Found %s'%name)
        lines = codecs.open(fName, encoding='utf_8').readlines()
        for line in lines:
            if line.split('.')[0] in ['book', 'enchantment', 'entity', 'gameMode', 'generator', 'item', 'tile'] and line.split('=')[0].strip() not in excludedEntries:
                enRes[line.split('=', 1)[-1].strip()] = line.split('=', 1)[0].strip()
                serNe[line.split('=', 1)[0].strip()] = line.split('=', 1)[-1].strip()
        lines = codecs.open(os.path.join(getDataDir(), 'Items', 'en_GB'), encoding='utf_8')
        for line in lines:
            enMisc[line.split('=', 1)[-1].strip()] = line.split('=', 1)[0].strip()
            csimNe[line.split('=', 1)[0].strip()] = line.split('=', 1)[-1].strip()
        log.debug('... Loaded!')
    else:
        return
    if not lang:
        lang = 'en_GB'
    log.debug('Looking for %s resources.'%lang)
    name = getResourceName(lang, data)
    if not name:
        lang = 'en_GB'
        name = getResourceName(lang, data)
    if name:
        fName = os.path.join(objectsDirectory, name[:2], name)
        if not os.path.exists(fName):
            fName = findResourceFile(name, objectsDirectory)
        if not fName:
            log.debug('Can\'t get the resource %s.'%name)
            return
        log.debug('Found %s...'%name)
        lines = codecs.open(fName, encoding='utf_8').readlines()
        for line in lines:
            if line.split('.')[0] in ['book', 'enchantment', 'entity', 'gameMode', 'generator', 'item', 'tile'] and line.split('=')[0].strip() not in excludedEntries:
                langRes[line.split('=', 1)[0].strip()] = line.split('=', 1)[-1].strip()
                serGnal[line.split('=', 1)[-1].strip()] = line.split('=', 1)[0].strip()
        if os.path.exists(os.path.join(getDataDir(), 'Items', lang)):
            lines = codecs.open(os.path.join(getDataDir(), 'Items', lang), encoding='utf_8')
            for line in lines:
                langMisc[line.split('=', 1)[0].strip()] = line.split('=', 1)[-1].strip()
                csimGnal[line.split('=', 1)[-1].strip()] = line.split('=', 1)[0].strip()
        log.debug('... Loaded!')
    else:
        return

def compound(char, string, pair=None):
    if pair is None:
        if char in '{[(':
            pair = '}])'['{[('.index(char)]
        else:
            pair = char
    name, misc = string.split(char, 1)
    name = name.strip()
    misc = [a.strip() for a in misc.strip()[:-1].split(',')]
    if (name not in enRes.keys() and name not in langRes.values()) and (name not in enMisc.keys() and name not in langMisc.values()):
        addMissing(name)
    head = langRes.get(enRes.get(name, name), name)
    for i in range(len(misc)):
        if ' ' in misc[i]:
            if langMisc.get(enMisc.get(misc[i], False), False):
                misc[i] = langMisc.get(enMisc.get(misc[i], misc[i]), misc[i])
            elif langRes.get(enRes.get(misc[i], False), False):
                misc[i] = langRes.get(enRes.get(misc[i], misc[i]), misc[i])
            else:
                stop = [False, False]
                for j in range(1, misc[i].count(' ') + 1):
                    elems = misc[i].rsplit(' ', j)
                    if not stop[0]:
                        h = elems[0]
                        if langMisc.get(enMisc.get(h, False), False):
                            h = langMisc.get(enMisc.get(h, h), h)
                            stop[0] = True
                        elif langRes.get(enRes.get(h, False), False):
                            h = langRes.get(enRes.get(h, h), h)
                            stop[0] = True
                    if not stop[1]:
                        t = u' '.join(elems[1:])
                        if langMisc.get(enMisc.get(t, False), False):
                            t = langMisc.get(enMisc.get(t, t), t)
                            stop[1] = True
                        elif langRes.get(enRes.get(t, False), False):
                            t = langRes.get(enRes.get(t, t), t)
                            stop[1] = True
                        if stop[0]:
                            stop[1] = True
                misc[i] = u' '.join((h, t))
                if (h not in enRes.keys() and h not in langRes.values()) and (h not in enMisc.keys() and h not in langMisc.values()):
                    addMissing(h, 'misc')
                if (t not in enRes.keys() and t not in langRes.values()) and (t not in enMisc.keys() and t not in langMisc.values()):
                    addMissing(t, 'misc')
        elif u'/' in misc[i]:
            misc[i] = u'/'.join([langMisc.get(enMisc.get(a, a), translate(a)) for a in misc[i].split('/')])
        elif '-' in misc[i]:
            misc[i] = u'-'.join([langMisc.get(enMisc.get(a, a), translate(a)) for a in misc[i].split('-')])
        elif '_' in misc[i]:
            misc[i] = u'_'.join([langMisc.get(enMisc.get(a, a), translate(a)) for a in misc[i].split('_')])
        else:
            misc[i] = langRes.get(enRes.get(misc[i], misc[i]), misc[i])
    tail = u'%s%s%s'%(char, u', '.join([langMisc.get(enMisc.get(a, a), a) for a in misc]), pair)
    return u' '.join((head, tail))

if report_missing:
    def addMissing(name, cat='base'):
        n = u''
        for a in name:
            if a == ' ' or a.isalnum():
                n += a
        elems = n.split(' ', 1)
        head = elems[0].lower()
        tail = ''
        if len(elems) > 1:
            tail = ''.join([a.capitalize() for a in elems[1].split(' ') if not a.isdigit()])
        if not n.isdigit():
            line = 'missing.%s.%s%s=%s\n'%(cat, head, tail, name)
            f = codecs.open(os.path.join(getDataDir(), 'missingmclangres.txt'), 'a+', encoding='utf_8')
            if line not in f.read():
                f.write(line)
            f.close()
else:
    def addMissing(*args, **kwargs): return

def translate(name):
    """Returns returns the translation of `name`, or `name` if no translation found.
    Can handle composed strings like: 'string_present_in_translations (other_string_1, other_string_2)'.
    Note that, in this case, the returned string may be partially translated."""
    for c in '{[(':
        if c in name:
            return compound(c, name)
    if report_missing:
        print '*', (name not in enRes.keys() and name not in langRes.values()) and (name not in enMisc.keys() and name not in langMisc.values()), name
    if (name not in enRes.keys() and name not in langRes.values()) and (name not in enMisc.keys() and name not in langMisc.values()):
        addMissing(name)
    return langRes.get(enRes.get(name, name), name)

def untranslate(name, case_sensitive=True):
    """Basic reverse function of `translate`."""
    key = serGnal.get(name, None)
    value = serNe.get(key, None)
    return value or name

def search(text, untranslate=False, capitalize=True, filters=[]):
    """Search for a `text` string in the resources entries.
    `filters` is a list of strings: they must be parts before the '=' sign in the resource files, or parts of.
    `filters` may be regexes.
    Returns a sorted list of matching elements."""
    # filters may contain regexes
    text = text.lower()
    results = []
    def get_result(l, w):
            if untranslate:
                if capitalize:
                    results.append('-'.join([b.capitalize() for b in ' '.join([a.capitalize() for a in serNe[w].split(' ')]).split('-')]))
                else:
                    results.append(serNe[w].lower())
            else:
                if capitalize:
                    results.append('-'.join([b.capitalize() for b in ' '.join([a.capitalize() for a in l.split(' ')]).split('-')]))
                else:
                    results.append(l.lower())
    for k, v in serGnal.items():
        if text in k.lower():
            if not filters or map(lambda (x,y):re.match(x,y), zip(filters, [v] * len(filters))) != [None, None]:
                if untranslate:
                    if capitalize:
                        results.append('-'.join([b.capitalize() for b in ' '.join([a.capitalize() for a in serNe[v].split(' ')]).split('-')]))
                    else:
                        results.append(serNe[v].lower())
                else:
                    if capitalize:
                        results.append('-'.join([b.capitalize() for b in ' '.join([a.capitalize() for a in k.split(' ')]).split('-')]))
                    else:
                        results.append(k.lower())
    results.sort()
    return results

