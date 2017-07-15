import os
import json
from logging import getLogger
import collections
#from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
#import pymclevel
import re
#import id_definitions

log = getLogger(__name__)

def get_deps(base_version, file_name):
    deps = [base_version]
    print "Base: {}".format(base_version)
    fp = open(os.path.join('mcver', base_version, file_name))
    data = json.loads(fp.read())
    fp.close()
    if "load" in data:
        deps.extend(get_deps(data["load"], file_name))
    return deps

def update(orig_dict, new_dict):
    for key, val in new_dict.iteritems():
        if isinstance(val, collections.Mapping):
            tmp = update(orig_dict.get(key, { }), val)
            orig_dict[key] = tmp
        elif isinstance(val, list):
            orig_dict[key] = (orig_dict.get(key, []) + val)
        else:
            orig_dict[key] = new_dict[key]
    return orig_dict


def aggregate(base_version, file_name):
    deps = get_deps(base_version, file_name)
    deps.reverse()
    print deps
    aggregate_data = {}
    for dep in deps:
        fp = open(os.path.join('mcver', dep, file_name))
        data = json.loads(fp.read())
        fp.close()
        update(aggregate_data, data)
    print aggregate_data
    with open("out.json", 'wb') as out:
        json.dump(aggregate_data, out)

#print get_deps("1.12", "entities.json")
aggregate("1.12", "entities.json")


