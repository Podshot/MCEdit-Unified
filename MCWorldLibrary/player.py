import nbt
import version_utils


class Player:

    def __init__(self, playerNBTFile):
        self.nbtFile = playerNBTFile
        self.nbtFileName = playerNBTFile.split("\\")[-1]
        self.root_tag = nbt.load(playerNBTFile)

        # Properties setup
        self._uuid = self.nbtFileName.split(".")[0]
        playerName = version_utils.getPlayerNameFromUUID(self._uuid)
        if playerName != self._uuid:
            self._name = playerName
        else:
            self._name = None
        self._gametype = self.root_tag["playerGameType"].value
        
        self._pos = [self.root_tag["Pos"][0].value, self.root_tag["Pos"][1].value, self.root_tag["Pos"][2].value]
        self._rot = [self.root_tag["Rotation"][0].value, self.root_tag["Rotation"][1].value]

        self._health = self.root_tag["Health"].value
        self._healf = self.root_tag["HealF"].value

        self._xp_level = self.root_tag["XpLevel"].value
        self._inventory = self.root_tag["Inventory"].value
        
    @property
    def name(self):
        return self._name
    
    @property
    def gametype(self):
        return self._gametype
    
    @property
    def uuid(self):
        return self._uuid
    
    @property
    def pos(self):
        return self._pos

    @property
    def rot(self):
        return self._rot

    @property
    def health(self):
        return self._health

    @property
    def healf(self):
        return self._healf

    @property
    def XP_Level(self):
        return self._xp_level
    
    @property
    def inventory(self):
        return self._inventory
    
    def save(self):
        raise NotImplementedError("Player Data cannot be saved right now")
