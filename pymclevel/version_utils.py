from nbt import *
import json
import urllib2
from directories import userCachePath
import os
import json


def getPlayerNameFromUUID(uuid):
    nuuid = uuid.replace("-", "")
    try:
        playerJSONResponse = urllib2.urlopen("https://api.mojang.com/user/profiles/{}/names".format(nuuid)).read()
        playerJSON = json.loads(playerJSONResponse)
        username = playerJSON[0]
        try:
            if os.path.exists(userCachePath):
                with open(userCachePath) as jsonString:
                    usercache = json.load(jsonString)
                usercache[uuid] = username
            else:
                usercache = {uuid:username}
# Write usercache.json (userCachePath)
        except:
            print "Unable to write to cache"
        return username
    except:
        try:
            if not os.path.exists(userCachePath):
                return uuid
            else:
                with open(userCachePath) as jsonString:
                    usercache = json.load(jsonString)
                return usercache[uuid]
        except:
            return uuid
# while True:
#print getPlayerNameFromUUID("11d0102c-4178-4953-9175-09bbd7d46264")