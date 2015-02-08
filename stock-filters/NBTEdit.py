import ast
from pymclevel.box import BoundingBox

inputs = [(("Entities", True),
           ("Tile Entities", True),
           ("Tile Ticks", True),
           ("Options", "title")),
          (("Results", "title"),
           ("", ["NBTTree", {}, 0, False]),
           )]

tree = None
chunks = None
boundingBox = None

#displayName = ""

def set_tree(t):
    global tree
    tree = t
    if hasattr(tree, 'treeRow'):
        t.treeRow.tooltipText = "Double-click to go to this item."
        
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
    
def nbt_ok_action():
    for chunk in chunks:
        chunk.dirty = True
    editor.removeUnsavedEdit()
    editor.addUnsavedEdit()
    editor.invalidateBox(boundingBox)

def perform(level, box, options):
    global chunks
    global boundingBox
    chunks = []
    boundingBox = box
    data = {"Entities": [], "TileEntities": [], "TileTicks": []}
    runOn = (options["Entities"], options["Tile Entities"], options["Tile Ticks"])
    for (chunk, slices, point) in level.getChunkSlices(box):
        if runOn[0]:
            for e in chunk.Entities:
                x = e["Pos"][0].value
                y = e["Pos"][1].value
                z = e["Pos"][2].value
                if (x, y, z) in box:
                    data["Entities"].append(e)
                    if chunk not in chunks:
                        chunks.append(chunk)
        if runOn[1]:
            for te in chunk.TileEntities:
                x = te["x"].value
                y = te["y"].value
                z = te["z"].value
                if (x, y, z) in box:
                    data["TileEntities"].append(te)
                    if chunk not in chunks:
                        chunks.append(chunk)
        if runOn[2]:
            for tt in chunk.TileTicks:
                x = tt["x"].value
                y = tt["y"].value
                z = tt["z"].value
                if (x, y, z) in box:
                    data["TileTicks"].append(tt)
                    if chunk not in chunks:
                        chunks.append(chunk)
    treeData = {"Entities": {}, "TileEntities": {}, "TileTicks": {}}
    for i in range(len(data["Entities"])):
        treeData["Entities"][u"%s"%((data["Entities"][i]["Pos"][0].value, data["Entities"][i]["Pos"][1].value, data["Entities"][i]["Pos"][2].value),)] = data["Entities"][i]
    for i in range(len(data["TileEntities"])):
        treeData["TileEntities"][u"%s"%((data["TileEntities"][i]["x"].value, data["TileEntities"][i]["y"].value, data["TileEntities"][i]["z"].value),)] = data["TileEntities"][i]
    for i in range(len(data["TileTicks"])):
        treeData["TileTicks"][u"%s"%((data["TileTicks"][i]["x"].value, data["TileTicks"][i]["y"].value, data["TileTicks"][i]["z"].value),)] = data["TileTicks"][i]
        
    
    inputs[1][1][1][1] = {'Data': treeData}
    options[""](inputs[1])