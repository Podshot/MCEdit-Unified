from nbt import *
import json
import urllib2
from directories import userCachePath
import os
import json
import time

def getPlayerNameFromUUID(uuid):
    t = time.time()
    nuuid = uuid.replace("-", "")
    try:
        if not os.path.exists(userCachePath):
            f = open(userCachePath,"w")
            f.write("{}")
            f.close()
        f = open(userCachePath,"r+")

        try:
            usercache = json.load(f)
        except:
            usercache = {}

        refreshUUID = True
        if uuid in usercache and "timestamp" in usercache[uuid] and t-usercache[uuid]["timestamp"] < 21600:
            refreshUUID = False

        if refreshUUID:
            try:
                playerJSONResponse = urllib2.urlopen("https://api.mojang.com/user/profiles/{}/names".format(nuuid)).read()
                playerJSON = json.loads(playerJSONResponse)
                username = playerJSON[0]
                usercache[uuid] = {"username":username,"timestamp":t}
            except:
                print "A network error occured"
                return uuid

        f.write(json.dumps(usercache))
        f.close()
        return usercache[uuid]["username"]
    except:
        print "Unable to r/w user cache file"
        return uuid