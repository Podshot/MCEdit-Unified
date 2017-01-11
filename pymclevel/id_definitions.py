# id_definitions.py
#
# D.C.-G. (LaChal) 2016
#
# Load the data according to the game version from the versioned resources.
#
"""
The logic here is to load the JSON definitions for blocks, entities and tile entities for a given game version.

Data for each game version is contained in subfolders of the 'mcver' one. These subfolders are named with a game version:

mcver/
  + 1.2/
    - blocks.json
    - entities.json
    - tileentities.json
  + 1.2.3/
    - blocks.json
    - entities.json
    - tileentities.json
[etc.]

The JSON files can contain all the definitions for a version, or partial ones.
If definitions are partial, other game version files can be loaded by referencing this version in a "load" object like this:

'''
{
    "load": "1.2",
    "blocks": [snip...]
}
'''

Using the directory structure above, and assuming the code snippet comes from the 'block.json' file in the '1.2.3' subfolder,
the data in 'blocks.json' in the '1.2' subfolder will be loaded before the data in 'blocks.json' in '1.2.3'.
So '1.2.3' data will override '1.2' one.
"""

import os
import json
from logging import getLogger
from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
import pymclevel

log = getLogger(__name__)

def _parse_data(data, prefix, namespace, defs_dict, ids_dict, ignore_load=False):
    """Parse the JSON data and build objects accordingly.
    :data: JSON data.
    :prefix: unicode: the prefix to be used, basically 'blocks', 'entities' or 'tileentities'.
    :defs_dict: dict: the object to be populated with definitions; basically 'MCEDIT_DEFS' dict.
    :ids_dict: dict: the object to be populated with IDs; basically 'MCEDIT_IDS' dict.
    :ignore_load: bool: whether to break on the 'load' object if encountered in the JSON data. Used to track and load dependencies in the right order. Default to False.
    Return the 'load' object value if :ignore_load: is False and the object is present, or a tuple containing the updated 'defs_dict' and ids_dict' objects."""
    if not ignore_load and 'load' in data.keys():
        return data['load']
    for definition, value in data.iteritems():
        if definition == prefix:
            # We're parsing the block/entity/whatever data
            for item in value:
                _name = item.get('_name', item.get('idStr', u'%s'%item['id']))
                entry_name = "DEF_%s_%s"%(prefix.upper(), _name.upper())
                defs_dict[entry_name] = item
                ids_dict[item['id']] = ids_dict[_name] = entry_name
                if item.get('idStr'):
                    ids_dict[u'%s:%s'%(namespace, item['idStr'])] = ids_dict[item['idStr']] = entry_name
        else:
            # Build extra info in other defs
            defs_dict[definition] = value
    return defs_dict, ids_dict

def _get_data(file_name):
    data = {}
    try:
        data = json.loads(open(file_name).read())
    except Exception, e:
        log.error("Could not load data from %s"%file_name)
        log.error("Error is: %s"%e)
    return data

def ids_loader(game_version, namespace=u"minecraft"):
    """Load the whole files from mcver directory.
    :game_version: str/unicode: the game version for which the resources will be loaded.
    namespace: unicode: the name to be put in front of some IDs. default to 'minecraft'."""
    log.info("Loading resources for MC %s"%game_version)
    global MCEDIT_DEFS
    global MCEDIT_IDS
    MCEDIT_DEFS = {}
    MCEDIT_IDS = {}
    d = os.path.join('mcver', game_version)
    if os.path.isdir(d):
        for file_name in os.listdir(d):
            if os.path.splitext(file_name)[-1].lower() == '.json':
                data = None
                log.info("Found %s"%file_name)
                data = _get_data(os.path.join(d, file_name))
                if data:
                    # We use here names coming from the 'minecraft:name_of_the_stuff' ids
                    # The second part of the name is present in the first file used (for MC 1.11) in the 'idStr' value).
                    # The keys of MCEDIT_DEFS are built by concatening the file base name and the idStr
                    # References to MCEDIT_DEFS elements are stored in MCEDIT_IDS dict.
                    # If an element "load" is defined in the JSON data, it must be a string corresponding to another game version.
                    # The corresponding file will be loaded before parsing the data.
                    log.info("Loading...")
                    prefix = os.path.splitext(file_name)[0]
                    deps = []
                    r = ''
                    _data = {}
                    first = True
                    while type(r) in (str, unicode):
                        if first:
                            r = _parse_data(data, prefix, namespace, MCEDIT_DEFS, MCEDIT_IDS)
                            first = False
                        else:
                            r = _parse_data(_data, prefix, namespace, MCEDIT_DEFS, MCEDIT_IDS)
                        if type(r) in (str, unicode):
                            v = game_version
                            if len(deps):
                                v = deps[-1]
                            log.info("Found dependency for %s %s"%(v, prefix))
                            deps.append(r)
                            _data = _get_data(os.path.join('mcver', r, file_name))
                        else:
                            defs, ids = r
                            MCEDIT_DEFS.update(defs)
                            MCEDIT_IDS.update(ids)
                    if deps:
                        deps.reverse()
                        log.info("Loading definitions dependencies")
                        _data = {}
                        for dep in deps:
                            _file_name = os.path.join('mcver', dep, file_name)
                            if os.path.exists(_file_name):
                                log.info("Found %s"%_file_name)
                                _data.update(_get_data(_file_name))
                            else:
                                log.info("Could not find %s"%_file_name)
                        _data.update(data)
                        _defs, _ids = _parse_data(_data, prefix, namespace, MCEDIT_DEFS, MCEDIT_IDS, ignore_load=True)
                        MCEDIT_DEFS.update(_defs)
                        MCEDIT_IDS.update(_ids)
                    log.info("Done")
    else:
        log.info("MC %s resources not found."%game_version)
    # Override the module objects to expose them outside when (re)importing.
    pymclevel.MCEDIT_DEFS = MCEDIT_DEFS
    pymclevel.MCEDIT_IDS = MCEDIT_IDS
    log.info("Loaded %s defs and %s ids"%(len(MCEDIT_DEFS), len(MCEDIT_IDS)))
    return MCEDIT_DEFS, MCEDIT_IDS
