from nbt import *
import json
import urllib2


def getPlayerNameFromUUID(uuid):
    nuuid = uuid.replace("-", "")
    try:
        playerJSONResponse = urllib2.urlopen("https://api.mojang.com/user/profiles/{}/names".format(nuuid)).read()
    except:
        return uuid
    playerJSON = json.loads(playerJSONResponse)
    return playerJSON[0]

# while True:
#print getPlayerNameFromUUID("11d0102c-4178-4953-9175-09bbd7d46264")
