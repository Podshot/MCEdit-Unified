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
import re
import collections
import sys
from distutils.version import LooseVersion


log = getLogger(__name__)

def update_dict(orig_dict, new_dict):
    for key, val in new_dict.iteritems():
        if isinstance(val, collections.Mapping):
            if orig_dict.get(key, {}) == val:
                continue
            tmp = update_dict(orig_dict.get(key, { }), val)
            orig_dict[key] = tmp
        elif isinstance(val, list):
            if orig_dict.get(key, []) == val:
                continue
            orig_dict[key] = (orig_dict.get(key, []) + val)
        else:
            if orig_dict.get(key, None) == new_dict[key]:
                continue
            orig_dict[key] = new_dict[key]
    return orig_dict

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
    # Find if "autobuild" items are defined
    autobuilds = data.get("autobuild", {})
    for a_name, a_value in autobuilds.items():
        p = re.findall(r"(^|[ ])%s\['(\w+)'" % prefix, a_value)
        if p:
            for a in p[0][1:]:
                if a not in data.keys():
                    log.error("Found wrong reference while parsing autobuilds for %s: %s" % (prefix, a))
                    autobuilds.pop(a_name)
                else:
                    autobuilds[a_name] = a_value.replace("%s[" % prefix, "data[")
        else:
            # Just remove stuff which is not related to data internal stuff
            autobuilds.pop(a_name)

    for definition, value in data.iteritems():
        if definition == prefix:
            # We're parsing the block/entity/whatever data
            for item in value:
                _name = item.get('_name', item.get('idStr', u'%s' % item['id']))
                entry_name = "DEF_%s_%s" % (prefix.upper(), _name.upper())
                defs_dict[entry_name] = item
                ids_dict[item['id']] = ids_dict[_name] = entry_name
                if item.get('idStr'):
                    ids_dict[u'%s:%s' % (namespace, item['idStr'])] = ids_dict[item['idStr']] = entry_name
                for a_name, a_value in autobuilds.items():
                    try:
                        v = eval(a_value)
#                             print "###", a_name, a_value, v
                        defs_dict[entry_name][a_name] = eval(a_value)
                        ids_dict[v] = entry_name
                    except Exception as e:
                        log.error("An error occurred while autobuilding definitions %s (value: \"%s\": %s" % (a_name, a_value, e))
        else:
            # Build extra info in other defs
            defs_dict[definition] = value
    return defs_dict, ids_dict


def _get_data(file_name):
    data = {}
    try:
        fp = open(file_name)
        data = json.loads(fp.read())
        fp.close()
    except Exception as e:
        log.error("Could not load data from %s" % file_name)
        log.error("Error is: %s" % e)
    return data


def ids_loader(game_version, namespace=u"minecraft", json_dict=False, timestamps=False, directory=None, update=False):
    """Load the whole files from mcver directory.
    :game_version: str/unicode: the game version for which the resources will be loaded.
    :namespace: unicode: the name to be put in front of some IDs. default to 'minecraft'.
    :json_dict: bool: Whether to return a ran dict from the JSon file(s) instead of the (MCEDIT_DEFS, MCEDIT_IDS) pair.
    :timestamp: bool: wheter the return also the loaded file timestamp.
    :directory: string: Path to the directory where the json files lie.
        Defaults to None. In this case, the 'mcver' directory is used, otherwise, 'game_vaerion' is ignored.
    :update: bool: Whether to update the MCEDIT_DEFS nd MCEDIT_IDS objects. Defaults to False."""
    log.info("Loading resources for MC %s"%game_version)
    global MCEDIT_DEFS
    global MCEDIT_IDS
    if not update:
        MCEDIT_DEFS = {}
        MCEDIT_IDS = {}
    if json_dict:
        _json = {}
    if timestamps:
        _timestamps = {}
    if directory is None:
        d = os.path.join('mcver', game_version)
    else:
        d = directory

    # If version 1.2.4 files are not found, try to load the one for the closest
    # lower version (like 1.2.3 or 1.2).
    if not os.path.isdir(d) and game_version != "Unknown":
        log.info("No definitions found for MC %s. Trying to find ones for the closest lower version." % game_version)
        ver_dirs = os.listdir('mcver')
        ver_dirs.append(game_version)
        ver_dirs.sort(key=LooseVersion)
        idx = ver_dirs.index(game_version) - 1
        ver = ver_dirs[idx]
        d = os.path.join('mcver', ver)
        log.info("Closest lower version found is %s." % ver)

    if os.path.isdir(d):
        for file_name in os.listdir(d):
            if os.path.splitext(file_name)[-1].lower() == '.json':
                log.info("Found %s" % file_name)
                path_name = os.path.join(d, file_name)
                data = _get_data(path_name)
                if timestamps:
                    _timestamps[path_name] = os.stat(path_name).st_mtime
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
                            if json_dict:
                                _json.update(data)
                            first = False
                        else:
                            r = _parse_data(_data, prefix, namespace, MCEDIT_DEFS, MCEDIT_IDS)
                            if json_dict:
                                _json.update(_data)
                        if isinstance(r, (str, unicode)):
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
                                #_data.update(_get_data(_file_name))
                                update_dict(_data, _get_data(_file_name))
                                if timestamps:
                                    _timestamps[_file_name] = os.stat(_file_name).st_mtime
                            else:
                                log.info("Could not find %s"%_file_name)
                        update_dict(_data, data)
                        #_data.update(data)
                        _defs, _ids = _parse_data(_data, prefix, namespace, MCEDIT_DEFS, MCEDIT_IDS, ignore_load=True)
                        update_dict(MCEDIT_DEFS, _defs)
                        update_dict(MCEDIT_IDS, _ids)
                        #MCEDIT_DEFS.update(_defs)
                        #MCEDIT_IDS.update(_ids)
                        if json_dict:
                            _json.update(_data)
                    log.info("Done")
    else:
        log.info("MC %s resources not found."%game_version)
    # Override the module objects to expose them outside when (re)importing.
    pymclevel.MCEDIT_DEFS = MCEDIT_DEFS
    pymclevel.MCEDIT_IDS = MCEDIT_IDS
    log.info("Loaded %s defs and %s ids"%(len(MCEDIT_DEFS), len(MCEDIT_IDS)))
    toreturn = (MCEDIT_DEFS, MCEDIT_IDS)
    if json_dict:
        toreturn = _json
    if '--dump-defs' in sys.argv:
        dump_f_name = 'defs_ids-%s.json' % game_version
        log.info("Dumping definitions as Json data in '%s'." % dump_f_name)
        with open(dump_f_name, 'w') as f:
            f.write("#" * 80)
            f.write("\nDEFS\n")
            f.write(json.dumps(MCEDIT_DEFS, indent=4))
            f.write("\n\n" + "#" * 80)
            f.write("\nIDS\n")
            f.write(json.dumps(MCEDIT_IDS, indent=4))
            f.close()
    if timestamps:
        toreturn += (_timestamps,)
    return toreturn

version_defs_ids = {}

class MCEditDefsIds(object):
    """Class to handle MCEDIT_DEFS and MCEDIT_IDS dicts."""

    def __init__(self, game_version, namespace=u"minecraft"):
        """:game_version, namespace: See 'ids_loader() docstring'."""
        global version_defs_ids
        self.mcedit_defs, self.mcedit_ids, self.timestamps = ids_loader(game_version, namespace, timestamps=True)
        version_defs_ids[game_version] = self

    def check_timestamps(self, timestamps):
        """Compare the stored and current modification time stamp of files.
        :timestamps: dict: {"file_path": <modification timestamp>}
        Returns a list of files which has'nt same timestamp as stored."""
        result = []
        for file_name, ts in timestamps.items():
            if os.stat(file_name).st_mtime != ts:
                result.append(file_name)
        return result

    def get_id(self, obj_id):
        """Acts like MCEDIT_IDS[obj_id]"""
        return self.mcedit_ids[obj_id]

    def get_def(self, def_id):
        """Acts like MCEDIT_DEFS[def_id]"""
        return self.mcedit_defs[def_id]

def get_defs_ids(game_version, namespace=u"minecraft"):
    """Create a MCEditDefsIds instance only if one for the game version does not already exists, or a definition file has been changed.
    See MCEditDefsIds doc.
    Returns a MCEditDefsIds instance."""
    if game_version in version_defs_ids.keys():
        obj = version_defs_ids[game_version]
        timestamps = obj.timestamps
        if not obj.check_timestamps(timestamps):
            return obj
    else:
        return MCEditDefsIds(game_version, namespace=namespace)

