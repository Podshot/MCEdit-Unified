from albow import Widget, Label, Button, TextField
from pymclevel import scoreboard
from pymclevel.nbt import *

operations = {
    "Yes/No Dialog": 1,
    "Custom Dialog (Hi Button)": 2,
    "Scoreboard Editing (Objective)": 3,
    "Scoreboard Editing (Team)": 4,
    }

inputs = (
    ("Operation", tuple(sorted(operations.keys()))),
    )

def hiAction():
    print '"Hi" Button clicked!'

def yesFUNC(level, box):
    for x in xrange(box.minx, box.maxx):
        for y in xrange(box.miny, box.maxy):
            for z in xrange(box.minz, box.maxz):
                level.setBlockAt(x, y, z, 19)


def perform(level, box, options):
    op = options["Operation"]
    #print dir(level.scoreboard.Objectives)
    print "Test Filter Ran"
    if op == "Yes/No Dialog":
        choice = editor.YesNoWidget("Place a sponge block here?")
        if choice:
            yesFunc(level, box)
            raise Exception("Response was Yes")
        else:
            raise Exception("Response was No")
    elif op == "Custom Dialog (Hi Button)":
        widget = Widget()
        widget.bg_color = (0.0, 0.0, 0.6)
        lbl = Label("Test Message from a External Widget")
        btn = Button("Hi", action=hiAction)
        widget.add(lbl)
        widget.add(btn)
        widget.shrink_wrap()
        editor.addExternalWidget(widget)        
    elif op == "Scoreboard Editing (Objective)":
        score = level.init_scoreboard()
        test_objective = TAG_Compound()
        test_objective["Name"] = TAG_String("FilterObjective")
        test_objective["DisplayName"] = TAG_String("FilterObjective")
        test_objective["CriteriaName"] = TAG_String("dummy")
        test_objective["RenderType"] = TAG_String("integer")
        test_objective = scoreboard.Objective(test_objective)
        score.Objectives.append(test_objective)
        score.save(level)
        for objective in score.Objectives:
            print "Objective Name: " + str(objective.Name)
    elif op == "Scoreboard Editing (Team)":
        if level.scoreboard != None:
            for team in level.scoreboard.Teams:
                print "Team Name: " + str(team.DisplayName)
