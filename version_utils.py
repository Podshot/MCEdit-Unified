import json
import urllib2
from directories import userCachePath
import os
import time
from PIL import Image
import atexit
import threading
import logging
from uuid import UUID
import httplib
import base64
import datetime

log = logging.getLogger(__name__)

#@Singleton
class PlayerCache:
    '''
    Used to cache Player names and UUID's, provides an small API to interface with it
    '''
    
    PATH = userCachePath
    TIMEOUT = 2.5
    
    __shared_state = {}
    
    def __init__(self):
        self.__dict__ = self.__shared_state
    
    # --- Utility Functions ---
    @staticmethod
    def insertSeperators(uuid):
        return uuid[:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:]
    
    @staticmethod
    def getDeltaTime(timestamp, unit):
        t = time.time()
        old = datetime.datetime.fromtimestamp(timestamp)
        current = datetime.datetime.fromtimestamp(t)
        delta = current - old
        return getattr(delta, unit, "hours")
    
    def __convert(self, json_in):
        for player in json_in:
            new_dict = {}
            new_dict["Name"] = player["Playername"]
            new_dict["Timestamp"] = player["Timestamp"]
            new_dict["Successful"] = player["WasSuccessful"]
            self._cache["Cache"][player["UUID (No Separator)"]] = new_dict
            
    def save(self):
        if hasattr(self, "_cache"):
            fp = open(self.PATH, 'w')
            json.dump(self._cache, fp, indent=4, separators=(',', ':'))
            fp.close()
    
    def load(self):
        '''
        Loads from the usercache.json file if it exists, if not an empty one will be generated
        '''
        self._cache = {"Version": 2, "Connection Timeout": 2.5, "Cache": {}}
        if not os.path.exists(self.PATH):
            fp = open(self.PATH, 'w')
            json.dump(self._cache, fp)
            fp.close()
        fp = open(self.PATH, 'r')
        try:
            json_in = json.load(fp)
            if "Version" not in json_in or json_in.get("Version", 0) != 2:
                self.__convert(json_in)
            else:
                self._cache = json_in
        except:
            log.warning("Usercache.json may be corrupted")
        finally:
            fp.close()
        self.temp_skin_cache = {}
        self.TIMEOUT = self._cache.get("Connection Timeout", 2.5)
        self.cache_lock = threading.RLock()
        self.player_refeshing = threading.Thread(target=self._batchRefreshPlayers)
        #self.player_refeshing.daemon(True) # No idea whether to use the property setter function or the attribute, so I'll use both
        self.player_refeshing.daemon = True
        self.player_refeshing.start()
        
    # --- Refreshing ---
    def _batchRefreshPlayers(self):
        to_refresh_successful = []
        to_refresh_failed = []
        to_refresh = []
        with self.cache_lock:
            # TODO: Put this into a thread, since it could take alot of time to run
            # TODO: Handle entries that weren't successful last time the cache was modified
        
            for uuid in self._cache["Cache"].keys():
                player = self._cache["Cache"][uuid]
                if player["Successful"]:
                    if self.getDeltaTime(player["Timestamp"], "hours") > 6:
                        to_refresh_successful.append(uuid)
                else:
                    to_refresh_failed.append(uuid)
                
            to_refresh = to_refresh_successful + to_refresh_failed
            for uuid in to_refresh:
                self._getPlayerInfoUUID(uuid)
        self.save()
        
    def force_refresh(self):
        for uuid in self._cache["Cache"].keys():
            self.getPlayerInfo(uuid, force=True)
        self.save()
        
            
    # --- Checking if supplied data is in the Cache ---
    def UUIDInCache(self, uuid):
        '''
        Checks to see if the UUID is already in the cache
        
        :param uuid: The UUID of the player
        :type uuid: str
        :rtype: bool
        '''
        return uuid.replace("-", "") in self._cache["Cache"]
    
    def nameInCache(self, name):
        '''
        Checks to see if the name is already in the cache
        
        :param name: The name of the player
        :type name: str
        :rtype: bool
        '''
        for uuid in self._cache["Cache"].keys():
            if self._cache["Cache"][uuid].get("Name", "") == name:
                return True
        return False
    
    # --- Getting data from the Cache ---
    def _getDataFromCacheUUID(self, uuid):
        '''
        Checks if the UUID is already in the cache
        
        :param uuid: The UUID that might be in the cache
        :type uuid: str
        :return: The player data that is in the cache for the specified UUID, same format as getPlayerInfo()
        :rtype: tuple
        '''
        clean_uuid = uuid.replace("-","")
        player = self._cache["Cache"].get(clean_uuid, {})
        return (self.insertSeperators(clean_uuid), player.get("Name", "<Unknown Name>"), clean_uuid)
    
    def _getDataFromCacheName(self, name):
        '''
        Checks if the Player name is already in the cache
        
        :param name: The name of the Player that might be in the cache
        :return: The player data that is in the cache for the specified Player name, same format as getPlayerInfo()
        :rtype: tuple
        '''
        for uuid in self._cache["Cache"].keys():
            clean_uuid = uuid.replace("-","")
            player = self._cache["Cache"][uuid]
            if player.get("Name", "") == name and player.get("Successful", False):
                return (self.insertSeperators(clean_uuid), player["Name"], clean_uuid)
        return ("<Unknown UUID>", name, "<Unknown UUID>")
    
    def _wasSuccessfulUUID(self, uuid):
        '''
        Returns whether retrieving the player data was Successful
        
        :param uuid: The UUID of the player to check
        :return: True if the last time the player data retrieval from Mojang's API was successful, False otherwise
        :rtype: bool
        '''
        clean_uuid = uuid.replace("-","")
        player = self._cache["Cache"].get(clean_uuid, {})
        return player.get("Successful", False)
    
    def _wasSuccessfulName(self, name):
        '''
        Returns whether retrieving the player data was Successful
        
        :param name: The name of the player to check
        :return: True if the last time the player data retrieval from Mojang's API was successful, False otherwise
        :rtype: bool
        '''
        for uuid in self._cache["Cache"].keys():
            player = self._cache["Cache"][uuid]
            if player.get("Name", "") == name:
                return player.get("Successful", False)
        return False
            
    def getPlayerInfo(self, arg, force=False, use_old_data=False):
        '''
        Recommended method to call to get Player data. Roughly determines whether a UUID or Player name was passed in 'arg'
        
        :param arg: Either a UUID or Player name to retrieve from the cache/Mojang's API
        :type arg: str
        :param force: True if the Player name should be forcefully fetched from Mojang's API
        :type force: bool
        :return: A tuple with the data in this order: (UUID with separator, Player name, UUID without separator)
        :rtype: tuple
        '''
        try:
            UUID(arg, version=4)
            if self.UUIDInCache(arg) and self._wasSuccessfulUUID(arg) and not force:
                return self._getDataFromCacheUUID(arg)
            else:
                return self._getPlayerInfoUUID(arg, use_old_data)
        except ValueError:
            if self.nameInCache(arg) and self._wasSuccessfulName(arg) and not force:
                return self._getDataFromCacheName(arg)
            else:
                return self._getPlayerInfoName(arg)
    
    # --- Player Data Getters ---
    def _getPlayerInfoUUID(self, uuid, use_old_data=False):
        clean_uuid = uuid.replace("-","")
        player = self._cache["Cache"].get(clean_uuid, {})
        response = self._getDataFromURL("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(clean_uuid))
        if response:
            try:
                data = response
                response = json.loads(response)
                player["Name"] = response.get("name", player.get("Name", "<Unknown Name>"))
                player["Timestamp"] = time.time()
                player["Successful"] = True
                self._cache["Cache"][clean_uuid] = player
                self.temp_skin_cache[clean_uuid] = data
                self.save()
                return (self.insertSeperators(clean_uuid), player["Name"], clean_uuid)
            except:
                player["Successful"] = False
                self._cache["Cache"][clean_uuid] = player
                if use_old_data and player.get("Name", "<Unknown Name>") != "<Unknown Name>":
                    return (self.insertSeperators(clean_uuid), player["Name"], clean_uuid)
                else:
                    return (self.insertSeperators(clean_uuid), "<Unknown Name>", clean_uuid)
        else:
            player["Successful"] = False
            self._cache["Cache"][clean_uuid] = player
            if use_old_data and player.get("Name", "<Unknown Name>") != "<Unknown Name>":
                return (self.insertSeperators(clean_uuid), player["Name"], clean_uuid)
            else:
                return (self.insertSeperators(clean_uuid), "<Unknown Name>", clean_uuid)
        
    def _getPlayerInfoName(self, name):
        response = self._getDataFromURL("https://api.mojang.com/users/profiles/minecraft/{}".format(name))
        if response:
            try:
                response = json.loads(response)
                uuid = response["id"]
                player = self._cache["Cache"].get(uuid,{})
                player["Name"] = response.get("name", player.get("Name", "<Unknown Name>"))
                player["Timestamp"] = time.time()
                player["Successful"] = True
                self._cache["Cache"][uuid] = player
                self.save()
                return (self.insertSeperators(uuid), player["Name"], uuid)
            except:
                return ("<Unknown UUID>", name, "<Unknown UUID>")           
        else:
            return ("<Unknown UUID>", name, "<Unknown UUID>")
        
    # --- Skin Getting ---
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
            print traceback.format_exc()
        return None
    
    def getPlayerSkin(self, arg, force_download=True, instance=None):
        '''
        Gets the player's skin from Mojang's skin servers
    
        :param uuid: The UUID of the player
        :type uuid: str
        :param force_download: Should the skin be re-downloaded even if it has already been downloaded
        :type force: bool
        :param instance: The instance of the PlayerTool
        :type instance: PlayerTool
        :return: The path to the player skin
        :rtype: str
        '''
        toReturn = 'char.png'
        
        uuid_sep, name, uuid = self.getPlayerInfo(arg)
        if uuid == "<Unknown UUID>":
            return toReturn
        player = self._cache["Cache"][uuid]
        skin_path = os.path.join("player-skins", uuid_sep.replace("-","_") + ".png")
        #temp_skin_path = os.path.join("player-skin", uuid_sep.replace("-","_") + ".temp.png")
        try:
            if not force_download and os.path.exists(skin_path):
                skin = Image.open(skin_path)
                if skin.size == (64,64):
                    skin = skin.crop((0,0,64,32))
                    skin.save(skin_path)
                toReturn = skin_path
            elif force_download or not os.path.exists(skin_path):
                if uuid in self.temp_skin_cache:
                    parsed = self._parseSkinResponse(self.temp_skin_cache[uuid])
                    if parsed is not None:
                        self._saveSkin(uuid, parsed)
                        toReturn = skin_path
                        player["Skin"] = { "Timestamp": time.time() }
                        self._cache["Cache"][uuid] = player
                        del self.temp_skin_cache[uuid]
                        self.save()
                else:
                    response = self._getDataFromURL("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(uuid))
                    if response is not None:
                        parsed = self._parseSkinResponse(response)
                        if parsed is not None:
                            self._saveSkin(uuid, parsed)
                            toReturn = skin_path
                            player["Skin"] = { "Timestamp": time.time() }
                            self._cache["Cache"][uuid] = player
                            self.save()
               
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
    
    def _saveSkin(self, uuid, data):
        if "-" not in uuid:
            uuid = self.insertSeperators(uuid)
            
        try:
            os.mkdir("player-skins")
        except OSError:
            pass
        
        skin_path = os.path.join("player-skins", uuid.replace("-","_") + ".png")
        
        with open(skin_path, 'wb') as fp:
            fp.write(data)
        skin = Image.open(skin_path)
        if skin.size == (64,64):
            skin = skin.crop((0,0,64,32))
            skin.save(skin_path)
                            
    def _getDataFromURL(self, url):
        import traceback
        try:
            response = urllib2.urlopen(url, timeout=self.TIMEOUT).read()
            return response
        except urllib2.HTTPError, e:
            log.warn("Encountered a HTTPError while trying to access \"" + url + "\"")
            log.warn("Error: " + str(e.code))
        except urllib2.URLError, e:
            log.warn("Encountered an URLError while trying to access \"" + url + "\"")
            log.warn("Error: " + str(e.reason))
        except httplib.HTTPException:
            log.warn("Encountered a HTTPException while trying to access \"" + url + "\"")
        except Exception:
            log.warn("Unknown error occurred while trying to get data from URL: " + url)
            log.warn(traceback.format_exc())
        return None
    
    def _postDataToURL(self, url, payload, headers):
        import traceback
        try:
            request = urllib2.Request(url, payload, headers)
            response = urllib2.urlopen(request, timeout=self.TIMEOUT).read()
            return response
        except urllib2.HTTPError, e:
            log.warn("Encountered a HTTPError while trying to POST to \"" + url + "\"")
            log.warn("Error: " + str(e.code))
        except urllib2.URLError, e:
            log.warn("Encountered an URLError while trying to POST to \"" + url + "\"")
            log.warn("Error: " + str(e.reason))
        except httplib.HTTPException:
            log.warn("Encountered a HTTPException while trying to POST to \"" + url + "\"")
        except Exception:
            log.warn("Unknown error occurred while trying to POST data to URL: " + url)
            log.warn(traceback.format_exc())
        return None
            
def _cleanup():
    if os.path.exists("player-skins"):
        for image_file in os.listdir("player-skins"):
            fp = None
            try:
                fp = open(os.path.join("player-skins", image_file), 'rb')
                im = Image.open(fp)
                if hasattr(im, 'close'):
                    im.close()
            except IOError:
                os.remove(os.path.join("player-skins", image_file))
            except AttributeError:
                pass # I have no idea why an Attribute Error is thrown on .close(), but this fixes it
            finally:
                if fp and not fp.closed:
                    fp.close()
    
atexit.register(_cleanup)
atexit.register(PlayerCache().save)
