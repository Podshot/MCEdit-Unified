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
            usercache = {}
            print "Usercache doesn't exist, no caching"
        else:
            f = open(userCachePath,"r+")
            usercache = json.loads(f.read())

        refreshUUID = True
        if os.path.exists(userCachePath) and uuid in usercache and "timestamp" in usercache[uuid] and t-usercache[uuid]["timestamp"] < 21600:
            refreshUUID = False

        if refreshUUID:
            try:
                print "Loading file from network"
                playerJSONResponse = urllib2.urlopen("https://api.mojang.com/user/profiles/{}/names".format(nuuid)).read()
                playerJSON = json.loads(playerJSONResponse)
                username = playerJSON[0]
                usercache[uuid] = {"username":username,"timestamp":t}
            except:
                print "A network error occured"
                return uuid
            else:
                print "Loaded from network."

        if os.path.exists(userCachePath):
            f.seek(0)
            f.write(json.dumps(usercache))
            f.close()
        return usercache[uuid]["username"]
    except:
        print "Unable to r/w user cache file"
        return uuid