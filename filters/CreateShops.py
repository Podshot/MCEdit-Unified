# Feel free to modify and use this filter however you wish. If you do,
# please give credit to SethBling.
# http://youtube.com/SethBling
#
''' Fixed for MC 1.8 by Rezzing, September 6, 2014 
PLEASE READ: The unusable trade won't prevent new trades anymore but I
solved it by adding a very high career level. So only use it if you like
the fancy stop sign. '''
# Reedited by DragonQuiz, October 12 , 2014
#
# Changes:
# 1) Allow your villager to move or not.
# 2) Rename your villager in MCEdit.
# 3) Allow players to receive experience for their trade. (Doesn't work at the moment).
# 4) Updated some of the code, made it more prettier.
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

inputs = [( ("General Trade","title"),
	("This is a modified version of SethBling's Create Shops filter","label"),
	("Profession", ProfessionKeys),
	("Add Stopping Trade", True),
	("Invulnerable Villager", True),
	("Make Unlimited Trades", True),
	("Give Experience per a Trade", True),
	("*Experience currently works, just the option to change it doesn't*","label"),
	("Make Villager not Move", False),
	("Villager Name",("string","width=250")),),
	
	(("Trade Notes","title"),
	("To create a shop first put your buy in the top slot(s) of the chest.\n"
	"Second put a second buy in the middle slot(optional).\n"
	"Third put a sell in the bottom slot.\n"
	"Click the chest you want and choose what you want and click hit enter\n"
	"*All items must be in the same row*\n"
	"\n"
	"To change the amount of trades:\n"
	"1) Uncheck 'Unlimited Trades'\n"
	"2) Open the createshop filter using Notepad++ (link:http://notepad-plus-plus.org/) or notepad\n"
	"*The filter is where you put the MCEdit folder*\n"
	"3) Scroll to:\n" 
	            "else:\n"
				"offer[uses] = TAG_Int(0)\n"
				"offer[maxUses] = TAG_Int(1)\n"
	"4) Change the amount you want\n"
	"\n"
	"*Note: Only change the numbers as above, changing anything else will result in the filter to not work correctly*\n"
	,"label")),
	]
	
def perform(level, box, options):
	emptyTrade = options["Add Stopping Trade"]
	invincible = options["Invulnerable Villager"]
	unlimited = options["Make Unlimited Trades"]
	xp = options["Give Experience per a Trade"]
	move = options["Make Villager not Move"]
	name = options["Villager Name"]
	
	for (chunk, slices, point) in level.getChunkSlices(box):
		for e in chunk.TileEntities:
			x = e["x"].value
			y = e["y"].value
			z = e["z"].value
			
			if (x,y,z) in box:
				if e["id"].value == "Chest":
					createShop(level, x, y, z, emptyTrade, invincible, Professions[options["Profession"]], unlimited, xp, move, name)

def createShop(level, x, y, z, emptyTrade, invincible, profession, unlimited, xp, move, name):
	chest = level.tileEntityAt(x, y, z)
	if chest == None:
		return

	priceList = {}
	priceListB = {}
	saleList = {}

	for item in chest["Items"]:
		slot = item["Slot"].value
		if slot >= 0 and slot <= 8:
			priceList[slot] = item
		elif slot >= 9 and slot <= 17:
			priceListB[slot-9] = item
		elif slot >= 18 and slot <= 26:
			saleList[slot-18] = item

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
	villager["id"] = TAG_String("Villager")
	villager["Motion"] = TAG_List()
	villager["Motion"].append(TAG_Double(0))
	villager["Motion"].append(TAG_Double(0))
	villager["Motion"].append(TAG_Double(0))
	villager["Pos"] = TAG_List()
	villager["Pos"].append(TAG_Double(x + 0.5))
	villager["Pos"].append(TAG_Double(y))
	villager["Pos"].append(TAG_Double(z + 0.5))
	villager["Rotation"] = TAG_List()
	villager["Rotation"].append(TAG_Float(0))
	villager["Rotation"].append(TAG_Float(0))
	
	villager["Willing"] = TAG_Byte(0)
	villager["Offers"] = TAG_Compound()
	villager["Offers"]["Recipes"] = TAG_List()
	for i in range(9):
		if (i in priceList or i in priceListB) and i in saleList:
			offer = TAG_Compound()
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
# Currently xp isn't working as I have no idea how to fix it but if you do know you can change it
	if xp:
		if "rewardExp" not in villager:
			villager["rewardExp"] = TAG_Byte(1)
		else:
			villager["rewardExp"] = TAG_Byte(0)
						
	if invincible:
		if "Invulnerable" not in villager:
			villager["Invulnerable"] = TAG_Byte(1)
		else:
			villager["Invulnerable"] = TAG_Byte(0)
			
	if move:
		if "NoAI" not in villager:
			villager["NoAI"] = TAG_Byte(1)
		else:
			villager["NoAI"] = TAG_Byte(0)
		
	level.setBlockAt(x, y, z, 0)

	chunk = level.getChunk(x / 16, z / 16)
	chunk.Entities.append(villager)
	chunk.TileEntities.remove(chest)
	chunk.dirty = True
