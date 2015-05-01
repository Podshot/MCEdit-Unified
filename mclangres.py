# -*- coding: utf_8 -*-
#
# mclangres.py
#
# Collect the Minecraft internal translations.
#
'''
Use `.minecraft/assets/indexes/[version].json`. The version is the highest
found by default.
Find the file name containing the en_GB translation (en_US seem to not be
present).
Load the en_GB file and build a dictionnary: {'string': 'element name'}.
Find the file name corresponding to the current MCEdit language, and build
a dictionnary: {'element name': 'string'}.
Retrieve the current MCEdit language translation with getting the 'element
name' in the English dictionnary and getting the 'string' in the current
language dictionnary using this 'element name'.
'''

import re
import os
import codecs
from directories import getMinecraftLauncherDirectory
import logging
log = logging.getLogger(__name__)

indexesDirectory = os.path.join(getMinecraftLauncherDirectory(), 'assets', 'indexes')
objectsDirectory = os.path.join(getMinecraftLauncherDirectory(), 'assets', 'objects')

enRes = {}
serNe = {}
langRes = {}
serGnal = {}

# Shall this be maintained in an external resource?
excludedEntries = ['tile.flower1.name',]

def getResourceName(name, data):
    match = re.findall('"minecraft/lang/%s.lang":[ ]\{\b*.*?"hash":[ ]"(.*?)",'%name, data, re.DOTALL)
    if match:
        return match[0]
    else:
        print 'Could not find %s resource name.'%name

def findResourceFile(name, basedir):
    for root, dirs, files in os.walk(basedir):
        if name in files:
            return os.path.join(basedir, root, name)

def buildResources(version=None, lang=None):
    log.debug('Building Minecraft language resources...')
    global enRes
    global serNe
    global langRes
    global serGnal
    enRes = {}
    serNe = {}
    langRes = {}
    serGnal = {}
    versions = os.listdir(indexesDirectory)
    if 'legacy.json' in versions:
        versions.remove('legacy.json')
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
        lines = codecs.open(fName).readlines()
        for line in lines:
            if line.split('=')[0].strip() not in excludedEntries:
                enRes[line.split('=', 1)[-1].strip()] = line.split('=', 1)[0].strip()
                serNe[line.split('=', 1)[0].strip()] = line.split('=', 1)[-1].strip()
        log.debug('... Loaded!')
    else:
        return
    if not lang:
        lang = 'en_GB'
    log.debug('Looking for %s resources.'%lang)
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
            if line.split('=')[0].strip() not in excludedEntries:
                langRes[line.split('=', 1)[0].strip()] = line.split('=', 1)[-1].strip()
                serGnal[line.split('=', 1)[-1].strip()] = line.split('=', 1)[0].strip()
        log.debug('... Loaded!')
    else:
        return

def translate(name):
    return langRes.get(enRes.get(name, name), name)

def untranslate(name):
    key = serGnal.get(name, None)
    value = serNe.get(key, None)
    return value or name

