import json
import urllib2
from directories import userCachePath
import os
import time
from PIL import Image
import atexit
import logging
from uuid import UUID
import httplib
import base64
import datetime
import traceback

from utilities.thread_utils import ThreadRS, threadable, threading

log = logging.getLogger(__name__)


#@Singleton
class PlayerCache:
    """
    Used to cache Player names and UUID's, provides an small API to interface with it
    """

    _PATH = userCachePath
    TIMEOUT = 2.5
    targets = [] # Used to send data update when subprocesses has finished.

    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state
        self.last_error = None
        self.error_count = 0

    # --- Utility Functions ---
    def add_target(self, target):
        global targets
        if target not in self.targets:
            self.targets.append(target)

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
            new_dict = {
                "Name": player["Playername"],
                "Timestamp": player["Timestamp"],
                "Successful": player["WasSuccessful"]
            }
            self._cache["Cache"][player["UUID (No Separator)"]] = new_dict

    def save(self):
        if hasattr(self, "_cache"):
            fp = open(self._PATH, 'w')
            json.dump(self._cache, fp, indent=4, separators=(',', ':'))
            fp.close()

    def load(self):
        """
        Loads from the usercache.json file if it exists, if not an empty one will be generated
        """
        self._cache = {"Version": 2, "Connection Timeout": 10, "Cache": {}}
        if not os.path.exists(self._PATH):
            fp = open(self._PATH, 'w')
            json.dump(self._cache, fp)
            fp.close()
        fp = open(self._PATH, 'r')
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
                if self.error_count >= 4:
                    break
                self._getPlayerInfoUUID(uuid)
        self.save()

    def force_refresh(self):
        for uuid in self._cache["Cache"].keys():
            self.getPlayerInfo(uuid, force=True)
        self.save()

    # --- Checking if supplied data is in the Cache ---
    def UUIDInCache(self, uuid):
        """
        Checks to see if the UUID is already in the cache

        :param uuid: The UUID of the player
        :type uuid: str
        :rtype: bool
        """
        return uuid.replace("-", "") in self._cache["Cache"]

    def nameInCache(self, name):
        """
        Checks to see if the name is already in the cache

        :param name: The name of the player
        :type name: str
        :rtype: bool
        """
        for uuid in self._cache["Cache"].keys():
            if self._cache["Cache"][uuid].get("Name", "") == name:
                return True
        return False

    # --- Getting data from the Cache ---
    def _getDataFromCacheUUID(self, uuid):
        """
        Checks if the UUID is already in the cache

        :param uuid: The UUID that might be in the cache
        :type uuid: str
        :return: The player data that is in the cache for the specified UUID, same format as getPlayerInfo()
        :rtype: tuple
        """
        clean_uuid = uuid.replace("-","")
        player = self._cache["Cache"].get(clean_uuid, {})
        return self.insertSeperators(clean_uuid), player.get("Name", "<Unknown Name>"), clean_uuid

    def _getDataFromCacheName(self, name):
        """
        Checks if the Player name is already in the cache

        :param name: The name of the Player that might be in the cache
        :return: The player data that is in the cache for the specified Player name, same format as getPlayerInfo()
        :rtype: tuple
        """
        for uuid in self._cache["Cache"].keys():
            clean_uuid = uuid.replace("-","")
            player = self._cache["Cache"][uuid]
            if player.get("Name", "") == name and player.get("Successful", False):
                return (self.insertSeperators(clean_uuid), player["Name"], clean_uuid)
        return ("<Unknown UUID>", name, "<Unknown UUID>")

    def _wasSuccessfulUUID(self, uuid):
        """
        Returns whether retrieving the player data was Successful

        :param uuid: The UUID of the player to check
        :return: True if the last time the player data retrieval from Mojang's API was successful, False otherwise
        :rtype: bool
        """
        clean_uuid = uuid.replace("-","")
        player = self._cache["Cache"].get(clean_uuid, {})
        return player.get("Successful", False)

    def _wasSuccessfulName(self, name):
        """
        Returns whether retrieving the player data was Successful

        :param name: The name of the player to check
        :return: True if the last time the player data retrieval from Mojang's API was successful, False otherwise
        :rtype: bool
        """
        for uuid in self._cache["Cache"].keys():
            player = self._cache["Cache"][uuid]
            if player.get("Name", "") == name:
                return player.get("Successful", False)
        return False

    def getPlayerInfo(self, arg, force=False, use_old_data=False):
        """
        Recommended method to call to get Player data. Roughly determines whether a UUID or Player name was passed in 'arg'

        :param arg: Either a UUID or Player name to retrieve from the cache/Mojang's API
        :type arg: str
        :param force: True if the Player name should be forcefully fetched from Mojang's API
        :type force: bool
        :param use_old_data: Fallback to old data even if force is True
        :type use_old_data: bool
        :return: A tuple with the data in this order: (UUID with separator, Player name, UUID without separator)
        :rtype: tuple
        """
        try:
            UUID(arg, version=4)
            if self.UUIDInCache(arg) and self._wasSuccessfulUUID(arg) and not force:
                return self._getDataFromCacheUUID(arg)
            else:
                r = self._getPlayerInfoUUID(arg, use_old_data)
                if r.__class__ == ThreadRS:
                    c = arg.replace('-', '')
                    return self.insertSeperators(c), 'Server not ready', c
        except ValueError:
            if self.nameInCache(arg) and self._wasSuccessfulName(arg) and not force:
                return self._getDataFromCacheName(arg)
            else:
                r = self._getPlayerInfoName(arg)
                if r.__class__ == ThreadRS:
                    return 'Server not ready', arg, 'Server not ready'
                else:
                    return r

    # --- Player Data Getters ---
    @threadable
    def _getPlayerInfoUUID(self, uuid, use_old_data=False):
        clean_uuid = uuid.replace("-", "")
        player = self._cache["Cache"].get(clean_uuid, {})

        # If delta between the player timestamp and the actual time is lower the 30 seconds,
        # return the current player data to avoid 429 error.
        delta = self.getDeltaTime(player.get("Timestamp", 0), 'seconds')
        if delta < 30:
            return self.insertSeperators(clean_uuid), player.get("Name", "<Unknown Name>"), clean_uuid

        player["Timestamp"] = time.time()
        response = self._getDataFromURL("https://sessionserver.mojang.com/session/minecraft/profile/{}".format(clean_uuid))
        if response:
            try:
                data = response
                response = json.loads(response)
                player["Name"] = response.get("name", player.get("Name", "<Unknown Name>"))
                player["Successful"] = True
                self._cache["Cache"][clean_uuid] = player
                self.temp_skin_cache[clean_uuid] = data
                self.save()
                return self.insertSeperators(clean_uuid), player["Name"], clean_uuid
            except:
                player["Successful"] = False
                self._cache["Cache"][clean_uuid] = player
                if use_old_data and player.get("Name", "<Unknown Name>") != "<Unknown Name>":
                    return self.insertSeperators(clean_uuid), player["Name"], clean_uuid
                else:
                    return self.insertSeperators(clean_uuid), "<Unknown Name>", clean_uuid
        else:
            player["Successful"] = False
            self._cache["Cache"][clean_uuid] = player
            if use_old_data and player.get("Name", "<Unknown Name>") != "<Unknown Name>":
                return self.insertSeperators(clean_uuid), player["Name"], clean_uuid
            else:
                return self.insertSeperators(clean_uuid), "<Unknown Name>", clean_uuid

    @threadable
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
                return self.insertSeperators(uuid), player["Name"], uuid
            except:
                return "<Unknown UUID>", name, "<Unknown UUID>"
        else:
            return "<Unknown UUID>", name, "<Unknown UUID>"

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
            print "Couldn't parse skin response JSON"
            print traceback.format_exc()
        return None

    @threadable
    def getPlayerSkin(self, arg, force_download=True, instance=None):
        """
        Gets the player's skin from Mojang's skin servers

        :param arg: The UUID of the player
        :type arg: str
        :param force_download: Should the skin be re-downloaded even if it has already been downloaded
        :type force_download: bool
        :param instance: The instance of the PlayerTool
        :type instance: PlayerTool
        :return: The path to the player skin
        :rtype: str
        """
        toReturn = 'char.png'

        raw_data = self.getPlayerInfo(arg)
        if raw_data.__class__ != ThreadRS:
            uuid_sep, name, uuid = raw_data
            if uuid == "<Unknown UUID>" or "Server not ready" in raw_data:
                return toReturn

            player = self._cache["Cache"][uuid]

            skin_path = os.path.join("player-skins", uuid_sep.replace("-","_") + ".png")
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
                        # If delta between the player timestamp and the actual time is lower the 30 seconds,
                        # set the 'response' to None to avoid 429 error.
                        delta = self.getDeltaTime(player.get("Timestamp", 0), 'seconds')
                        if delta < 30:
                            response = None
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
                print "Unknown error occurred while reading/downloading skin for "+str(uuid.replace("-","_")+".png")
                print traceback.format_exc()
        else:
            toReturn = raw_data.join()
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
        conn = None
        try:
            conn = urllib2.urlopen(url, timeout=self.TIMEOUT)
            response = conn.read()
            self.last_error = False
            return response
        except urllib2.HTTPError, e:
            log.warn("Encountered a HTTPError while trying to access \"" + url + "\"")
            log.warn("Error: " + str(e.code))
            self.error_count += 1
        except urllib2.URLError, e:
            log.warn("Encountered an URLError while trying to access \"" + url + "\"")
            log.warn("Error: " + str(e.reason))
            self.error_count += 1
        except httplib.HTTPException:
            log.warn("Encountered a HTTPException while trying to access \"" + url + "\"")
            self.error_count += 1
        except Exception:
            log.warn("Unknown error occurred while trying to get data from URL: " + url)
            log.warn(traceback.format_exc())
            self.error_count += 1
        finally:
            if conn:
                conn.close()
        return None

    def _postDataToURL(self, url, payload, headers):
        conn = None
        try:
            request = urllib2.Request(url, payload, headers)
            conn = urllib2.urlopen(request, timeout=self.TIMEOUT)
            response = conn.read()
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
        finally:
            if conn: conn.close()
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
