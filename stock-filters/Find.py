# written by texelelf
#-# Adding a result pages, and NBT edit stuff
from pymclevel import TAG_Byte, TAG_Short, TAG_Int, TAG_Compound, TAG_List, TAG_String, TAG_Double, TAG_Float, TAG_Long, \
    TAG_Byte_Array, TAG_Int_Array
from pymclevel.box import BoundingBox
from albow import alert, ask
import ast
# Let import the stuff to save files.
from mcplatform import askSaveFile
from directories import getDocumentsFolder

# The RECODR_UNDO is not yet usable...
# RECORD_UNDO = False

displayName = "Find"

tagtypes = {"TAG_Byte": 0, "TAG_Short": 1, "TAG_Int": 2, "TAG_Compound": 3, "TAG_List": 4, "TAG_String": 5,
            "TAG_Double": 6, "TAG_Float": 7, "TAG_Long": 8, "TAG_Byte_Array": 9, "TAG_Int_Array": 10}

tagses = {0: TAG_Byte, 1: TAG_Short, 2: TAG_Int, 3: TAG_Compound, 4: TAG_List, 5: TAG_String,
          6: TAG_Double, 7: TAG_Float, 8: TAG_Long, 9: TAG_Byte_Array, 10: TAG_Int_Array, "Any": 11}

inputs = [(("Match by:", ("TileEntity", "Entity", "Block")),
           ("Match block type (for TileEntity searches):", False),
           ("Match block:", "blocktype"),
           ("Match block data:", True),
           ("Match tile entities (for Block searches):", False),
           ("\"None\" for Name or Value will match any tag's Name or Value respectively.", "label"),
           ("Match Tag Name:", ("string", "value=None")),
           ("Match Tag Value:", ("string", "value=None")),
           ("Case insensitive:", True),
           ("Match Tag Type:", tuple(("Any",)) + tuple(tagtypes.keys())),
           ("Operation:", ("Start New Search", "Dump Found Coordinates")),
           ("Options", "title")),

           (("Results", "title"), ("", ["NBTTree", {}, 0, False])), # [str name_of_widget_type, dict default_data, int page_to_goback, bool show_load_button]

           (("Documentation", "title"),
           ("This filter is designed to search for NBT in either Entities or TileEntities.\n"
            "It can also be used to search for blocks.\n\"Match by\" determines which type of object "
            "is prioritized during the search.\nEntites and TileEntities will search relatively quickly, "
            "while the speed of searching by Block will be directly proportional to the selection size (since every "
            "single block within the selection will be examined).\n"
            "All Entity searches will ignore the block settings; TileEntity searches will try to "
            "\"Match block type\" if checked, and Block searches will try to \"Match tile entity\" tags if "
            "checked.\nIt is faster to match TileEntity searches with a Block Type than vice versa.\nBlock "
            "matching can also optionally match block data, e.g. matching all torches, or only torches facing "
            "a specific direction.\n\"Start New Search\" will re-search through the selected volume, while \"Find Next\" "
            "will iterate through the search results of the previous search.", "label"))
]

tree = None # the tree widget
chunks = None # the chunks used to perform the search
bbox = None # the bouding box to search in
by = None # what is searched: Entities, TileEntities or blocs

def set_tree(t):
    global tree
    tree = t

# Use this method to overwrite the NBT tree default behaviour on mouse clicks
def nbttree_mouse_down(e):
    if e.num_clicks > 1:
        if tree.selected_item and tree.selected_item[3].startswith('(') and tree.selected_item[3].endswith(')'):
            s = ast.literal_eval(tree.selected_item[3])
            editor.mainViewport.cameraPosition = (s[0] + 0.5, s[1] + 2, s[2] - 1)
            editor.mainViewport.yaw = 0.0
            editor.mainViewport.pitch = 45.0

            newBox = BoundingBox(s, (1, 1, 1))
            editor.selectionTool.setSelection(newBox)
    tree.treeRow.__class__.mouse_down(tree.treeRow, e)

def get_chunks():
    return chunks

def get_box():
    return bbox

def get_by():
    return by

# Use this method to overwrite the NBT tree 'OK' button default behaviour
def nbt_ok_action():
    by = get_by()
    chunks = get_chunks()
    box = get_box()
    if by not in (trn._('TileEntity'), trn._('Entity')):
        return
    if chunks:
        for chunk, slices, point in chunks:
            if by == trn._('TileEntity'):
                for e in chunk.TileEntities:
                    x = e["x"].value
                    y = e["y"].value
                    z = e["z"].value
            elif by == trn._('Entity'):
                for e in chunk.Entities:
                    x = e["Pos"][0].value
                    y = e["Pos"][1].value
                    z = e["Pos"][2].value
            if (x, y, z) in box:
                chunk.dirty = True

try:
    search
except NameError:
    search = None


def FindTagS(nbtData, name, value, tagtype):
    if type(nbtData) is TAG_List or type(nbtData) is TAG_Compound:
        if name in nbtData.name or name == "":
            if value == "":
                if type(nbtData) is tagtype or tagtype == 11:
                    print "found in pre-area"
                    return True
        if type(nbtData) is TAG_List:
            list = True
        else:
            list = False

        for tag in range(0, len(nbtData)) if list else nbtData.keys():
            if type(nbtData[tag]) is TAG_Compound:
                if FindTagS(nbtData[tag], name, value, tagtype):
                    return True
            elif type(nbtData[tag]) is TAG_List:
                if FindTagS(nbtData[tag], name, value, tagtype):
                    return True
            else:
                if name in nbtData[tag].name or name == "":
                    if value in unicode(nbtData[tag].value):
                        if type(nbtData[tag]) is tagtype or tagtype == 11:
                            print "found in list/compound"
                            return True
        else:
            return False
    else:
        if name in nbtData.name or name == "":
            if value in unicode(nbtData.value):
                if type(nbtData[tag]) is tagtype or tagtype == 11:
                    print "found outside"
                    return True
    return False


def FindTagI(nbtData, name, value, tagtype):
    if type(nbtData) is TAG_List or type(nbtData) is TAG_Compound:
        if name in (u"%s"%nbtData.name).upper() or name == "":
            if value == "":
                if type(nbtData) is tagtype or tagtype == 11:
                    return True
        if type(nbtData) is TAG_List:
            list = True
        else:
            list = False

        for tag in range(0, len(nbtData)) if list else nbtData.keys():
            if type(nbtData[tag]) is TAG_Compound:
                if FindTagI(nbtData[tag], name, value, tagtype):
                    return True
            elif type(nbtData[tag]) is TAG_List:
                if FindTagI(nbtData[tag], name, value, tagtype):
                    return True
            else:
                if name in (u"%s"%nbtData[tag].name).upper() or name == "":
                    if value in unicode(nbtData[tag].value).upper():
                        if type(nbtData[tag]) is tagtype or tagtype == 11:
                            return True
        else:
            return False
    else:
        if name in (u"%s"%nbtData.name).upper() or name == "":
            if value in unicode(nbtData.value).upper():
                if type(nbtData[tag]) is tagtype or tagtype == 11:
                    return True
    return False


def FindTag(nbtData, name, value, tagtype, caseSensitive):
    if caseSensitive:
        return FindTagS(nbtData, name, value, tagtype)
    else:
        return FindTagI(nbtData, name, value, tagtype)


def perform(level, box, options):
    global search

    # Don't forget to 'globalize' these...
    global chunks
    global bbox
    global by
    bbox = box

    by = options["Match by:"]
    matchtype = options["Match block type (for TileEntity searches):"]
    matchblock = options["Match block:"]
    matchdata = options["Match block data:"]
    matchtile = options["Match tile entities (for Block searches):"]
    matchname = u"" if options["Match Tag Name:"] == "None" else unicode(options["Match Tag Name:"])
    matchval = u"" if options["Match Tag Value:"] == "None" else unicode(options["Match Tag Value:"])
    caseSensitive = not options["Case insensitive:"]
    matchtagtype = tagtypes.get(options["Match Tag Type:"], "Any")
    op = options["Operation:"]

    datas = []

    if not caseSensitive:
        matchname = matchname.upper()
        matchval = matchval.upper()

    if matchtile and matchname == "" and matchval == "":
        alert("\nInvalid Tag Name and Value; the present values will match every tag of the specified type.")

    if search is None or op == trn._("Start New Search") or op == trn._("Dump Found Coordinates"):
        search = []

    if not search:
        if by == trn._("Block"):
            for x in xrange(box.minx, box.maxx):
                for z in xrange(box.minz, box.maxz):
                    for y in xrange(box.miny, box.maxy):
                        block = level.blockAt(x, y, z)
                        data = level.blockDataAt(x, y, z)
                        if block == matchblock.ID and (not matchdata or data == matchblock.blockData):
                            pass
                        else:
                            continue
                        if matchtile:
                            tile = level.tileEntityAt(x, y, z)
                            if tile is not None:
                                if not FindTag(tile, matchname, matchval, tagses[matchtagtype], caseSensitive):
                                    continue
                            else:
                                continue
                        search.append((x, y, z))
                        datas.append(data)
        elif by == trn._("TileEntity"):
            chunks = []
            for (chunk, slices, point) in level.getChunkSlices(box):
                for e in chunk.TileEntities:
                    x = e["x"].value
                    y = e["y"].value
                    z = e["z"].value
                    if (x, y, z) in box:
                        if matchtype:
                            block = level.blockAt(x, y, z)
                            data = level.blockDataAt(x, y, z)
                            if block == matchblock.ID and (not matchdata or data == matchblock.blockData):
                                pass
                            else:
                                continue
                        if not FindTag(e, matchname, matchval, tagses[matchtagtype], caseSensitive):
                            continue

                        search.append((x, y, z))
                        datas.append(e)
                        chunks.append([chunk, slices, point])
        else:
            chunks = []
            for (chunk, slices, point) in level.getChunkSlices(box):
                for e in chunk.Entities:
                    x = e["Pos"][0].value
                    y = e["Pos"][1].value
                    z = e["Pos"][2].value
                    if (x, y, z) in box:
                        if FindTag(e, matchname, matchval, tagses[matchtagtype], caseSensitive):
                            search.append((x, y, z))
                            datas.append(e)
                            chunks.append([chunk, slices, point])
    if not search:
        alert("\nNo matching blocks/tile entities found")
    else:
        search.sort()
        if op == trn._("Dump Found Coordinates"):
            result = "\n".join("%d, %d, %d" % pos for pos in search)
            answer = ask(result, height=editor.height, colLabel="Matching Coordinates", responses=["Save", "OK"])
            if answer == "Save":
                fName = askSaveFile(getDocumentsFolder(), "Save to file...", "find.txt", 'TXT\0*.txt\0\0', 'txt')
                if fName:
                    fData = "# MCEdit find output\n# Search options:\n# Match by: %s\n# Match block type: %s\n# Match block: %s\n# Match block data: %s\n# Match tile entities: %s\n# Match Tag Name:%s\n# Match Tag Value: %s\n# Case insensitive: %s\n# Match Tag Type: %s\n\n%s"%(by, matchtype, matchblock, matchdata, matchtile, matchname, matchval, caseSensitive, matchtagtype, result)
                    open(fName, 'w').write(fData)
        else:
            treeData = {}
            # To set tooltip text to the items the need it, use a dict: {"value": <item to be added to the tree>, "tooltipText": "Some text"}
            for i in range(len(search)):
                if by == trn._('Block'):
                    treeData[u"%s"%(search[i],)] = {"value": datas[i], "tooltipText": "Double-click to go to this item."}
                elif by == trn._('Entity'):
                    treeData[u"%s"%((datas[i]['Pos'][0].value, datas[i]['Pos'][1].value, datas[i]['Pos'][2].value),)] = {"value": datas[i], "tooltipText": "Double-click to go to this item."}
                else:
                    treeData[u"%s"%((datas[i]['x'].value, datas[i]['y'].value, datas[i]['z'].value),)] = {"value": datas[i], "tooltipText": "Double-click to go to this item."}
            inputs[1][1][1][1] = {'Data': treeData}
            options[""](inputs[1])
