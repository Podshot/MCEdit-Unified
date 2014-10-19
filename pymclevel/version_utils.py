from nbt import *
import json
import urllib2
from directories import userCachePath
import os
import json
import time

def getPlayerNameFromUUID(uuid):
    try:
        t = time.time()
    except:
        t = 0
    nuuid = uuid.replace("-", "")
    try:
        if not os.path.exists(userCachePath):
            usercache = {}
            print "{} doesn't exist, will not cache".format(userCachePath)
        else:
            try:
                f = open(userCachePath,"r+")
                usercache = json.loads(f.read())
            except:
                print "Error loading {} from disk".format(userCachePath)
                usercache = {}

        try:
            if os.path.exists(userCachePath) and uuid in usercache and "timestamp" in usercache[uuid] and t-usercache[uuid]["timestamp"] < 21600:
                refreshUUID = False
            else:
                refreshUUID = False
        except:
            refreshUUID = True

        if refreshUUID:
            try:
                print "Loading {} from network".format(uuid)
                playerJSONResponse = urllib2.urlopen("https://api.mojang.com/user/profiles/{}/names".format(nuuid)).read()
                playerJSON = json.loads(playerJSONResponse)
                username = playerJSON[0]
                usercache[uuid] = {"username":username,"timestamp":t}
            except:
                print "Error loading {} from network".format(uuid)
                return uuid
        try:
            if os.path.exists(userCachePath):
                f.seek(0)
                f.write(json.dumps(usercache))
                f.close()
        except:
            print "Error writing {} to disk".format(userCachePath)
        return usercache[uuid]["username"]
    except:
        print "An error occured getting the username for {}".format(uuid)
        return uuid