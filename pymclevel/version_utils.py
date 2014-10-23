from nbt import *
import json
import urllib2
from directories import userCachePath
import os
import json
import time
import base64

#def getPlayerSkinURL(uuid):
#    try:
#        playerJSONResponse = urllib2.urlopen('https://sessionserver.mojang.com/session/minecraft/profile/{}'.format(uuid))
#        print playerJSONResponse
#        texturesJSON = json.loads(playerJSONResponse)['properties']
#        for prop in properties:
#            if prop['name'] == 'textures':
#                b64 = base64.b64decode(prop['value']);
#                print b64
#                return json.loads(b64)['textures']['SKIN']['url']
#    except:
#        raise

#print getPlayerSkinURL('4566e69fc90748ee8d71d7ba5aa00d20')

def getPlayerNameFromUUID(uuid,forceNetwork=False):
    if forceNetwork:
        try:
            print "Loading {} from network".format(uuid)
            nuuid = uuid.replace("-", "")
            playerJSONResponse = urllib2.urlopen("https://api.mojang.com/user/profiles/{}/names".format(nuuid)).read()
            playerJSON = json.loads(playerJSONResponse)
            return playerJSON[0]
        except:
            raise
    else:
        try:
            t = time.time()
        except:
            t = 0
        try:
            if not os.path.exists(userCachePath):
                usercache = {}
                print "{} doesn't exist, will not cache".format(userCachePath)
            else:
                try:
                    print "Reading {} from disk".format(userCachePath)
                    f = open(userCachePath,"r+")
                    usercache = json.loads(f.read())
                except:
                    print "Error loading {} from disk".format(userCachePath)
                    usercache = {}

            try:
                if os.path.exists(userCachePath) and uuid in usercache and "timestamp" in usercache[uuid] and t-usercache[uuid]["timestamp"] < 21600:
                    refreshUUID = False
                else:
                    refreshUUID = True
            except:
                refreshUUID = True

            if refreshUUID:
                try:
                    usercache[uuid] = {"username":getPlayerNameFromUUID(uuid,True),"timestamp":t}
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
            try:
                print usercache[uuid]
                return usercache[uuid]["username"]
            except:
                print "Error returning uuid"
                return uuid
        except:
            print "Error getting the username for {}".format(uuid)
            return uuid