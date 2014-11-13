import json
import urllib2
from directories import userCachePath, getDataDir
import os
import time
import base64  # @UnusedImport
from pymclevel.mclevelbase import PlayerNotFound
import urllib
from PIL import Image

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

def getUUIDFromPlayerName(player, seperator=True, forceNetwork=False):
    if forceNetwork:
        try:
            print "Loading {} from network".format(player)
            playerJSONResponse = urllib2.urlopen("https://api.mojang.com/users/profiles/minecraft/{}".format(player)).read()
            playerJSON = json.loads(playerJSONResponse)
            if seperator:
                return "-".join((playerJSON["id"][:8], playerJSON["id"][8:12], playerJSON["id"][12:16], playerJSON["id"][16:20], playerJSON["id"][20:]))
            else:
                return playerJSON["id"]
        except:
            raise PlayerNotFound(player)
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
                uuid = [x for x in usercache if usercache[x]["username"].lower() == player.lower()][0]
                if os.path.exists(userCachePath) and uuid in usercache and "timestamp" in usercache[uuid] and t-usercache[uuid]["timestamp"] < 21600:
                    refreshUUID = False
                else:
                    refreshUUID = True
            except:
                refreshUUID = True

            if refreshUUID:
                uuid = getUUIDFromPlayerName(player, seperator, True)
                    
                try:
                    usercache[uuid] = {"username":getPlayerNameFromUUID(uuid, True),"timestamp":t}
                except:
                    print "Error updating {} from network. Using last known".format(uuid)
                    return uuid
            try:
                if os.path.exists(userCachePath):
                    f.seek(0)
                    f.write(json.dumps(usercache))
                    f.close()
            except:
                print "Error writing {} to disk".format(userCachePath)
            print usercache[uuid]
            return uuid

        except:
            print "Error getting the uuid for {}".format(player)
            raise PlayerNotFound(player)

def getPlayerNameFromUUID(uuid,forceNetwork=False):
    '''
    Gets the Username from a UUID
    :param uuid: The Player's UUID
    :param forceNetwork: Forces use Mojang's API instead of first looking in the usercache.json
    '''
    if forceNetwork:
        try:
            print "Loading {} from network".format(uuid)
            nuuid = uuid.replace("-", "")
            playerJSONResponse = urllib2.urlopen("https://api.mojang.com/user/profiles/{}/names".format(nuuid)).read()
            playerJSON = json.loads(playerJSONResponse)
            return playerJSON[0]
        except:
            raise PlayerNotFound(uuid)
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
        
def getPlayerSkin(uuid, force=False):
    toReturn = 'char.png'
    if os.path.exists("player-skins"+os.path.sep+uuid.replace("-","_")+".png") and not force:
        return "player-skins"+os.path.sep+uuid.replace("-","_")+".png"
    try:
        os.mkdir("player-skins")
    except OSError:
        pass
    playerJSONResponse = urllib2.urlopen("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(uuid.replace("-",""))).read()
    playerJSON = json.loads(playerJSONResponse)
    for entry in playerJSON["properties"]:
        if entry["name"] == "textures":
            texturesJSON = json.loads(base64.b64decode(entry["value"]))
            urllib.urlretrieve(texturesJSON["textures"]["SKIN"]["url"], "player-skins"+os.path.sep+uuid.replace("-","_")+".png")
            toReturn = "player-skins"+os.path.sep+uuid.replace("-","_")+".png"
    player_skin = Image.open(toReturn)
    if player_skin.size == (64,64):
        player_skin.crop((0,0,64,32)).save(toReturn)
    return toReturn