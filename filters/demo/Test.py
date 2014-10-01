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
    print dir(editor)
    ds.setLevel(level)
    ds.setBox(box)
    #mceutils.SimpleInteractiveWidget("Test",yesFUNC,noFUNC)
    choice = editor.YesNoWidget("Place a sponge block here?")
    if choice:
        yesFunc(level, box)
        raise Exception("Response was Yes")
    else:
        raise Exception("Response was No")
