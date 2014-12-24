import json
import urllib2
from directories import userCachePath, getDataDir
import os
import time
import base64  # @UnusedImport
from pymclevel.mclevelbase import PlayerNotFound
import urllib
from PIL import Image
from urllib2 import HTTPError

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

class __PlayerCache:
    
    SUCCESS = 0
    FAILED = 1

    def __convert(self):
        jsonFile = None
        try:
            jsonFile = json.load(open(userCachePath))
        except ValueError:
            # Assuming JSON file is corrupted, deletes file and creates new one
            os.remove(userCachePath)
            with open(userCachePath, 'w') as json_out:
                json.dump([], json_out)
        if jsonFile is not None:
            for old_player in jsonFile.keys():
                player = jsonFile[old_player]
                new_player = {}
                new_player["Playername"] = player["username"]
                new_player["UUID (No Separator)"] = old_player.replace("-","")
                new_player["UUID (Separator)"] = old_player
                new_player["WasSuccessful"] = True
                new_player["Timstamp"] = player["timestamp"]
                self._playerCacheList.append(new_player)
            self._save()
            print "Convert usercache.json"
    
    
    def __init__(self):
        self._playerCacheList = []
        if not os.path.exists(userCachePath):
            with open(userCachePath, "w") as out:
                json.dump(self._playerCacheList, out)
        with open(userCachePath) as f:
            line = f.readline()
            if line.startswith("{"):
                self.__convert();
        try:
            with open(userCachePath) as json_in:
                self._playerCacheList = json.load(json_in)
        except:
            print "usercache.json is corrupted"
    

    def _save(self):
        with open(userCachePath, "w") as out:
            json.dump(self._playerCacheList, out)
    
    
    def getPlayerFromUUID(self, uuid, forceNetwork=False):
        player = {}
        if forceNetwork:
            response = None
            try:
                response = urllib2.urlopen("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(uuid.replace("-",""))).read()
            except urllib2.URLError:
                return uuid
            if response is not None and response != "":
                playerJSON = json.loads(response)
                player["Playername"] = playerJSON["name"]
                player["UUID (No Separator)"] = playerJSON["id"]
                player["UUID (Separator)"] = uuid
                player["WasSuccessful"] = True
                player["Timstamp"] = time.time()
                self._playerCacheList.append(player)
                self._save()
                return playerJSON["name"]
            else:
                return uuid
        else:
            for p in self._playerCacheList:
                if p["UUID (Separator)"] == uuid and p["WasSuccessful"]:
                    return p["Playername"]
            result = self.getPlayerFromUUID(uuid, forceNetwork=True)
            if result == uuid:
                player = {"Playername":"<Unknown>","UUID (Separator)":uuid,"UUID (No Separator)":uuid.replace("-",""),"Timestamp":"<Invalid>","WasSuccessful":False}
                self._playerCacheList.append(player)
                return uuid
    
    def getPlayerFromPlayername(self, playername, forceNetwork=False, separator=True):
        if forceNetwork:
            response = None
            try:
                response = urllib2.urlopen("https://api.mojang.com/users/profiles/minecraft/{}".format(playername)).read()
            except urllib2.URLError:
                return playername
            if response is not None and response != "":
                playerJSON = json.loads(response)
                player = {}
                player["Playername"] = playername
                player["UUID (No Separator)"] = playerJSON["id"]
                uuid = playerJSON["id"][:4]+"-"+playerJSON["id"][4:8]+"-"+playerJSON["id"][8:12]+"-"+playerJSON["id"][12:16]+"-"+playerJSON["id"][16:]
                player["UUID (Separator)"] = uuid
                player["WasSuccessful"] = True
                player["Timstamp"] = time.time()
                self._playerCacheList.append(player)
                self._save()
                if separator:
                    return uuid
                else:
                    return playerJSON["id"]
            else:
                return playername
        else:
            for p in self._playerCacheList:
                if p["Playername"] == playername and p["WasSuccessful"]:
                    return p["UUID (Separator)"]
            result = self.getPlayerFromPlayername(playername, forceNetwork=True)
            if result == self.FAILED:
                player = {"Playername":playername,"UUID (Separator)":"<Unknown>","UUID (No Separator)":"<Unknown>","Timestamp":"<Invalid>","WasSuccessful":False}
                self._playerCacheList.append(player)
                return playername
    
    # 0 if for a list of the playernames, 1 is for a dictionary of all player data
    def getAllPlayersKnown(self, returnType=0):
        toReturn = None
        if returnType == 0:
            toReturn = []
            for p in self._playerCacheList:
                toReturn.append(p["Playername"])
        elif returnType == 1:
            toReturn = {}
            for p in self._playerCacheList:
                toReturn[p["Playername"]] = p
        return toReturn        
        
    
    def __formats(self):
        player = {
                  "Playername":"<Username>",
                  "UUID":"<uuid>",
                  "Timestamp":"<timestamp>",
                  # WasSuccessful will be true if the UUID/Player name was retrieved successfully
                  "WasSuccessful":True
                  }
        pass
                
playercache = __PlayerCache()
            
def getUUIDFromPlayerName(player, seperator=True, forceNetwork=False):
    return playercache.getPlayerFromPlayername(player, forceNetwork, seperator)
    '''
    if forceNetwork:
        try:
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
                    f = open(userCachePath,"r+")
                    usercache = json.loads(f.read())
                except:
                    print "Error loading {} from disk".format(userCachePath)

                    os.remove(userCachePath)
                    f = open(userCachePath, 'ar+')
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
            return uuid

        except:
            print "Error getting the uuid for {}".format(player)
            raise PlayerNotFound(player)
    '''

def getPlayerNameFromUUID(uuid,forceNetwork=False):
    '''
    Gets the Username from a UUID
    :param uuid: The Player's UUID
    :param forceNetwork: Forces use Mojang's API instead of first looking in the usercache.json
    '''
    return playercache.getPlayerFromUUID(uuid, forceNetwork)
    '''
    if forceNetwork:
        try:
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
                    f = open(userCachePath,"r+")
                    usercache = json.loads(f.read())
                except:
                    print "Error loading {} from disk".format(userCachePath)
                    
                    os.remove(userCachePath)
                    f = open(userCachePath, 'ar+')
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
                return usercache[uuid]["username"]
            except:
                print "Error returning uuid"
                return uuid
        except:
            print "Error getting the username for {}".format(uuid)
            return uuid
    '''
        
def getPlayerSkin(uuid, force=False, trying_again=False, instance=None):
    SKIN_URL = "http://skins.minecraft.net/MinecraftSkins/{}.png"
    toReturn = 'char.png'
    try:
        os.mkdir("player-skins")
    except OSError:
        pass
    try:
        # Checks to see if the skin even exists
        urllib2.urlopen(SKIN_URL.format(playercache.getPlayerFromUUID(uuid, forceNetwork=True)))
    except urllib2.URLError as e:
        if "Not Found" in e.msg:
            return toReturn
    try:
        if os.path.exists(os.path.join("player-skins", uuid.replace("-", "_")+".png")) and not force:
            player_skin = Image.open(os.path.join("player-skins", uuid.replace("-","_")+".png"))
            if player_skin.size == (64,64):
                player_skin = player_skin.crop((0,0,64,32))
                player_skin.save(os.path.join("player-skins", uuid.replace("-","_")+".png"))
            toReturn = os.path.join("player-skins", uuid.replace("-","_")+".png")
        else:
            playername = playercache.getPlayerFromUUID(uuid,forceNetwork=True)
            urllib.urlretrieve(SKIN_URL.format(playername), os.path.join("player-skins", uuid.replace("-","_")+".png"))
            toReturn = os.path.join("player-skins", uuid.replace("-","_")+".png")
            player_skin = Image.open(toReturn)
            if player_skin.size == (64,64):
                player_skin = player_skin.crop((0,0,64,32))
                player_skin.save(os.path.join("player-skins", uuid.replace("-","_")+".png"))
    except IOError:
        print "Couldn't find Image file ("+str(uuid.replace("-","_")+".png")+") or the file may be corrupted"
        print "Trying to re-download skin...."
        if not trying_again and instance != None:
            instance.delete_skin(uuid)
            os.remove(os.path.join("player-skins", uuid.replace("-","_")+".png"))
            toReturn = getPlayerSkin(uuid, force=True, trying_again=True)
        pass
    except HTTPError:
        print "Couldn't connect to a network"
        raise Exception("Could not connect to the skins server, please check your Internet connection and try again.")
        pass
    except Exception, e:
        print "Unknown error occurred while reading/downloading skin for "+str(uuid.replace("-","_")+".png")
        pass
    return toReturn
