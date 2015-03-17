# Feel free to modify and use this filter however you wish. If you do,
# please give credit to SethBling.
# http://youtube.com/SethBling
#
''' Fixed for MC 1.8 by Rezzing, September 6, 2014 
PLEASE READ: The unusable trade won't prevent new trades anymore but I
solved it by adding a very high career level. So only use it if you like
the fancy stop sign. '''
# Reedited by DragonQuiz, November 8, 2014
#
# Changes: ^denotes new change
# 1) Allow your villager to move or not.
# 2) Rename your villager in MCEdit.
# 3) Allow players to receive experience for their trade.
# 4) Updated more of the code, made it much prettier.
# 5) Added rotation so the villager *can rotate* when possible.
# And a big thanks to Sethbling for creating this filter and all his other filters at http://sethbling.com/downloads/mcedit-filters/

from pymclevel import TAG_Byte, TAG_Short, TAG_Int, TAG_Compound, TAG_List, TAG_String, TAG_Double, TAG_Float

displayName = "Create Shops"

Professions = {
    "Farmer (brown)": 0,
    "Librarian (white)": 1,
    "Priest (purple)": 2,
    "Blacksmith (black apron)": 3,
    "Butcher (white apron)": 4,
    "Villager (green)": 5,
}

ProfessionKeys = ()
for key in Professions.keys():
    ProfessionKeys = ProfessionKeys + (key,)

inputs = [(("General Trade", "title"),
           ("This is a modified version of SethBling's Create Shops filter at DragonQuiz's request", "label"),
           ("Profession", ProfessionKeys),
           ("Add Stopping Trade", True),
           ("Invulnerable Villager", True),
           ("Make Unlimited Trades", True),
           ("Give Experience per a Trade", True),
           ("Make Villager not Move", False),
           ("Make Villager Silent", False),
           ("Villager Name", ("string", "width=250")),),

          (("Rotation", "title"),
           ("      Rotate the Position of your Trader\n"
            "*Can only be used if Not Move is checked*", "label"),
           ("Y-Axis", (0, -180, 180)),
           ("Changes its body rotation. Due west is 0. Must be between -180 to 180 degrees.", "label"),
           ("X-Axis", (0, -90, 90)),
           (
               "Changes the head rotation Horizontal is 0. Positive values look downward. Must be between -90 to 90 degrees",
               "label"),
           ),

          (("Trade Notes", "title"),
           ("To create a shop first put your buy in the top slot(s) of the chest.\n"
            "Second put a second buy in the middle slot(optional).\n"
            "Third put a sell in the bottom slot.\n"
            "Click the chest you want and choose what you want and click hit enter\n"
            "*All items must be in the same row*\n"
            , "label")),
          ]


def perform(level, box, options):
    emptyTrade = options["Add Stopping Trade"]
    invincible = options["Invulnerable Villager"]
    unlimited = options["Make Unlimited Trades"]
    xp = options["Give Experience per a Trade"]
    nomove = options["Make Villager not Move"]
    silent = options["Make Villager Silent"]
    name = options["Villager Name"]
    yaxis = options["Y-Axis"]
    xaxis = options["X-Axis"]
    for (chunk, slices, point) in level.getChunkSlices(box):
        for e in chunk.TileEntities:
            x = e["x"].value
            y = e["y"].value
            z = e["z"].value

            if (x, y, z) in box:
                if e["id"].value == "Chest":
                    createShop(level, x, y, z, emptyTrade, invincible, Professions[options["Profession"]], unlimited,
                               xp, nomove, silent, name, yaxis, xaxis)


def createShop(level, x, y, z, emptyTrade, invincible, profession, unlimited, xp, nomove, silent, name, yaxis, xaxis):
    chest = level.tileEntityAt(x, y, z)
    if chest is None:
        return

    priceList = {}
    priceListB = {}
    saleList = {}

    for item in chest["Items"]:
        slot = item["Slot"].value
        if 0 <= slot <= 8:
            priceList[slot] = item
        elif 9 <= slot <= 17:
            priceListB[slot - 9] = item
        elif 18 <= slot <= 26:
            saleList[slot - 18] = item

    villager = TAG_Compound()
    villager["PersistenceRequired"] = TAG_Byte(1)
    villager["OnGround"] = TAG_Byte(1)
    villager["Air"] = TAG_Short(300)
    villager["AttackTime"] = TAG_Short(0)
    villager["DeathTime"] = TAG_Short(0)
    villager["Fire"] = TAG_Short(-1)
    villager["Health"] = TAG_Short(20)
    villager["HurtTime"] = TAG_Short(0)
    villager["Age"] = TAG_Int(0)
    villager["Profession"] = TAG_Int(profession)
    villager["Career"] = TAG_Int(1)
    villager["CareerLevel"] = TAG_Int(1000)
    villager["Riches"] = TAG_Int(200)
    villager["FallDistance"] = TAG_Float(0)
    villager["CustomNameVisible"] = TAG_Byte(1)
    villager["CustomName"] = TAG_String(name)
    villager["Invulnerable"] = TAG_Byte(invincible)
    villager["NoAI"] = TAG_Byte(nomove)
    villager["id"] = TAG_String("Villager")
    villager["Motion"] = TAG_List([TAG_Double(0.0), TAG_Double(0.0), TAG_Double(0.0)])
    villager["Pos"] = TAG_List([TAG_Double(x + 0.5), TAG_Double(y), TAG_Double(z + 0.5)])
    villager["Rotation"] = TAG_List([TAG_Float(yaxis), TAG_Float(xaxis)])

    villager["Willing"] = TAG_Byte(0)
    villager["Offers"] = TAG_Compound()
    villager["Offers"]["Recipes"] = TAG_List()

    if silent:
        villager["Silent"] = TAG_Byte(1)
    else:
        villager["Silent"] = TAG_Byte(0)

    for i in range(9):
        if (i in priceList or i in priceListB) and i in saleList:
            offer = TAG_Compound()
            if xp:
                offer["rewardExp"] = TAG_Byte(1)
            else:
                offer["rewardExp"] = TAG_Byte(0)

            if unlimited:
                offer["uses"] = TAG_Int(0)
                offer["maxUses"] = TAG_Int(2000000000)
            else:
                offer["uses"] = TAG_Int(0)
                offer["maxUses"] = TAG_Int(1)

            if i in priceList:
                offer["buy"] = priceList[i]
            if i in priceListB:
                if i in priceList:
                    offer["buyB"] = priceListB[i]
                else:
                    offer["buy"] = priceListB[i]

            offer["sell"] = saleList[i]
            villager["Offers"]["Recipes"].append(offer)

    if emptyTrade:
        offer = TAG_Compound()
        offer["buy"] = TAG_Compound()
        offer["buy"]["Count"] = TAG_Byte(1)
        offer["buy"]["Damage"] = TAG_Short(0)
        offer["buy"]["id"] = TAG_String("minecraft:barrier")
        offer["sell"] = TAG_Compound()
        offer["sell"]["Count"] = TAG_Byte(1)
        offer["sell"]["Damage"] = TAG_Short(0)
        offer["sell"]["id"] = TAG_String("minecraft:barrier")
        villager["Offers"]["Recipes"].append(offer)

    level.setBlockAt(x, y, z, 0)

    chunk = level.getChunk(x / 16, z / 16)
    chunk.Entities.append(villager)
    chunk.TileEntities.remove(chest)
    chunk.dirty = True
