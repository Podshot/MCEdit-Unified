import json
import urllib2
from directories import userCachePath
import os
import time
import urllib
from PIL import Image
from urllib2 import HTTPError
import atexit
import threading
import logging
from uuid import UUID
from utilities.misc import deprecated, Singleton
import httplib
import base64

logger = logging.getLogger()

# TODO: Rewrite JSON structure (again) to be based off of non-seperated UUID's key, enough of iterating over lists
@Singleton
class PlayerCache:
    '''
    Used to cache Player names and UUID's, provides an small API to interface with it
    '''
    Instance = None
    _playerCacheList = []
    SKIN_URL = "https://sessionserver.mojang.com/session/minecraft/profile/{}"

    def __convert(self):
        jsonFile = None
        fp = open(userCachePath)
        try:
            jsonFile = json.load(fp)
            fp.close()
        except ValueError:
            fp.close()
            # Assuming JSON file is corrupted, deletes file and creates new one
            os.remove(userCachePath)
            with open(userCachePath, 'w') as json_out:
                json.dump([], json_out)
        if jsonFile is not None:
            for old_player in jsonFile.keys():
                player = jsonFile[old_player]
                new_player = {"Playername": player["username"], "UUID (No Separator)": old_player.replace("-", ""),
                              "UUID (Separator)": old_player, "WasSuccessful": True, "Timstamp": player["timestamp"]}
                self._playerCacheList.append(new_player)
            self._save()
            print "Convert usercache.json"
            
    def fixAllOfPodshotsBugs(self):
        '''
        Convenient function that fixes any bugs/typos (in the usercache.json file) that Podshot may have created
        '''
        for player in self._playerCacheList:
            # Timestamp type fixing
            if "Timstamp" in player:
                player["Timestamp"] = player["Timstamp"]
                del player["Timstamp"]
                
            if "Skin" not in player:
                player["Skin"] = {"Timestamp": time.time()}   
        self._save()
    
    def load(self):
        '''
        Loads from the usercache.json file if it exists, if not an empty one will be generated
        '''
        if not os.path.exists(userCachePath):
            out = open(userCachePath, 'w') 
            json.dump(self._playerCacheList, out)
            out.close()
        f = open(userCachePath, 'r')
        line = f.readline()
        if line.startswith("{"):
            f.close()
            self.__convert()
        f.close()
        try:
            json_in = open(userCachePath)
            self._playerCacheList = json.load(json_in)
        except:
            logger.warning("Usercache.json may be corrupted")
            self._playerCacheList = []
        finally:
            json_in.close()
        self.fixAllOfPodshotsBugs()
        self.refresh_lock = threading.Lock()
        self.player_refreshing = threading.Thread(target=self._refreshAll)
        self.player_refreshing.daemon = True
        self.player_refreshing.start()     

    def _save(self):
        out = open(userCachePath, "w")
        json.dump(self._playerCacheList, out, indent=4, separators=(',', ':'))
        out.close()
            
    def _removePlayerWithName(self, name):
        toRemove = None
        for p in self._playerCacheList:
            if p["Playername"] == name:
                toRemove = p
        if toRemove is not None:
            self._playerCacheList.remove(toRemove)
            self._save()
    
    def _removePlayerWithUUID(self, uuid, seperator=True):
        toRemove = None
        for p in self._playerCacheList:
            if seperator:
                if p["UUID (Separator)"] == uuid:
                    toRemove = p
            else:
                if p["UUID (No Separator)"] == uuid:
                    toRemove = p
        if toRemove is not None:
            self._playerCacheList.remove(toRemove)
            self._save()
            
    def nameInCache(self, name):
        '''
        Checks to see if the name is already in the cache
        
        :param name: The name of the player
        :type name: str
        :rtype: bool
        '''
        isInCache = False
        for p in self._playerCacheList:
            if p["Playername"] == name:
                isInCache = True
        return isInCache
    
    def uuidInCache(self, uuid, seperator=True):
        '''
        Checks to see if the UUID is already in the cache
        
        :param uuid: The UUID of the player
        :type uuid: str
        :param seperator: True if the UUID has separators ('-')
        :type seperator: bool
        :rtype: bool
        '''
        isInCache = False
        for p in self._playerCacheList:
            if seperator:
                if p["UUID (Separator)"] == uuid:
                    isInCache = True
            else:
                if p["UUID (No Separator)"] == uuid:
                    isInCache = True
        return isInCache
    
    def _refreshAll(self):
        with self.refresh_lock:
            playersNeededToBeRefreshed = []
            try:
                t = time.time()
            except:
                t = 0
            for player in self._playerCacheList:
                if player["Timestamp"] != "<Invalid>":
                    if t - player["Timestamp"] > 21600:
                        playersNeededToBeRefreshed.append(player)
            for player in playersNeededToBeRefreshed:
                #self.getPlayerFromUUID(player["UUID (Separator)"], forceNetwork=True, dontSave=True)
                self.getPlayerInfo(player["UUID (Separator)"], force=True)
                self._save()
    
    def force_refresh(self):
        '''
        Refreshes all players in the cache, regardless of how long ago the name was synced
        '''
        players = self._playerCacheList
        for player in players:
            self.getPlayerInfo(player["UUID (Separator)"], force=True)
            
    @deprecated
    def getPlayerFromUUID(self, uuid, forceNetwork=False, dontSave=False):
        player = {}
        response = None
        if forceNetwork:
            if self.uuidInCache(uuid):
                self._removePlayerWithUUID(uuid)
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
                player["Timestamp"] = time.time()
                self._playerCacheList.append(player)
                if not dontSave:
                    self._save()
                return playerJSON["name"]
            else:
                return uuid
        else:
            couldNotFind = False
            for p in self._playerCacheList:
                if p["UUID (Separator)"] == uuid and p["WasSuccessful"]:
                    couldNotFind = False
                    return p["Playername"]
                else:
                    couldNotFind = True
            if couldNotFind:
                result = self.getPlayerFromUUID(uuid, forceNetwork=True)
                if result == uuid:
                    player = {"Playername":"<Unknown>","UUID (Separator)":uuid,"UUID (No Separator)":uuid.replace("-",""),"Timestamp":"<Invalid>","WasSuccessful":False}
                    self._playerCacheList.append(player)
                    return uuid
    @deprecated
    def getPlayerFromPlayername(self, playername, forceNetwork=False, separator=True):
        response = None
        if forceNetwork:
            if self.nameInCache(playername):
                self._removePlayerWithName(playername)
            try:
                response = urllib2.urlopen("https://api.mojang.com/users/profiles/minecraft/{}".format(playername)).read()
            except urllib2.URLError:
                return playername
            if response is not None and response != "":
                playerJSON = json.loads(response)
                player = {"Playername": playername, "UUID (No Separator)": playerJSON["id"]}
                uuid = playerJSON["id"][:8]+"-"+playerJSON["id"][8:12]+"-"+playerJSON["id"][12:16]+"-"+playerJSON["id"][16:20]+"-"+playerJSON["id"][20:]
                player["UUID (Separator)"] = uuid
                player["WasSuccessful"] = True
                player["Timestamp"] = time.time()
                self._playerCacheList.append(player)
                self._save()
                if separator:
                    return uuid
                else:
                    return playerJSON["id"]
            else:
                return playername
        else:
            couldNotFind = False
            for p in self._playerCacheList:
                if p["Playername"] == playername and p["WasSuccessful"]:
                    couldNotFind = False
                    return p["UUID (Separator)"]
                else:
                    couldNotFind = True
            if couldNotFind:
                result = self.getPlayerFromPlayername(playername, forceNetwork=True)
                if result == playername:
                    player = {"Playername":playername,"UUID (Separator)":"<Unknown>","UUID (No Separator)":"<Unknown>","Timestamp":"<Invalid>","WasSuccessful":False}
                    self._playerCacheList.append(player)
                    return playername
    
    # 0 if for a list of the playernames, 1 is for a dictionary of all player data
    def getAllPlayersKnown(self, returnType=0, include_failed_lookups=False):
        '''
        Returns all players in the cache
        
        :param returnType: What type should be returned, 0 for a list of playernames, 1 for a dictionary of player data, with the key being the player name
        :type returnType: int
        :param include_failed_lookups: Whether all current failed lookups also be included
        :type include_failed_lookups: bool
        :return: All player data in the specified data structure
        :rtype: list or dict
        '''
        toReturn = None
        if returnType == 0:
            toReturn = []
            for p in self._playerCacheList:
                if p["WasSuccessful"]:
                    toReturn.append(p["Playername"])
                elif include_failed_lookups:
                    toReturn.append(p["Playername"])      
        elif returnType == 1:
            toReturn = {}
            for p in self._playerCacheList:
                if p["WasSuccessful"]:
                    toReturn[p["Playername"]] = p
                elif include_failed_lookups:
                    toReturn[p["Playername"]] = p
        return toReturn
    
    def getFromCacheUUID(self, uuid, seperator=True):
        '''
        Checks if the UUID is already in the cache
        
        :param uuid: The UUID that might be in the cache
        :type uuid: str
        :param seperator: Whether the UUID is seperated by -'s
        :type seperator: bool
        :return: The player data that is in the cache for the specified UUID, same format as getPlayerInfo()
        :rtype: tuple
        '''
        for player in self._playerCacheList:
            if seperator and player["UUID (Separator)"] == uuid:
                return player["UUID (Separator)"], player["Playername"], player["UUID (No Separator)"]
            elif player["UUID (No Separator)"] == uuid:
                return player["UUID (Separator)"], player["Playername"], player["UUID (No Separator)"]
            
    def getFromCacheName(self, name):
        '''
        Checks if the Player name is already in the cache
        
        :param name: The name of the Player that might be in the cache
        :return: The player data that is in the cache for the specified Player name, same format as getPlayerInfo()
        :rtype: tuple
        '''
        for player in self._playerCacheList:
            if name == player["Playername"]:
                return player["UUID (Separator)"], player["Playername"], player["UUID (No Separator)"]
    
    def getPlayerInfo(self, arg, force=False):
        '''
        Recommended method to call to get Player data. Roughly determines whether a UUID or Player name was passed in 'arg'
        
        :param arg: Either a UUID or Player name to retrieve from the cache/Mojang
        :type arg: str
        :param force: True if the Player name should be forcefully fetched from Mojang
        :type force: bool
        :return: A tuple with the data in this order: (UUID with separator, Player name, UUID without separator)
        :rtype: tuple
        '''
        try:
            UUID(arg, version=4)
            print "Arg is UUID"
            if self.uuidInCache(arg) and not force:
                return self.getFromCacheUUID(arg)
            else:
                return self._getPlayerInfoUUID(arg)
        except ValueError:
            print "Arg is name"
            if self.nameInCache(arg) and not force:
                return self.getFromCacheName(arg)
            else:
                return self._getPlayerInfoName(arg)
        
    def _getPlayerInfoUUID(self, uuid):
        response_name = None
        response_uuid = None
        player = {}
        if self.uuidInCache(uuid):
            self._removePlayerWithUUID(uuid)
            
        response_uuid = json.loads(self._getDataFromURL("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(uuid.replace("-", ""))))
        response_name = json.loads(self._getDataFromURL("https://api.mojang.com/users/profiles/minecraft/{}".format(response_uuid["name"])))
        if response_uuid is None or response_name is None:
            print "Caught value error while getting player info for "+uuid
            return uuid
        if response_name is not None and response_name != "" and response_uuid is not None and response_uuid != "":
            player["Playername"] = response_name["name"]
            player["UUID (Separator)"] = response_name["id"][:8]+"-"+response_name["id"][8:12]+"-"+response_name["id"][12:16]+"-"+response_name["id"][16:20]+"-"+response_name["id"][20:]
            player["UUID (No Separator)"] = response_name["id"]
            player["WasSuccessful"] = True
            player["Timestamp"] = time.time()
            self._playerCacheList.append(player)
            self._save()
            return player["UUID (Separator)"], player["Playername"], player["UUID (No Separator)"]
        else:
            return uuid
            #raise Exception("Couldn't find player")
    
    def _getPlayerInfoName(self, playername):
        response_name = None
        response_uuid = None
        player = {}
        if self.nameInCache(playername):
            self._removePlayerWithName(playername)
            
        response_name = json.loads(urllib2.urlopen("https://api.mojang.com/users/profiles/minecraft/{}".format(playername)).read())
        response_uuid = json.loads(urllib2.urlopen("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(response_name["id"])).read())
        if response_name is None or response_uuid is None:
            print "Caught value error while getting player info for "+playername
            return playername
        if response_name is not None and response_name != "" and response_uuid is not None and response_uuid != "":
            player["Playername"] = response_name["name"]
            player["UUID (Separator)"] = response_name["id"][:8]+"-"+response_name["id"][8:12]+"-"+response_name["id"][12:16]+"-"+response_name["id"][16:20]+"-"+response_name["id"][20:]
            player["UUID (No Separator)"] = response_name["id"]
            player["WasSuccessful"] = True
            player["Timestamp"] = time.time()
            self._playerCacheList.append(player)
            self._save()
            return player["UUID (Separator)"], player["Playername"], player["UUID (No Separator)"]
        else:
            return playername
            #raise Exception("Couldn't find player")
            
    def getPlayerDict(self, key, value):
        for player in self._playerCacheList:
            if player.get(key, None) == value:
                return player
        return None
            
    def getPlayerSkin(self, arg, force_download=True, instance=None):
        print "Getting skin for: {} ({}, {})".format(arg, force_download, instance)
        toReturn = 'char.png'
        try:
            os.mkdir("player-skins")
        except OSError:
            print "directory already exists"
        uuid_sep, name, uuid = self.getPlayerInfo(arg)
        print "Got uuid_sep, name uuid"
        player = self.getPlayerDict("UUID (Separator)", uuid_sep)
        skin_path = os.path.join("player-skins", uuid_sep.replace("-", "_") + ".png")
        print "Got player data"
        try:
            if not force_download and os.path.exists(skin_path):
                print "Didn't force download and skin already exists"
                skin = Image.open(skin_path)
                if skin.size == (64,64):
                    skin = skin.crop((0,0,64,32))
                    skin.save(skin_path)
                toReturn = skin_path
            elif force_download or not os.path.exists(skin_path):
                '''
                if (time.time() - player["Skin"]["Timestamp"]) >= 120:
                    if os.path.exists(skin_path):
                        return skin_path
                    else:
                        return toReturn
                '''    
                response = self._getDataFromURL(self.SKIN_URL.format(uuid))
                if response is not None:
                    parsed = self._parseSkinResponse(response)
                    if parsed is not None:
                        with open(skin_path, 'wb') as fp:
                            fp.write(parsed)
                        skin = Image.open(skin_path)
                        if skin.size == (64, 64):
                            skin = skin.crop((0,0,64,32))
                            skin.save(skin_path)
                        toReturn = skin_path
                        del player["Skin"]["Timestamp"]
                        player["Skin"]["Timestamp"] = time.time()
        except IOError:
            print "Couldn't find Image file ("+skin_path+") or the file may be corrupted"
            if instance is not None:
                instance.delete_skin(uuid_sep.replace("-","_"))
                os.remove(skin_path)
                print "Something happened, retrying"
                toReturn = self.getPlayerSkin(arg, True, instance)
        except Exception:
            import traceback
            print "Unknown error occurred while reading/downloading skin for "+str(uuid.replace("-","_")+".png")
            print traceback.format_exc()
        return toReturn
    
    def _getDataFromURL(self, url):
        try:
            print "Getting data from: {}".format(url)
            return urllib2.urlopen(url, timeout=10).read()
        except urllib2.HTTPError, e:
            print "Encountered a HTTPError"
            print "Error: " + str(e.code)
        except urllib2.URLError, e:
            print "Encountered an URLError"
            print "Error: " + str(e.reason)
        except httplib.HTTPException:
            print "Encountered a HTTPException"
        except Exception:
            import traceback
            print "Unknown error occurred while trying to get data from URL: " + url
            traceback.format_exc()
        return None
        
    
    def _parseSkinResponse(self, response):
        try:
            resp = json.loads(response)
            decoded = base64.b64decode(resp["properties"][0]["value"])
            resp = json.loads(decoded)
            if "SKIN" in resp["textures"]:
                resp = self._getDataFromURL(resp["textures"]["SKIN"]["url"])
                return resp
        except:
            import traceback
            print "Couldn't parse skin response JSON"
            traceback.format_exc()
        return None
            
    
    @staticmethod
    def __formats():
        player = {
                  "Playername":"<Username>",
                  "UUID (Separator)":"<uuid with the '-' separator>",
                  "UUID (No Separator)":"<uuid without the '-' separator",
                  "Timestamp":"<timestamp>",
                  # WasSuccessful will be true if the UUID/Player name was retrieved successfully
                  "WasSuccessful":True,
                  "Skin": {
                           "Timestamp":"<timestamp>",
                           }
                  }
        pass
    
    def cleanup(self):
        '''
        Removes all failed UUID/Player name lookups from the cache
        '''
        remove = []
        for player in self._playerCacheList:
            if not player["WasSuccessful"]:
                remove.append(player)
        for toRemove in remove:
            self._playerCacheList.remove(toRemove)
        self._save()
         
#_playercache = PlayerCache()
#_playercache.load()
#playercache = _playercache
PlayerCache.Instance().load()
            
@deprecated
def getUUIDFromPlayerName(player, seperator=True, forceNetwork=False):
    '''
    Old compatibility function for the PlayerCache method. It is recommended to use playercache.getPlayerInfo()
    '''
    return PlayerCache.Instance().getPlayerFromPlayername(player, forceNetwork, seperator)

@deprecated
def getPlayerNameFromUUID(uuid,forceNetwork=False):
    '''
    Old compatibility function for the PlayerCache method. It is recommended to use playercache.getPlayerInfo()
    '''
    return PlayerCache.Instance().getPlayerFromUUID(uuid, forceNetwork)     

def getPlayerSkin(uuid, force=False, trying_again=False, instance=None):
    '''
    Gets the player's skin from Mojang's skin servers
    
    :param uuid: The UUID of the player
    :type uuid: str
    :param force: Should the skin be redownloaded even if it has already been downloaded
    :type force: bool
    :param trying_again: True if the method already failed once
    :type trying_again: bool
    :param instance: The instance of the PlayerTool
    :type instance: PlayerTool
    :return: The path to the player skin
    :rtype: str
    '''
    '''
    playercache = PlayerCache.Instance()
    SKIN_URL = "http://skins.minecraft.net/MinecraftSkins/{}.png"
    toReturn = 'char.png'
    try:
        os.mkdir("player-skins")
    except OSError:
        pass
    if force or not os.path.exists(os.path.join("player-skins", uuid.replace("-", "_")+".png")):
        try:
            # Checks to see if the skin even exists
            urllib2.urlopen(SKIN_URL.format(playercache.getPlayerFromUUID(uuid, forceNetwork=False)))
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
            playername = playercache.getPlayerFromUUID(uuid,forceNetwork=False)
            urllib.urlretrieve(SKIN_URL.format(playername), os.path.join("player-skins", uuid.replace("-","_")+".png"))
            toReturn = os.path.join("player-skins", uuid.replace("-","_")+".png")
            player_skin = Image.open(toReturn)
            if player_skin.size == (64,64):
                player_skin = player_skin.crop((0,0,64,32))
                player_skin.save(os.path.join("player-skins", uuid.replace("-","_")+".png"))
    except IOError:
        print "Couldn't find Image file ("+str(uuid.replace("-","_")+".png")+") or the file may be corrupted"
        print "Trying to re-download skin...."
        if not trying_again and instance is not None:
            instance.delete_skin(uuid)
            os.remove(os.path.join("player-skins", uuid.replace("-","_")+".png"))
            toReturn = getPlayerSkin(uuid, force=True, trying_again=True)
        pass
    except HTTPError:
        print "Couldn't connect to a network"
        raise Exception("Could not connect to the skins server, please check your Internet connection and try again.")
        pass
    except Exception:
        print "Unknown error occurred while reading/downloading skin for "+str(uuid.replace("-","_")+".png")
        pass
    return toReturn
    '''
    return PlayerCache.Instance().getPlayerSkin(uuid, force, instance)
    #return 'char.png'

def _cleanup():
    if os.path.exists("player-skins"):
        for image_file in os.listdir("player-skins"):
            fp = None
            try:
                fp = open(os.path.join("player-skins", image_file), 'rb')
                Image.open(fp)
            except IOError:
                fp.close()
                os.remove(os.path.join("player-skins", image_file))
    PlayerCache.Instance().cleanup()
    
atexit.register(_cleanup)

