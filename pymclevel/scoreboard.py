import nbt

class PlayerScores:
    '''
    Contains Objective scores for each player
    '''
    
    def __init__(self, players):
        self._playersScores = {}
        self._players = players
        self.setup()
        
    def setup(self):
        for p in self._players:
            if p["Name"].value not in self._playersScores:
                self._playersScores[p["Name"].value] = {}
            self._playersScores[p["Name"].value][p["Objective"].value] = {"Score":p["Score"].value,"Locked":p["Locked"].value}
    
    def get_player_scores(self):
        return self._playersScores
        
        
        
class Objective:
    '''
    Represents a Scoreboard Objective
    '''

    def __init__(self, objective):
        self._criteria = objective["CriteriaName"].value
        self._displayName = objective["DisplayName"].value
        self._name = objective["Name"].value
        # Only Render Type currently is integer, bu this is to prevent
        # breaking in possible newer versions
        self._renderType = objective["RenderType"].value

    @property
    def Criteria(self):
        '''
        The Criteria of the Objective
        '''
        return self._criteria

    @property
    def DisplayName(self):
        '''
        The DisplayName of the Objective
        '''
        return self._displayName

    @property
    def Name(self):
        '''
        The Name of the Objective
        '''
        return self._name

    @property
    def RenderType(self):
        '''
        The RenderType of the Objective (As of 1.8: only integer)
        '''
        return self._renderType

    def getTAGStructure(self):
        '''
        Returns a TAG_Compound() that matches the Objective structure
        '''
        tag = nbt.TAG_Compound()
        tag["Name"] = nbt.TAG_String(self.name)
        tag["RenderType"] = nbt.TAG_String(self.renderType)
        tag["DisplayName"] = nbt.TAG_String(self.displayName)
        tag["CriteriaName"] = nbt.TAG_String(self.criteria)
        return tag

class Team:
    '''
    Represents a Scoreboard Team
    '''

    def __init__(self, team):
        self.displayName = team["DisplayName"].value
        self.name = team["Name"].value
        self.prefix = team["Prefix"].value
        self.suffix = team["Suffix"].value
        if "TeamColor" in team:
            self.color = team["TeamColor"].value
        else:
            self.color = None
        self.deathMessage = team["DeathMessageVisibility"].value
        self.nametags = team["NameTagVisibility"].value
        self.friendlyInvisibles = team["SeeFriendlyInvisibles"].value
        self.friendlyFire = team["AllowFriendlyFire"].value
        self.teamMembers = []
        for player in team["Players"]:
            self.teamMembers.append(player.value)


    @property
    def DisplayName(self):
        '''
        The DisplayName of the Team
        '''
        return self.displayName

    @property
    def Name(self):
        '''
        The Name of the Team
        '''
        return self.name

    @property
    def Prefix(self):
        '''
        The Prefix of the Team
        '''
        return self.prefix

    @property
    def Suffix(self):
        '''
        The Suffix of the Team
        '''
        return self.suffix

    @property
    def Color(self):
        '''
        The Color of the Team
        '''
        return self.color

    @property
    def DeathMessage(self):
        '''
        The DeathMessage for the Team
        '''
        return self.deathMessage

    @property
    def NameTags(self):
        '''
        The NameTags of the Team
        '''
        return self.nametags

    @property
    def FriendlyInvisibles(self):
        '''
        Whether the members of the Team should see other players that are invisible and that are on their Team
        '''
        return self.friendlyInvisibles

    @property
    def FriendlyFire(self):
        '''
        Whether players on the same Team can damage each other
        '''
        return self.friendlyFire

    @property
    def TeamMembers(self):
        '''
        A list of player names of players that are on the Team
        '''
        return self.teamMembers

    def getTAGStructure(self):
        '''
        Returns a TAG_Compound() that matches the Team structure
        '''
        tag = nbt.TAG_Compound()
        tag["Name"] = nbt.TAG_String(self.name)
        tag["DisplayName"] = nbt.TAG_String(self.displayName)
        tag["Prefix"] = nbt.TAG_String(self.prefix)
        tag["Suffix"] = nbt.TAG_String(self.suffix)
        if self.color != None:
            tag["TeamColor"] = nbt.TAG_String(self.color)
        tag["NameTagVisibility"] = nbt.TAG_String(self.nametags)
        tag["DeathMessageVisibility"] = nbt.TAG_String(self.deathMessage)
        tag["AllowFriendlyFire"] = nbt.TAG_Byte(self.friendlyFire)
        tag["SeeFriendlyInvisibles"] = nbt.TAG_Byte(self.friendlyInvisibles)
        players = nbt.TAG_List()
        for member in self.teamMembers:
            players.append(nbt.TAG_String(member))
        tag["Players"] = players
        return tag
        
class Scoreboard:
    '''
    Represents a world's scoreboard.dat file
    '''

    def __init__(self, level, should_create_scoreboard):
        '''
        Initiates a Scoreboard object
        :param level: The level that this Scoreboard represents
        :param should_create_scoreboard: Creates a empty Scoreboard if one is not present in the world's data folder
        '''
        self.level = level
        self._objectives = []
        self._teams = []
        self._scs = should_create_scoreboard
        self._playerscores = {}
        self.root_tag = None
        self.setup()

    def setup(self):
        if not self._scs:
            self.root_tag = nbt.load(self.level.worldFolder.getFolderPath("data")+"/scoreboard.dat")
            for objective in self.root_tag["data"]["Objectives"]:
                self._objectives.append(Objective(objective))

            for team in self.root_tag["data"]["Teams"]:
                self._teams.append(Team(team))
            self._playerscores = PlayerScores(self.root_tag["data"]["PlayerScores"]).get_player_scores()
        else:
            self.root_tag = nbt.TAG_Compound()
            self.root_tag["data"] = nbt.TAG_Compound()
            
    @property
    def Objectives(self):
        '''
        The Objectives that belong to this Scoreboard
        '''
        return self._objectives

    @property
    def Teams(self):
        '''
        The Teams that belong to this Scoreboard
        '''
        return self._teams
    
    @property
    def PlayerScores(self):
        '''
        A list PlayerScore object
        '''
        return self._playerscores

    def save(self, level):
        '''
        Saves the Scoreboard object to disk
        :param level: The Level that this scoreboard should be saved to
        '''
        objectiveList = nbt.TAG_List()
        teamList = nbt.TAG_List()
        for objective in self._objectives:
            objectiveList.append(objective.getTAGStructure())
        for team in self._teams:
            teamList.append(team.getTAGStructure())
        self.root_tag["data"]["Objectives"] = objectiveList
        self.root_tag["data"]["Teams"] = teamList
        print "Saving Scoreboard...."
        self.root_tag.save(level.worldFolder.getFolderPath("data")+"/scoreboard.dat")
        
        
