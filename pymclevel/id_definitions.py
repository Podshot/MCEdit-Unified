# id_definitions.py
#
# D.C.-G. (LaChal) 2016
#
# Load the data according to the game version from the versioned resources.
#
import os
import json
from logging import getLogger
from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
import pymclevel

log = getLogger(__name__)

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
                try:
                    data = json.loads(open(os.path.join(d, file_name)).read())
                except Exception, e:
                    log.error("Could not load data from %s"%file_name)
                    log.error("Error is: %s"%e)
                if data:
                    # We use here names coming from the 'minecraft:name_of_the_stuff' ids
                    # The second part of the name is present in the first file used (for MC 1.11) in the 'idStr' value).
                    # The keys of MCEDIT_DEFS are built by concatening the file base name and the idStr
                    # References to MCEDIT_DEFS elements are stored in MCEDIT_IDS dict.
                    log.info("Loading...")
                    prefix = os.path.splitext(file_name)[0]
                    for definition, value in data.iteritems():
                        if definition == prefix:
                            # We're parsing the block/entity/whatever data
                            for item in value:
                                _name = item.get('_name', item.get('idStr', u'%s'%item['id']))
                                entry_name = "DEF_%s_%s"%(prefix.upper(), _name.upper())
                                MCEDIT_DEFS[entry_name] = item
                                MCEDIT_IDS[item['id']] = MCEDIT_IDS[_name] = entry_name
                                if item.get('idStr'):
                                    MCEDIT_IDS[u'%s:%s'%(namespace, item['idStr'])] = MCEDIT_IDS[item['idStr']] = entry_name
                        else:
                            # Build extra info in other defs
                            MCEDIT_DEFS[definition] = value
                    log.info("Done")
    else:
        log.info("MC %s resources not found."%game_version)
    # Override the module objects to expose them outside when (re)ipmorting.
    pymclevel.MCEDIT_DEFS = MCEDIT_DEFS
    pymclevel.MCEDIT_IDS = MCEDIT_IDS
    return MCEDIT_DEFS, MCEDIT_IDS
