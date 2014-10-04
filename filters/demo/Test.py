from albow import Widget, Label, Button

inputs = (
    ("Test Option", False),
)


def yesFUNC(level, box):
    for x in xrange(box.minx, box.maxx):
        for y in xrange(box.miny, box.maxy):
            for z in xrange(box.minz, box.maxz):
                level.setBlockAt(x, y, z, 19)


def perform(level, box, options):
    print "Test Filter Ran"
    widget = Widget()
    widget.bg_color = (0.0, 0.0, 0.6)
    lbl = Label("Test Message from a External Widget")
    btn = Button("Hi")
    widget.add(lbl)
    widget.add(btn)
    widget.shrink_wrap()
    editor.addExternalWidget(widget)
    # mceutils.SimpleInteractiveWidget("Test",yesFUNC,noFUNC)
    choice = editor.YesNoWidget("Place a sponge block here?")
    for objective in level.scoreboard.Objectives.keys():
        print "Objective Name: " + str(level.scoreboard.Objectives[objective].Name)
    for team in level.scoreboard.Teams.keys():
        print "Team Name: " + str(level.scoreboard.Teams[team].DisplayName)
    if choice:
        yesFunc(level, box)
        raise Exception("Response was Yes")
    else:
        raise Exception("Response was No")
