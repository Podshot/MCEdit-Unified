from albow import Widget, Label, Button, TextFieldWrapped
from MCWorldLibrary.nbt import *
import release

operations = {
    "Yes/No Dialog": 1,
    "Custom Dialog": 2,
    "Scoreboard Editing (Objective)": 3,
    "Scoreboard Editing (Team)": 4,
    "Player Data": 5,
    }

inputs = (
    ("Operation", tuple(sorted(operations.keys()))),
    ("Float Field Test (Default)", 0.0),
    ("Float Field Test (Min=-1.0 Max=1.0", (0.0, -1.0, 1.0)),
    ("Float Field Test (Increments by 0.3)", (0.0, -5.0, 5.0, 0.3)),
    )


class StoreData:
    def __init__(self):
        self._isFork = False
        self._editor = None
    @property
    def isFork(self):
        return self._isFork
    @property
    def editor(self):
        return self._editor

data = StoreData()
def hiAction():
    print '"Hi" Button clicked!'

def yesFUNC(level, box):
    for x in xrange(box.minx, box.maxx):
        for y in xrange(box.miny, box.maxy):
            for z in xrange(box.minz, box.maxz):
                level.setBlockAt(x, y, z, 19)


def perform(level, box, options):
    ver = release.get_version()
    if "unified" in ver.lower():
        try:
            data.editor = editor
            data.isFork = True
        except NameError:
            import inspect
            data.editor = inspect.stack()[1][0].f_locals.get('self', None).editor
            pass
    else:
        import inspect
        data.editor = inspect.stack()[1][0].f_locals.get('self', None).editor
    if not data.isFork:
        raise NotImplemented("This filter will only work with MCEdit-Unified!")
    op = options["Operation"]
    #print dir(level.scoreboard.Objectives)
    #print level.init_scoreboard().PlayerScores["Chevalerie94"]
    print "Test Filter Ran"
    if op == "Yes/No Dialog":
        choice = editor.YesNoWidget("Place a sponge block here?")
        if choice:
            yesFunc(level, box)
            raise Exception("Response was Yes")
        else:
            raise Exception("Response was No")
    elif op == "Custom Dialog":
        entities = {}
        chunks = []
        for (chunk, slices, point) in level.getChunkSlices(box):
            for e in chunk.Entities:
                x = e["Pos"][0].value
                y = e["Pos"][1].value
                z = e["Pos"][2].value
                
                if (x,y,z) in box:
                    keyname = "{0} - {1},{2},{3}".format(e["id"].value,int(x),int(y),int(z))
                    entities[keyname] = e
                    chunks.append(chunk)
        thing = (
                 ("Entity", tuple(sorted(entities.keys()))),
                 ("Entity Name", "string"),
                 ("Replace existing names?", False),
                 )
        result = editor.addExternalWidget(thing)
        if result != "user canceled":
            entity = entities[result["Entity"]]
            if "CustomName" not in result["Entity"]:
                entity["CustomName"] = TAG_String(result["Entity Name"])
            elif "CustomName" in result["Entity"] and result["Replace existing names?"]:
                result["Entity"]["CustomName"] = TAG_String(result["Entity Name"])
            for c in chunks:
                c.dirty = True
    elif op == "Scoreboard Editing (Objective)":
        scoreboard = level.init_scoreboard()
        test_objective = TAG_Compound()
        test_objective["Name"] = TAG_String("FilterObjective")
        test_objective["DisplayName"] = TAG_String("FilterObjective")
        test_objective["CriteriaName"] = TAG_String("dummy")
        test_objective["RenderType"] = TAG_String("integer")
        scoreboard["data"]["Objectives"].append(test_objective)
        level.save_scoreboard(scorebaord)
        for objective in score.Objectives:
            print "Objective Name: " + str(objective["Name"].value)
    elif op == "Scoreboard Editing (Team)":
        if level.scoreboard is not None:
            for team in level.scoreboard.Teams:
                print "Team Name: " + str(team.DisplayName)
    elif op == "Player Data":
        players = level.init_player_data()
        for p in players.keys():
            print players[p]["Air"].value
        level.save_player_data(players)
