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
        return self.fiendlyInvisibles

    @property
    def FriendlyFire(self):
        return self.friendlyFire

    @property
    def TeamMembers(self):
        return self.teamMembers

class Scoreboard:

    def __init__(self, level):
        self.level = level
        self.setup()

    def setup(self):
        self.root_tag = nbt.load(self.level.worldFolder.getFolderPath("data")+"/scoreboard.dat")
        self.objectives = {}
        self.teams = {}
        for objective in self.root_tag["data"]["Objectives"]:
            self.objectives[objective["Name"].value] = Objective(objective)

        for team in self.root_tag["data"]["Teams"]:
            self.teams[team["Name"].value] = Team(team)


    @property
    def Objectives(self):
        return self.objectives

    @property
    def Teams(self):
        return self.teams
        
        
