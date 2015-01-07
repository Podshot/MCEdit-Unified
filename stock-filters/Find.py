#written by texelelf
from pymclevel import TAG_Byte, TAG_Short, TAG_Int, TAG_Compound, TAG_List, TAG_String, TAG_Double, TAG_Float, TAG_Long, TAG_Byte_Array, TAG_Int_Array
from pymclevel.box import BoundingBox

displayName = "Find"

tagtypes = { "TAG_Byte":0, "TAG_Short":1, "TAG_Int":2, "TAG_Compound":3, "TAG_List":4, "TAG_String":5,
             "TAG_Double":6, "TAG_Float":7, "TAG_Long":8, "TAG_Byte_Array":9, "TAG_Int_Array":10 }

tagses = {  0:TAG_Byte, 1:TAG_Short, 2:TAG_Int, 3:TAG_Compound, 4:TAG_List, 5:TAG_String,
            6:TAG_Double, 7:TAG_Float, 8:TAG_Long, 9:TAG_Byte_Array, 10:TAG_Int_Array, "Any":11}

inputs = [    (("Match by:",("TileEntity","Entity","Block")),
            ("Match block type (for TileEntity searches):", False),
            ("Match block:","blocktype"),
            ("Match block data:", True),
            ("Match tile entities (for Block searches):", False),
            ("\"None\" for Name or Value will match any tag's Name or Value respectively.","label"),
            ("Match Tag Name:",("string","value=None")),
            ("Match Tag Value:",("string","value=None")),
            ("Case insensitive:",True),
            ("Match Tag Type:",tuple(("Any",))+tuple(tagtypes.keys())),
            ("Operation:",("Start New Search","Find Next","Dump Found Coordinates")),
            ("Options","title")),

            (("Documentation","title"),
            ("This filter is designed to search for NBT in either Entities or TileEntities.  "
             "It can also be used to search for blocks.  \"Match by\" determines which type of object "
             "is prioritized during the search.  Entites and TileEntities will search relatively quickly, "
             "while the speed of searching by Block will be directly proportional to the selection size (since every "
             "single block within the selection will be examined).  "
             "All Entity searches will ignore the block settings; TileEntity searches will try to "
             "\"Match block type\" if checked, and Block searches will try to \"Match tile entity\" tags if "
             "checked.  It is faster to match TileEntity searches with a Block Type than vice versa.  Block "
             "matching can also optionally match block data, e.g. matching all torches, or only torches facing "
             "a specific direction.\n\"Start New Search\" will re-search through the selected volume, while \"Find Next\" "
             "will iterate through the search results of the previous search.","label"))
            ]

try:
    search
except NameError:
    search = None

def FindTagS(nbtData,name,value,tagtype):
    if type(nbtData) is TAG_List or type(nbtData) is TAG_Compound:
        if name in nbtData.name or name == "":
            if value == "":
                if (type(nbtData) is tagtype or tagtype == 11):
                    print "found in pre-area"
                    return True
        if type(nbtData) is TAG_List:
            list = True
        else:
            list = False

        for tag in range(0,len(nbtData)) if list else nbtData.keys():
            if type(nbtData[tag]) is TAG_Compound:
                if FindTagS(nbtData[tag],name,value,tagtype):
                    return True
            elif type(nbtData[tag]) is TAG_List:
                if FindTagS(nbtData[tag],name,value,tagtype):
                    return True
            else:
                if name in nbtData[tag].name or name == "":
                    if value in unicode(nbtData[tag].value):
                        if (type(nbtData[tag]) is tagtype or tagtype == 11):
                            print "found in list/compound"
                            return True
        else:
            return False
    else:
        if name in nbtData.name or name == "":
            if value in unicode(nbtData.value):
                if (type(nbtData[tag]) is tagtype or tagtype == 11):
                    print "found outside"
                    return True
    return False

def FindTagI(nbtData,name,value,tagtype):
    if type(nbtData) is TAG_List or type(nbtData) is TAG_Compound:
        if name in nbtData.name.upper() or name == "":
            if value == "":
                if (type(nbtData) is tagtype or tagtype == 11):
                    return True
        if type(nbtData) is TAG_List:
            list = True
        else:
            list = False

        for tag in range(0,len(nbtData)) if list else nbtData.keys():
            if type(nbtData[tag]) is TAG_Compound:
                if FindTagI(nbtData[tag],name,value,tagtype):
                    return True
            elif type(nbtData[tag]) is TAG_List:
                if FindTagI(nbtData[tag],name,value,tagtype):
                    return True
            else:
                if name in nbtData[tag].name.upper() or name == "":
                    if value in unicode(nbtData[tag].value).upper():
                        if (type(nbtData[tag]) is tagtype or tagtype == 11):
                            return True
        else:
            return False
    else:
        if name in nbtData.name.upper() or name == "":
            if value in unicode(nbtData.value).upper():
                if (type(nbtData[tag]) is tagtype or tagtype == 11):
                    return True
    return False

def FindTag(nbtData,name,value,tagtype,caseSensitive):
    if caseSensitive:
        return FindTagS(nbtData,name,value,tagtype)
    else:
        return FindTagI(nbtData,name,value,tagtype)

def perform(level, box, options):
    global search

    by = options["Match by:"]
    matchtype = options["Match block type (for TileEntity searches):"]
    matchblock = options["Match block:"]
    matchdata = options["Match block data:"]
    matchtile = options["Match tile entities (for Block searches):"]
    matchname = u"" if options["Match Tag Name:"] == "None" else unicode(options["Match Tag Name:"])
    matchval = u"" if options["Match Tag Value:"] == "None" else unicode(options["Match Tag Value:"])
    caseSensitive = not options["Case insensitive:"]
    matchtagtype = tagtypes[options["Match Tag Type:"]] if options["Match Tag Type:"] != "Any" else "Any"
    op = options["Operation:"]

    if not caseSensitive:
        matchname = matchname.upper()
        matchval = matchval.upper()

    if matchtile and matchname == "" and matchval == "":
        raise Exception("\nInvalid Tag Name and Value; the present values will match every tag of the specified type.")

    if search == None or op == "Start New Search" or op == "Dump Found Coordinates":
        search = []

    if not search:
        if by == "Block":
            for x in xrange(box.minx, box.maxx):
                for z in xrange(box.minz, box.maxz):
                    for y in xrange(box.miny, box.maxy):
                        block = level.blockAt(x,y,z)
                        data = level.blockDataAt(x,y,z)
                        if block == matchblock.ID and (not matchdata or data == matchblock.blockData):
                            pass
                        else:
                            continue
                        if matchtile:
                            tile = level.tileEntityAt(x,y,z)
                            if tile != None:
                                if not FindTag(tile,matchname,matchval,tagses[matchtagtype],caseSensitive):
                                    continue
                            else:
                                continue
                        search.append((x,y,z))
        elif by == "TileEntity":
            for (chunk, _, _) in level.getChunkSlices(box):
                for e in chunk.TileEntities:
                    x = e["x"].value
                    y = e["y"].value
                    z = e["z"].value
                    if (x,y,z) in box:
                        if matchtype:
                            block = level.blockAt(x,y,z)
                            data = level.blockDataAt(x,y,z)
                            if block == matchblock.ID and (not matchdata or data == matchblock.blockData):
                                pass
                            else:
                                continue
                        if not FindTag(e,matchname,matchval,tagses[matchtagtype],caseSensitive):
                            continue

                        search.append((x,y,z))
        else:
            for (chunk, _, _) in level.getChunkSlices(box):
                for e in chunk.Entities:
                    x = e["Pos"][0].value
                    y = e["Pos"][1].value
                    z = e["Pos"][2].value
                    if (x,y,z) in box:
                        if FindTag(e,matchname,matchval,tagses[matchtagtype],caseSensitive):
                            search.append((x,y,z))
    if not search:
        raise Exception("\nNo matching blocks/tile entities found")
    else:
        search.sort()
        if op == "Dump Found Coordinates":
            raise Exception("\nMatching Coordinates:\n"+"\n".join("%d, %d, %d" % pos for pos in search))
        else:
            for s in search:
                editor.mainViewport.cameraPosition = (s[0]+0.5,s[1]+2,s[2]-1)
                editor.mainViewport.yaw = 0.0
                editor.mainViewport.pitch = 45.0

                newBox = BoundingBox(s, (1,1,1))
                editor.selectionTool.setSelection(newBox)

                if not editor.YesNoWidget("Matching blocks/tile entities found at "+str(s)+".\nContinue search?"):
                    raise Exception("\nSearch halted.")
            else:
                raise Exception("\nEnd of search.")
