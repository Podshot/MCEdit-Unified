import nbt

class Objective:

    def __init__(self, objective):
        self.criteria = objective["CriteriaName"].value
        self.displayName = objective["DisplayName"].value
        self.name = objective["Name"].value
        # Only Render Type currently is integer, bu this is to prevent
        # breaking in possible newer versions
        self.renderType = objective["RenderType"].value

    @property
    def Citeria(self):
        return self.criteria

    @property
    def DisplayName(self):
        return self.displayName

    @property
    def Name(self):
        return self.name

    @property
    def RenderType(self):
        return self.renderType

    def getTAGStructure(self):
        tag = nbt.TAG_Compound()
        tag["Name"] = nbt.TAG_String(self.name)
        tag["RenderType"] = nbt.TAG_String(self.rednerType)
        tag["DisplayName"] = nbt.TAG_String(self.displayName)
        tag["CriteriaName"] = nbt.TAG_String(self.criteria)
        return tag

class Team:

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
        return self.displayName

    @property
    def Name(self):
        return self.name

    @property
    def Prefix(self):
        return self.prefix

    @property
    def Suffix(self):
        return self.suffix

    @property
    def Color(self):
        return self.color

    @property
    def DeathMessage(self):
        return self.deathMessage

    @property
    def NameTags(self):
        return self.nametags

    @property
    def FriendlyInvisibles(self):
        return self.friendlyInvisibles

    @property
    def FriendlyFire(self):
        return self.friendlyFire

    @property
    def TeamMembers(self):
        return self.teamMembers

    def getTAGStructure(self):
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

    def __init__(self, level):
        self.level = level
        self.setup()

    def setup(self):
        self.root_tag = nbt.load(self.level.worldFolder.getFolderPath("data")+"/scoreboard.dat")
        self.objectives = []
        self.teams = []
        for objective in self.root_tag["data"]["Objectives"]:
            self.objectives.append(Objective(objective))

        for team in self.root_tag["data"]["Teams"]:
            self.teams.append(Team(team))


    @property
    def objectives(self):
        return self.objectives

    @property
    def teams(self):
        return self.teams

    def save(self):
        objectiveList = nbt.TAG_List()
        teamList = nbt.TAG_List()
        for objective in self.objectives:
            objectiveList.append(objective.getTAGStructure())
        for team in self.teams:
            teamList.append(team.getTAGStructure())
        self.root_tag["data"]["Objectives"] = objectiveList
        self.root_tag["data"]["Teams"] = teamList
        print "Saving Scoreboard...."
        with open(self.level.worldFolder.getFolderPath("data")+"/scoreboard.dat") as datFile:
            self.root_tag.save(datFile)
        
        
