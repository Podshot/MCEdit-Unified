from logging import getLogger
from numpy import zeros, rollaxis, indices
import traceback
from os.path import join
from collections import defaultdict
from pprint import pformat
import mclangres
import json
import os

NOTEX = (496, 496)

log = getLogger(__name__)


class Block(object):
    """
    Value object representing an (id, data) pair.
    Provides elements of its parent material's block arrays.
    Blocks will have (name, ID, blockData, aka, color, brightness, opacity, blockTextures)
    """

    def __str__(self):
        return "<Block {name} ({id}:{data})>".format(
            name=self.name, id=self.ID, data=self.blockData)

    def __repr__(self):
        return str(self)

    def __cmp__(self, other):
        if not isinstance(other, Block):
            return -1
        key = lambda a: a and (a.ID, a.blockData)
        return cmp(key(self), key(other))

    def __init__(self, materials, blockID, blockData=0, blockString=''):
        self.materials = materials
        self.ID = blockID
        self.blockData = blockData
        self.stringID = blockString

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        if attr == "name":
            r = self.materials.names[self.ID]
        else:
            r = getattr(self.materials, attr)[self.ID]
        if attr in ("name", "aka", "color", "type", "search"):
            r = r[self.blockData]
        return r


id_limit = 4096

class BlockstateAPI(object):
    material_map = {}
    
    def __init__(self, mats, definition_file):
        self._mats = mats
        self.block_map = {}
        self.blockstates = {}
        
        for b in self._mats:
            if b.ID == 0:
                b.stringID = "air"
            self.block_map[b.ID] = "minecraft:" + b.stringID
        
        with open(os.path.join("pymclevel", definition_file)) as def_file:
            self.blockstates = json.load(def_file)
            
        self.material_map[self._mats] = self
        
    def idToBlockstate(self, bid, data):
        '''
        Converts from a numerical ID to a BlockState string
    
        :param bid: The ID of the block
        :type bid: int
        :param data: The data value of the block
        :type data: int
        :return: The BlockState string
        :rtype: str
        '''       
        if bid not in self.block_map:
            return ("<Unknown>", {})
        
        name = self.block_map[bid].replace("minecraft:", "")

        if name not in self.blockstates["minecraft"]:
            return ("<Unknown>", {})
        
        properties = {}
        for prop in self.blockstates["minecraft"][name]["properties"]: # TODO: Change this if MCEdit's mod support ever improves
            if prop["<data>"] == data:
                for field in prop.keys():
                    if field == "<data>":
                        continue
                    properties[field] = prop[field]
                return (name, properties)
        return (name, properties)
    
    def blockstateToID(self, name, properties):
        '''
        Converts from a BlockState to a numerical ID/Data pair
    
        :param name: The BlockState name
        :type name: str
        :param properties: A list of Property/Value pairs in dict form
        :type properties: list
        :return: A tuple containing the numerical ID/Data pair (<id>, <data>)
        :rtype: tuple
        '''
        
        if ":" in name:
            prefix, name = name.split(":")
        else:
            prefix = "minecraft"
            
        if prefix not in self.blockstates:
            return (-1, -1)
        elif name not in self.blockstates[prefix]:
            return (-1, -1)
        
        bid = self.blockstates[prefix][name]["id"]
        for prop in self.blockstates[prefix][name]["properties"]:
            correct = True
            for (key, value) in properties.iteritems():
                if key in prop:
                    correct = correct and (prop[key] == value)
            if correct:
                return (bid, prop["<data>"])
        return (bid, 0)
    
    @staticmethod
    def stringifyBlockstate(name, properties):
        if not name.startswith("minecraft:"):
            name = "minecraft:" + name # This should be changed as soon as possible
        result = name + "["
        for (key, value) in properties.iteritems():
            result += "{}={},".format(key, value)
        if result.endswith("["):
            return result[:-1]
        return result[:-1] + "]"
    
    @staticmethod
    def deStringifyBlockstate(blockstate):
        seperated = blockstate.split("[")
        
        if len(seperated) == 1:
            if not seperated[0].startswith("minecraft:"):
                seperated[0] = "minecraft:" + seperated[0] 
            return (seperated[0], {})
        
        name, props = seperated
        
        if not name.startswith("minecraft:"):
            name = "minecraft:" + name
            
        properties = {}
    
        props = props[:-1]
        props = props.split(",")
        for prop in props:
            prop = prop.split("=")
            properties[prop[0]] = prop[1]
        return (name, properties)


class MCMaterials(object):
    defaultColor = (201, 119, 240, 255)
    defaultBrightness = 0
    defaultOpacity = 15
    defaultTexture = NOTEX
    defaultTex = [t // 16 for t in defaultTexture]

    def __init__(self, defaultName="Unused Block"):
        object.__init__(self)
        self.yamlDatas = []

        self.defaultName = defaultName

        self.blockTextures = zeros((id_limit, 16, 6, 2), dtype='uint16')
        # Sets the array size for terrain.png
        self.blockTextures[:] = self.defaultTexture
        self.names = [[defaultName] * 16 for _ in range(id_limit)]
        self.aka = [[""] * 16 for _ in range(id_limit)]
        self.search = [[""] * 16 for _ in range(id_limit)]

        self.type = [["NORMAL"] * 16] * id_limit
        self.blocksByType = defaultdict(list)
        self.allBlocks = []
        self.blocksByID = {}

        self.lightEmission = zeros(id_limit, dtype='uint8')
        self.lightEmission[:] = self.defaultBrightness
        self.lightAbsorption = zeros(id_limit, dtype='uint8')
        self.lightAbsorption[:] = self.defaultOpacity
        self.flatColors = zeros((id_limit, 16, 4), dtype='uint8')
        self.flatColors[:] = self.defaultColor

        self.idStr = [""] * id_limit

        self.id_limit = id_limit

        self.color = self.flatColors
        self.brightness = self.lightEmission
        self.opacity = self.lightAbsorption
        self.types = {}

        self.Air = self.addBlock(0,
                                 name="Air",
                                 texture=(0, 336),
                                 opacity=0,
        )

    def __repr__(self):
        return "<MCMaterials ({0})>".format(self.name)

    @property
    def AllStairs(self):
        return [b for b in self.allBlocks if "Stairs" in b.name]

    @property
    def AllSlabs(self):
        return [b for b in self.allBlocks if "Slab" in b.name]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        return len(self.allBlocks)

    def __iter__(self):
        return iter(self.allBlocks)

    def __getitem__(self, key):
        """ Let's be magic. If we get a string, return the first block whose
            name matches exactly. If we get a (id, data) pair or an id, return
            that block. for example:

                level.materials[0]  # returns Air
                level.materials["Air"]  # also returns Air
                level.materials["Powered Rail"]  # returns Powered Rail
                level.materials["Lapis Lazuli Block"]  # in Classic

           """
        if isinstance(key, basestring):
            for b in self.allBlocks:
                if b.name == key:
                    return b
            if "[" not in key:
                lowest_block = None
                for b in self.allBlocks:
                    if ("minecraft:{}".format(b.idStr) == key or b.idStr == key):
                        if b.blockData == 0:
                            return b
                        elif not lowest_block:
                            lowest_block = b
                        elif lowest_block.blockData > b.blockData:
                            lowest_block = b
                if lowest_block:
                    return lowest_block
            elif self.blockstate_api:
                name, properties = self.blockstate_api.deStringifyBlockstate(key)
                return self[self.blockstate_api.blockstateToID(name, properties)]
            raise KeyError("No blocks named: " + key)
        if isinstance(key, (tuple, list)):
            block_id, blockData = key
            return self.blockWithID(block_id, blockData)
        return self.blockWithID(key)

    def blocksMatching(self, name, names=None):
        toReturn = []
        name = name.lower()
        spiltNames = name.split(" ")
        amount = len(spiltNames)
        for i, v in enumerate(self.allBlocks):
            if names is None:
                nameParts = v.name.lower().split(" ")
                for anotherName in v.aka.lower().split(" "):
                    nameParts.append(anotherName)
                for anotherName in v.search.lower().split(" "):
                    nameParts.append(anotherName)
            else:
                nameParts = names[i].lower().split(" ")
            i = 0
            spiltNamesUsed = []
            for v2 in nameParts:
                Start = True
                j = 0
                while j < len(spiltNames) and Start:
                    if spiltNames[j] in v2 and j not in spiltNamesUsed:
                        i += 1
                        spiltNamesUsed.append(j)
                        Start = False
                    j += 1
            if i == amount:
                toReturn.append(v)
        return toReturn

    def blockWithID(self, block_id, data=0):
        if (block_id, data) in self.blocksByID:
            return self.blocksByID[block_id, data]
        else:
            bl = Block(self, block_id, blockData=data)
            return bl
        
    def setup_blockstates(self, blockstate_definition_file):
        self.blockstate_api = BlockstateAPI(self, blockstate_definition_file)

    def addJSONBlocksFromFile(self, filename):
        try:
            import pkg_resources

            f = pkg_resources.resource_stream(__name__, filename)
        except (ImportError, IOError), e:
            log.debug("Cannot get resource_stream for %s %s"%(filename, e))
            root = os.environ.get("PYMCLEVEL_YAML_ROOT", "pymclevel")  # fall back to cwd as last resort
            path = join(root, filename)

            log.debug("Failed to read %s using pkg_resources. Trying %s instead." % (filename, path))

            f = file(path)
        try:
            log.info(u"Loading block info from %s", f)
            blockyaml = json.load(f)
            #blockyaml = yaml.load(f)
            self.addJSONBlocks(blockyaml)

        except Exception, e:
            log.warn(u"Exception while loading block info from %s: %s", f, e)
            traceback.print_exc()

    def addJSONBlocks(self, blockyaml):
        self.yamlDatas.append(blockyaml)
        for block in blockyaml['blocks']:
            try:
                self.addJSONBlock(block)
            except Exception, e:
                log.warn(u"Exception while parsing block: %s", e)
                traceback.print_exc()
                log.warn(u"Block definition: \n%s", pformat(block))

    def addJSONBlock(self, kw):
        blockID = kw['id']

        # xxx unused_yaml_properties variable unused; needed for
        # documentation purpose of some sort?  -zothar
        # unused_yaml_properties = \
        #['explored',
        # # 'id',
        # # 'idStr',
        # # 'mapcolor',
        # # 'name',
        # # 'tex',
        # ### 'tex_data',
        # # 'tex_direction',
        # ### 'tex_direction_data',
        # 'tex_extra',
        # # 'type'
        # ]

        for val, data in kw.get('data', {0: {}}).items():
            datakw = dict(kw)
            datakw.update(data)
            idStr = datakw.get('idStr', "")
            tex = [t * 16 for t in datakw.get('tex', self.defaultTex)]
            texture = [tex] * 6
            texDirs = {
                "FORWARD": 5,
                "BACKWARD": 4,
                "LEFT": 1,
                "RIGHT": 0,
                "TOP": 2,
                "BOTTOM": 3,
            }
            for dirname, dirtex in datakw.get('tex_direction', {}).items():
                if dirname == "SIDES":
                    for dirname in ("LEFT", "RIGHT"):
                        texture[texDirs[dirname]] = [t * 16 for t in dirtex]
                if dirname in texDirs:
                    texture[texDirs[dirname]] = [t * 16 for t in dirtex]
            datakw['texture'] = texture
            # print datakw
            block = self.addBlock(blockID, val, **datakw)
            block.yaml = datakw
            self.idStr[blockID] = idStr

        tex_direction_data = kw.get('tex_direction_data')
        if tex_direction_data:
            texture = datakw['texture']
            # X+0, X-1, Y+, Y-, Z+b, Z-f
            texDirMap = {
                "NORTH": 0,
                "EAST": 1,
                "SOUTH": 2,
                "WEST": 3,
            }

            def rot90cw():
                rot = (5, 0, 2, 3, 4, 1)
                texture[:] = [texture[r] for r in rot]

            for data, direction in tex_direction_data.items():
                for _i in range(texDirMap.get(direction, 0)):
                    rot90cw()
                self.blockTextures[blockID][int(data)] = texture

    def addBlock(self, blockID, blockData=0, **kw):
        blockData = int(blockData)
        try:
            name = kw.pop('name', self.names[blockID][blockData])
        except:
            print (blockID, blockData)
        stringName = kw.pop('idStr', '')

        self.lightEmission[blockID] = kw.pop('brightness', self.defaultBrightness)
        self.lightAbsorption[blockID] = kw.pop('opacity', self.defaultOpacity)
        self.aka[blockID][blockData] = kw.pop('aka', "")
        self.search[blockID][blockData] = kw.pop('search', "")
        block_type = kw.pop('type', 'NORMAL')

        color = kw.pop('mapcolor', self.flatColors[blockID, blockData])
        self.flatColors[blockID, blockData] = (tuple(color) + (255,))[:4]

        texture = kw.pop('texture', None)

        if texture:
            self.blockTextures[blockID, blockData] = texture

        self.names[blockID][blockData] = name
        if blockData is 0:
            self.type[blockID] = [block_type] * 16
        else:
            self.type[blockID][blockData] = block_type

        block = Block(self, blockID, blockData, stringName)

        if kw.pop('invalid', 'false') == 'false':
            self.allBlocks.append(block)
        self.blocksByType[block_type].append(block)

        self.blocksByID[blockID, blockData] = block

        return block


alphaMaterials = MCMaterials(defaultName="Future Block!")
alphaMaterials.name = "Alpha"
alphaMaterials.addJSONBlocksFromFile("minecraft.json")
alphaMaterials.setup_blockstates("pc_blockstates.json")

classicMaterials = MCMaterials(defaultName="Not present in Classic")
classicMaterials.name = "Classic"
classicMaterials.addJSONBlocksFromFile("classic.json")

indevMaterials = MCMaterials(defaultName="Not present in Indev")
indevMaterials.name = "Indev"
indevMaterials.addJSONBlocksFromFile("indev.json")

pocketMaterials = MCMaterials()
pocketMaterials.name = "Pocket"
pocketMaterials.addJSONBlocksFromFile("pocket.json")
pocketMaterials.setup_blockstates("pe_blockstates.json")

# --- Static block defs ---

alphaMaterials.Stone = alphaMaterials[1, 0]
alphaMaterials.Grass = alphaMaterials[2, 0]
alphaMaterials.Dirt = alphaMaterials[3, 0]
alphaMaterials.Cobblestone = alphaMaterials[4, 0]
alphaMaterials.WoodPlanks = alphaMaterials[5, 0]
alphaMaterials.Sapling = alphaMaterials[6, 0]
alphaMaterials.SpruceSapling = alphaMaterials[6, 1]
alphaMaterials.BirchSapling = alphaMaterials[6, 2]
alphaMaterials.Bedrock = alphaMaterials[7, 0]
alphaMaterials.WaterActive = alphaMaterials[8, 0]
alphaMaterials.Water = alphaMaterials[9, 0]
alphaMaterials.LavaActive = alphaMaterials[10, 0]
alphaMaterials.Lava = alphaMaterials[11, 0]
alphaMaterials.Sand = alphaMaterials[12, 0]
alphaMaterials.Gravel = alphaMaterials[13, 0]
alphaMaterials.GoldOre = alphaMaterials[14, 0]
alphaMaterials.IronOre = alphaMaterials[15, 0]
alphaMaterials.CoalOre = alphaMaterials[16, 0]
alphaMaterials.Wood = alphaMaterials[17, 0]
alphaMaterials.PineWood = alphaMaterials[17, 1]
alphaMaterials.BirchWood = alphaMaterials[17, 2]
alphaMaterials.JungleWood = alphaMaterials[17, 3]
alphaMaterials.Leaves = alphaMaterials[18, 0]
alphaMaterials.PineLeaves = alphaMaterials[18, 1]
alphaMaterials.BirchLeaves = alphaMaterials[18, 2]
alphaMaterials.JungleLeaves = alphaMaterials[18, 3]
alphaMaterials.LeavesPermanent = alphaMaterials[18, 4]
alphaMaterials.PineLeavesPermanent = alphaMaterials[18, 5]
alphaMaterials.BirchLeavesPermanent = alphaMaterials[18, 6]
alphaMaterials.JungleLeavesPermanent = alphaMaterials[18, 7]
alphaMaterials.LeavesDecaying = alphaMaterials[18, 8]
alphaMaterials.PineLeavesDecaying = alphaMaterials[18, 9]
alphaMaterials.BirchLeavesDecaying = alphaMaterials[18, 10]
alphaMaterials.JungleLeavesDecaying = alphaMaterials[18, 11]
alphaMaterials.Sponge = alphaMaterials[19, 0]
alphaMaterials.Glass = alphaMaterials[20, 0]
alphaMaterials.LapisLazuliOre = alphaMaterials[21, 0]
alphaMaterials.LapisLazuliBlock = alphaMaterials[22, 0]
alphaMaterials.Dispenser = alphaMaterials[23, 0]
alphaMaterials.Sandstone = alphaMaterials[24, 0]
alphaMaterials.NoteBlock = alphaMaterials[25, 0]
alphaMaterials.Bed = alphaMaterials[26, 0]
alphaMaterials.PoweredRail = alphaMaterials[27, 0]
alphaMaterials.DetectorRail = alphaMaterials[28, 0]
alphaMaterials.StickyPiston = alphaMaterials[29, 0]
alphaMaterials.Web = alphaMaterials[30, 0]
alphaMaterials.UnusedShrub = alphaMaterials[31, 0]
alphaMaterials.TallGrass = alphaMaterials[31, 1]
alphaMaterials.Shrub = alphaMaterials[31, 2]
alphaMaterials.DesertShrub2 = alphaMaterials[32, 0]
alphaMaterials.Piston = alphaMaterials[33, 0]
alphaMaterials.PistonHead = alphaMaterials[34, 0]
alphaMaterials.WhiteWool = alphaMaterials[35, 0]
alphaMaterials.OrangeWool = alphaMaterials[35, 1]
alphaMaterials.MagentaWool = alphaMaterials[35, 2]
alphaMaterials.LightBlueWool = alphaMaterials[35, 3]
alphaMaterials.YellowWool = alphaMaterials[35, 4]
alphaMaterials.LightGreenWool = alphaMaterials[35, 5]
alphaMaterials.PinkWool = alphaMaterials[35, 6]
alphaMaterials.GrayWool = alphaMaterials[35, 7]
alphaMaterials.LightGrayWool = alphaMaterials[35, 8]
alphaMaterials.CyanWool = alphaMaterials[35, 9]
alphaMaterials.PurpleWool = alphaMaterials[35, 10]
alphaMaterials.BlueWool = alphaMaterials[35, 11]
alphaMaterials.BrownWool = alphaMaterials[35, 12]
alphaMaterials.DarkGreenWool = alphaMaterials[35, 13]
alphaMaterials.RedWool = alphaMaterials[35, 14]
alphaMaterials.BlackWool = alphaMaterials[35, 15]
alphaMaterials.Block36 = alphaMaterials[36, 0]
alphaMaterials.Flower = alphaMaterials[37, 0]
alphaMaterials.Rose = alphaMaterials[38, 0]
alphaMaterials.BrownMushroom = alphaMaterials[39, 0]
alphaMaterials.RedMushroom = alphaMaterials[40, 0]
alphaMaterials.BlockofGold = alphaMaterials[41, 0]
alphaMaterials.BlockofIron = alphaMaterials[42, 0]
alphaMaterials.DoubleStoneSlab = alphaMaterials[43, 0]
alphaMaterials.DoubleSandstoneSlab = alphaMaterials[43, 1]
alphaMaterials.DoubleWoodenSlab = alphaMaterials[43, 2]
alphaMaterials.DoubleCobblestoneSlab = alphaMaterials[43, 3]
alphaMaterials.DoubleBrickSlab = alphaMaterials[43, 4]
alphaMaterials.DoubleStoneBrickSlab = alphaMaterials[43, 5]
alphaMaterials.StoneSlab = alphaMaterials[44, 0]
alphaMaterials.SandstoneSlab = alphaMaterials[44, 1]
alphaMaterials.WoodenSlab = alphaMaterials[44, 2]
alphaMaterials.CobblestoneSlab = alphaMaterials[44, 3]
alphaMaterials.BrickSlab = alphaMaterials[44, 4]
alphaMaterials.StoneBrickSlab = alphaMaterials[44, 5]
alphaMaterials.Brick = alphaMaterials[45, 0]
alphaMaterials.TNT = alphaMaterials[46, 0]
alphaMaterials.Bookshelf = alphaMaterials[47, 0]
alphaMaterials.MossStone = alphaMaterials[48, 0]
alphaMaterials.Obsidian = alphaMaterials[49, 0]
alphaMaterials.Torch = alphaMaterials[50, 0]
alphaMaterials.Fire = alphaMaterials[51, 0]
alphaMaterials.MonsterSpawner = alphaMaterials[52, 0]
alphaMaterials.WoodenStairs = alphaMaterials[53, 0]
alphaMaterials.Chest = alphaMaterials[54, 0]
alphaMaterials.RedstoneWire = alphaMaterials[55, 0]
alphaMaterials.DiamondOre = alphaMaterials[56, 0]
alphaMaterials.BlockofDiamond = alphaMaterials[57, 0]
alphaMaterials.CraftingTable = alphaMaterials[58, 0]
alphaMaterials.Crops = alphaMaterials[59, 0]
alphaMaterials.Farmland = alphaMaterials[60, 0]
alphaMaterials.Furnace = alphaMaterials[61, 0]
alphaMaterials.LitFurnace = alphaMaterials[62, 0]
alphaMaterials.Sign = alphaMaterials[63, 0]
alphaMaterials.WoodenDoor = alphaMaterials[64, 0]
alphaMaterials.Ladder = alphaMaterials[65, 0]
alphaMaterials.Rail = alphaMaterials[66, 0]
alphaMaterials.StoneStairs = alphaMaterials[67, 0]
alphaMaterials.WallSign = alphaMaterials[68, 0]
alphaMaterials.Lever = alphaMaterials[69, 0]
alphaMaterials.StoneFloorPlate = alphaMaterials[70, 0]
alphaMaterials.IronDoor = alphaMaterials[71, 0]
alphaMaterials.WoodFloorPlate = alphaMaterials[72, 0]
alphaMaterials.RedstoneOre = alphaMaterials[73, 0]
alphaMaterials.RedstoneOreGlowing = alphaMaterials[74, 0]
alphaMaterials.RedstoneTorchOff = alphaMaterials[75, 0]
alphaMaterials.RedstoneTorchOn = alphaMaterials[76, 0]
alphaMaterials.Button = alphaMaterials[77, 0]
alphaMaterials.SnowLayer = alphaMaterials[78, 0]
alphaMaterials.Ice = alphaMaterials[79, 0]
alphaMaterials.Snow = alphaMaterials[80, 0]
alphaMaterials.Cactus = alphaMaterials[81, 0]
alphaMaterials.Clay = alphaMaterials[82, 0]
alphaMaterials.SugarCane = alphaMaterials[83, 0]
alphaMaterials.Jukebox = alphaMaterials[84, 0]
alphaMaterials.Fence = alphaMaterials[85, 0]
alphaMaterials.Pumpkin = alphaMaterials[86, 0]
alphaMaterials.Netherrack = alphaMaterials[87, 0]
alphaMaterials.SoulSand = alphaMaterials[88, 0]
alphaMaterials.Glowstone = alphaMaterials[89, 0]
alphaMaterials.NetherPortal = alphaMaterials[90, 0]
alphaMaterials.JackOLantern = alphaMaterials[91, 0]
alphaMaterials.Cake = alphaMaterials[92, 0]
alphaMaterials.RedstoneRepeaterOff = alphaMaterials[93, 0]
alphaMaterials.RedstoneRepeaterOn = alphaMaterials[94, 0]
alphaMaterials.StainedGlass = alphaMaterials[95, 0]
alphaMaterials.Trapdoor = alphaMaterials[96, 0]
alphaMaterials.HiddenSilverfishStone = alphaMaterials[97, 0]
alphaMaterials.HiddenSilverfishCobblestone = alphaMaterials[97, 1]
alphaMaterials.HiddenSilverfishStoneBrick = alphaMaterials[97, 2]
alphaMaterials.StoneBricks = alphaMaterials[98, 0]
alphaMaterials.MossyStoneBricks = alphaMaterials[98, 1]
alphaMaterials.CrackedStoneBricks = alphaMaterials[98, 2]
alphaMaterials.HugeBrownMushroom = alphaMaterials[99, 0]
alphaMaterials.HugeRedMushroom = alphaMaterials[100, 0]
alphaMaterials.IronBars = alphaMaterials[101, 0]
alphaMaterials.GlassPane = alphaMaterials[102, 0]
alphaMaterials.Watermelon = alphaMaterials[103, 0]
alphaMaterials.PumpkinStem = alphaMaterials[104, 0]
alphaMaterials.MelonStem = alphaMaterials[105, 0]
alphaMaterials.Vines = alphaMaterials[106, 0]
alphaMaterials.FenceGate = alphaMaterials[107, 0]
alphaMaterials.BrickStairs = alphaMaterials[108, 0]
alphaMaterials.StoneBrickStairs = alphaMaterials[109, 0]
alphaMaterials.Mycelium = alphaMaterials[110, 0]
alphaMaterials.Lilypad = alphaMaterials[111, 0]
alphaMaterials.NetherBrick = alphaMaterials[112, 0]
alphaMaterials.NetherBrickFence = alphaMaterials[113, 0]
alphaMaterials.NetherBrickStairs = alphaMaterials[114, 0]
alphaMaterials.NetherWart = alphaMaterials[115, 0]
alphaMaterials.EnchantmentTable = alphaMaterials[116, 0]
alphaMaterials.BrewingStand = alphaMaterials[117, 0]
alphaMaterials.Cauldron = alphaMaterials[118, 0]
alphaMaterials.EnderPortal = alphaMaterials[119, 0]
alphaMaterials.PortalFrame = alphaMaterials[120, 0]
alphaMaterials.EndStone = alphaMaterials[121, 0]
alphaMaterials.DragonEgg = alphaMaterials[122, 0]
alphaMaterials.RedstoneLampoff = alphaMaterials[123, 0]
alphaMaterials.RedstoneLampon = alphaMaterials[124, 0]
alphaMaterials.OakWoodDoubleSlab = alphaMaterials[125, 0]
alphaMaterials.SpruceWoodDoubleSlab = alphaMaterials[125, 1]
alphaMaterials.BirchWoodDoubleSlab = alphaMaterials[125, 2]
alphaMaterials.JungleWoodDoubleSlab = alphaMaterials[125, 3]
alphaMaterials.OakWoodSlab = alphaMaterials[126, 0]
alphaMaterials.SpruceWoodSlab = alphaMaterials[126, 1]
alphaMaterials.BirchWoodSlab = alphaMaterials[126, 2]
alphaMaterials.JungleWoodSlab = alphaMaterials[126, 3]
alphaMaterials.CocoaPlant = alphaMaterials[127, 0]
alphaMaterials.SandstoneStairs = alphaMaterials[128, 0]
alphaMaterials.EmeraldOre = alphaMaterials[129, 0]
alphaMaterials.EnderChest = alphaMaterials[130, 0]
alphaMaterials.TripwireHook = alphaMaterials[131, 0]
alphaMaterials.Tripwire = alphaMaterials[132, 0]
alphaMaterials.BlockofEmerald = alphaMaterials[133, 0]
alphaMaterials.SpruceWoodStairs = alphaMaterials[134, 0]
alphaMaterials.BirchWoodStairs = alphaMaterials[135, 0]
alphaMaterials.JungleWoodStairs = alphaMaterials[136, 0]
alphaMaterials.CommandBlock = alphaMaterials[137, 0]
alphaMaterials.BeaconBlock = alphaMaterials[138, 0]
alphaMaterials.CobblestoneWall = alphaMaterials[139, 0]
alphaMaterials.MossyCobblestoneWall = alphaMaterials[139, 1]
alphaMaterials.FlowerPot = alphaMaterials[140, 0]
alphaMaterials.Carrots = alphaMaterials[141, 0]
alphaMaterials.Potatoes = alphaMaterials[142, 0]
alphaMaterials.WoodenButton = alphaMaterials[143, 0]
alphaMaterials.MobHead = alphaMaterials[144, 0]
alphaMaterials.Anvil = alphaMaterials[145, 0]
alphaMaterials.TrappedChest = alphaMaterials[146, 0]
alphaMaterials.WeightedPressurePlateLight = alphaMaterials[147, 0]
alphaMaterials.WeightedPressurePlateHeavy = alphaMaterials[148, 0]
alphaMaterials.RedstoneComparatorInactive = alphaMaterials[149, 0]
alphaMaterials.RedstoneComparatorActive = alphaMaterials[150, 0]
alphaMaterials.DaylightSensor = alphaMaterials[151, 0]
alphaMaterials.BlockofRedstone = alphaMaterials[152, 0]
alphaMaterials.NetherQuartzOre = alphaMaterials[153, 0]
alphaMaterials.Hopper = alphaMaterials[154, 0]
alphaMaterials.BlockofQuartz = alphaMaterials[155, 0]
alphaMaterials.QuartzStairs = alphaMaterials[156, 0]
alphaMaterials.ActivatorRail = alphaMaterials[157, 0]
alphaMaterials.Dropper = alphaMaterials[158, 0]
alphaMaterials.StainedClay = alphaMaterials[159, 0]
alphaMaterials.StainedGlassPane = alphaMaterials[160, 0]
alphaMaterials.AcaciaLeaves = alphaMaterials[161, 0]
alphaMaterials.DarkOakLeaves = alphaMaterials[161, 1]
alphaMaterials.AcaciaLeavesPermanent = alphaMaterials[161, 4]
alphaMaterials.DarkOakLeavesPermanent = alphaMaterials[161, 5]
alphaMaterials.AcaciaLeavesDecaying = alphaMaterials[161, 8]
alphaMaterials.DarkOakLeavesDecaying = alphaMaterials[161, 9]
alphaMaterials.Wood2 = alphaMaterials[162, 0]
alphaMaterials.AcaciaStairs = alphaMaterials[163, 0]
alphaMaterials.DarkOakStairs = alphaMaterials[164, 0]
alphaMaterials.SlimeBlock = alphaMaterials[165, 0]
alphaMaterials.Barrier = alphaMaterials[166, 0]
alphaMaterials.IronTrapdoor = alphaMaterials[167, 0]
alphaMaterials.Prismarine = alphaMaterials[168, 0]
alphaMaterials.SeaLantern = alphaMaterials[169, 0]
alphaMaterials.HayBlock = alphaMaterials[170, 0]
alphaMaterials.Carpet = alphaMaterials[171, 0]
alphaMaterials.HardenedClay = alphaMaterials[172, 0]
alphaMaterials.CoalBlock = alphaMaterials[173, 0]
alphaMaterials.PackedIce = alphaMaterials[174, 0]
alphaMaterials.TallFlowers = alphaMaterials[175, 0]
alphaMaterials.StandingBanner = alphaMaterials[176, 0]
alphaMaterials.WallBanner = alphaMaterials[177, 0]
alphaMaterials.DaylightSensorOn = alphaMaterials[178, 0]
alphaMaterials.RedSandstone = alphaMaterials[179, 0]
alphaMaterials.SmooothRedSandstone = alphaMaterials[179, 1]
alphaMaterials.RedSandstoneSairs = alphaMaterials[180, 0]
alphaMaterials.DoubleRedSandstoneSlab = alphaMaterials[181, 0]
alphaMaterials.RedSandstoneSlab = alphaMaterials[182, 0]
alphaMaterials.SpruceFenceGate = alphaMaterials[183, 0]
alphaMaterials.BirchFenceGate = alphaMaterials[184, 0]
alphaMaterials.JungleFenceGate = alphaMaterials[185, 0]
alphaMaterials.DarkOakFenceGate = alphaMaterials[186, 0]
alphaMaterials.AcaciaFenceGate = alphaMaterials[187, 0]
alphaMaterials.SpruceFence = alphaMaterials[188, 0]
alphaMaterials.BirchFence = alphaMaterials[189, 0]
alphaMaterials.JungleFence = alphaMaterials[190, 0]
alphaMaterials.DarkOakFence = alphaMaterials[191, 0]
alphaMaterials.AcaciaFence = alphaMaterials[192, 0]
alphaMaterials.SpruceDoor = alphaMaterials[193, 0]
alphaMaterials.BirchDoor = alphaMaterials[194, 0]
alphaMaterials.JungleDoor = alphaMaterials[195, 0]
alphaMaterials.AcaciaDoor = alphaMaterials[196, 0]
alphaMaterials.DarkOakDoor = alphaMaterials[197, 0]
alphaMaterials.EndRod = alphaMaterials[198, 0]
alphaMaterials.ChorusPlant = alphaMaterials[199, 0]
alphaMaterials.ChorusFlowerAlive = alphaMaterials[200, 0]
alphaMaterials.ChorusFlowerDead = alphaMaterials[200, 5]
alphaMaterials.Purpur = alphaMaterials[201, 0]
alphaMaterials.PurpurPillar = alphaMaterials[202, 0]
alphaMaterials.PurpurStairs = alphaMaterials[203, 0]
alphaMaterials.PurpurSlab = alphaMaterials[205, 0]
alphaMaterials.EndStone = alphaMaterials[206, 0]
alphaMaterials.BeetRoot = alphaMaterials[207, 0]
alphaMaterials.GrassPath = alphaMaterials[208, 0]
alphaMaterials.EndGateway = alphaMaterials[209, 0]
alphaMaterials.CommandBlockRepeating = alphaMaterials[210, 0]
alphaMaterials.CommandBlockChain = alphaMaterials[211, 0]
alphaMaterials.FrostedIce = alphaMaterials[212, 0]
alphaMaterials.StructureVoid = alphaMaterials[217, 0]
alphaMaterials.StructureBlock = alphaMaterials[255, 0]

# --- Classic static block defs ---
classicMaterials.Stone = classicMaterials[1]
classicMaterials.Grass = classicMaterials[2]
classicMaterials.Dirt = classicMaterials[3]
classicMaterials.Cobblestone = classicMaterials[4]
classicMaterials.WoodPlanks = classicMaterials[5]
classicMaterials.Sapling = classicMaterials[6]
classicMaterials.Bedrock = classicMaterials[7]
classicMaterials.WaterActive = classicMaterials[8]
classicMaterials.Water = classicMaterials[9]
classicMaterials.LavaActive = classicMaterials[10]
classicMaterials.Lava = classicMaterials[11]
classicMaterials.Sand = classicMaterials[12]
classicMaterials.Gravel = classicMaterials[13]
classicMaterials.GoldOre = classicMaterials[14]
classicMaterials.IronOre = classicMaterials[15]
classicMaterials.CoalOre = classicMaterials[16]
classicMaterials.Wood = classicMaterials[17]
classicMaterials.Leaves = classicMaterials[18]
classicMaterials.Sponge = classicMaterials[19]
classicMaterials.Glass = classicMaterials[20]

classicMaterials.RedWool = classicMaterials[21]
classicMaterials.OrangeWool = classicMaterials[22]
classicMaterials.YellowWool = classicMaterials[23]
classicMaterials.LimeWool = classicMaterials[24]
classicMaterials.GreenWool = classicMaterials[25]
classicMaterials.AquaWool = classicMaterials[26]
classicMaterials.CyanWool = classicMaterials[27]
classicMaterials.BlueWool = classicMaterials[28]
classicMaterials.PurpleWool = classicMaterials[29]
classicMaterials.IndigoWool = classicMaterials[30]
classicMaterials.VioletWool = classicMaterials[31]
classicMaterials.MagentaWool = classicMaterials[32]
classicMaterials.PinkWool = classicMaterials[33]
classicMaterials.BlackWool = classicMaterials[34]
classicMaterials.GrayWool = classicMaterials[35]
classicMaterials.WhiteWool = classicMaterials[36]

classicMaterials.Flower = classicMaterials[37]
classicMaterials.Rose = classicMaterials[38]
classicMaterials.BrownMushroom = classicMaterials[39]
classicMaterials.RedMushroom = classicMaterials[40]
classicMaterials.BlockofGold = classicMaterials[41]
classicMaterials.BlockofIron = classicMaterials[42]
classicMaterials.DoubleStoneSlab = classicMaterials[43]
classicMaterials.StoneSlab = classicMaterials[44]
classicMaterials.Brick = classicMaterials[45]
classicMaterials.TNT = classicMaterials[46]
classicMaterials.Bookshelf = classicMaterials[47]
classicMaterials.MossStone = classicMaterials[48]
classicMaterials.Obsidian = classicMaterials[49]

# --- Indev static block defs ---
indevMaterials.Stone = indevMaterials[1]
indevMaterials.Grass = indevMaterials[2]
indevMaterials.Dirt = indevMaterials[3]
indevMaterials.Cobblestone = indevMaterials[4]
indevMaterials.WoodPlanks = indevMaterials[5]
indevMaterials.Sapling = indevMaterials[6]
indevMaterials.Bedrock = indevMaterials[7]
indevMaterials.WaterActive = indevMaterials[8]
indevMaterials.Water = indevMaterials[9]
indevMaterials.LavaActive = indevMaterials[10]
indevMaterials.Lava = indevMaterials[11]
indevMaterials.Sand = indevMaterials[12]
indevMaterials.Gravel = indevMaterials[13]
indevMaterials.GoldOre = indevMaterials[14]
indevMaterials.IronOre = indevMaterials[15]
indevMaterials.CoalOre = indevMaterials[16]
indevMaterials.Wood = indevMaterials[17]
indevMaterials.Leaves = indevMaterials[18]
indevMaterials.Sponge = indevMaterials[19]
indevMaterials.Glass = indevMaterials[20]

indevMaterials.RedWool = indevMaterials[21]
indevMaterials.OrangeWool = indevMaterials[22]
indevMaterials.YellowWool = indevMaterials[23]
indevMaterials.LimeWool = indevMaterials[24]
indevMaterials.GreenWool = indevMaterials[25]
indevMaterials.AquaWool = indevMaterials[26]
indevMaterials.CyanWool = indevMaterials[27]
indevMaterials.BlueWool = indevMaterials[28]
indevMaterials.PurpleWool = indevMaterials[29]
indevMaterials.IndigoWool = indevMaterials[30]
indevMaterials.VioletWool = indevMaterials[31]
indevMaterials.MagentaWool = indevMaterials[32]
indevMaterials.PinkWool = indevMaterials[33]
indevMaterials.BlackWool = indevMaterials[34]
indevMaterials.GrayWool = indevMaterials[35]
indevMaterials.WhiteWool = indevMaterials[36]

indevMaterials.Flower = indevMaterials[37]
indevMaterials.Rose = indevMaterials[38]
indevMaterials.BrownMushroom = indevMaterials[39]
indevMaterials.RedMushroom = indevMaterials[40]
indevMaterials.BlockofGold = indevMaterials[41]
indevMaterials.BlockofIron = indevMaterials[42]
indevMaterials.DoubleStoneSlab = indevMaterials[43]
indevMaterials.StoneSlab = indevMaterials[44]
indevMaterials.Brick = indevMaterials[45]
indevMaterials.TNT = indevMaterials[46]
indevMaterials.Bookshelf = indevMaterials[47]
indevMaterials.MossStone = indevMaterials[48]
indevMaterials.Obsidian = indevMaterials[49]

indevMaterials.Torch = indevMaterials[50, 0]
indevMaterials.Fire = indevMaterials[51, 0]
indevMaterials.InfiniteWater = indevMaterials[52, 0]
indevMaterials.InfiniteLava = indevMaterials[53, 0]
indevMaterials.Chest = indevMaterials[54, 0]
indevMaterials.Cog = indevMaterials[55, 0]
indevMaterials.DiamondOre = indevMaterials[56, 0]
indevMaterials.BlockofDiamond = indevMaterials[57, 0]
indevMaterials.CraftingTable = indevMaterials[58, 0]
indevMaterials.Crops = indevMaterials[59, 0]
indevMaterials.Farmland = indevMaterials[60, 0]
indevMaterials.Furnace = indevMaterials[61, 0]
indevMaterials.LitFurnace = indevMaterials[62, 0]

# --- Pocket static block defs ---

pocketMaterials.Air = pocketMaterials[0, 0]
pocketMaterials.Stone = pocketMaterials[1, 0]
pocketMaterials.Grass = pocketMaterials[2, 0]
pocketMaterials.Dirt = pocketMaterials[3, 0]
pocketMaterials.Cobblestone = pocketMaterials[4, 0]
pocketMaterials.WoodPlanks = pocketMaterials[5, 0]
pocketMaterials.Sapling = pocketMaterials[6, 0]
pocketMaterials.SpruceSapling = pocketMaterials[6, 1]
pocketMaterials.BirchSapling = pocketMaterials[6, 2]
pocketMaterials.Bedrock = pocketMaterials[7, 0]
pocketMaterials.Wateractive = pocketMaterials[8, 0]
pocketMaterials.Water = pocketMaterials[9, 0]
pocketMaterials.Lavaactive = pocketMaterials[10, 0]
pocketMaterials.Lava = pocketMaterials[11, 0]
pocketMaterials.Sand = pocketMaterials[12, 0]
pocketMaterials.Gravel = pocketMaterials[13, 0]
pocketMaterials.GoldOre = pocketMaterials[14, 0]
pocketMaterials.IronOre = pocketMaterials[15, 0]
pocketMaterials.CoalOre = pocketMaterials[16, 0]

pocketMaterials.Wood = pocketMaterials[17, 0]
pocketMaterials.PineWood = pocketMaterials[17, 1]
pocketMaterials.BirchWood = pocketMaterials[17, 2]
pocketMaterials.JungleWood = pocketMaterials[17, 3]
pocketMaterials.Leaves = pocketMaterials[18, 0]
pocketMaterials.PineLeaves = pocketMaterials[18, 1]
pocketMaterials.BirchLeaves = pocketMaterials[18, 2]
pocketMaterials.JungleLeaves = pocketMaterials[18, 3]

pocketMaterials.Sponge = pocketMaterials[19, 0]
pocketMaterials.Glass = pocketMaterials[20, 0]

pocketMaterials.LapisLazuliOre = pocketMaterials[21, 0]
pocketMaterials.LapisLazuliBlock = pocketMaterials[22, 0]
pocketMaterials.Sandstone = pocketMaterials[24, 0]
pocketMaterials.NoteBlock = pocketMaterials[25, 0]
pocketMaterials.Bed = pocketMaterials[26, 0]
pocketMaterials.PoweredRail = pocketMaterials[27, 0]
pocketMaterials.DetectorRail = pocketMaterials[28, 0]
pocketMaterials.Web = pocketMaterials[30, 0]
pocketMaterials.UnusedShrub = pocketMaterials[31, 0]
pocketMaterials.TallGrass = pocketMaterials[31, 1]
pocketMaterials.Shrub = pocketMaterials[31, 2]

pocketMaterials.WhiteWool = pocketMaterials[35, 0]
pocketMaterials.OrangeWool = pocketMaterials[35, 1]
pocketMaterials.MagentaWool = pocketMaterials[35, 2]
pocketMaterials.LightBlueWool = pocketMaterials[35, 3]
pocketMaterials.YellowWool = pocketMaterials[35, 4]
pocketMaterials.LightGreenWool = pocketMaterials[35, 5]
pocketMaterials.PinkWool = pocketMaterials[35, 6]
pocketMaterials.GrayWool = pocketMaterials[35, 7]
pocketMaterials.LightGrayWool = pocketMaterials[35, 8]
pocketMaterials.CyanWool = pocketMaterials[35, 9]
pocketMaterials.PurpleWool = pocketMaterials[35, 10]
pocketMaterials.BlueWool = pocketMaterials[35, 11]
pocketMaterials.BrownWool = pocketMaterials[35, 12]
pocketMaterials.DarkGreenWool = pocketMaterials[35, 13]
pocketMaterials.RedWool = pocketMaterials[35, 14]
pocketMaterials.BlackWool = pocketMaterials[35, 15]

pocketMaterials.Flower = pocketMaterials[37, 0]
pocketMaterials.Rose = pocketMaterials[38, 0]
pocketMaterials.BrownMushroom = pocketMaterials[39, 0]
pocketMaterials.RedMushroom = pocketMaterials[40, 0]
pocketMaterials.BlockofGold = pocketMaterials[41, 0]
pocketMaterials.BlockofIron = pocketMaterials[42, 0]

pocketMaterials.DoubleStoneSlab = pocketMaterials[43, 0]
pocketMaterials.DoubleSandstoneSlab = pocketMaterials[43, 1]
pocketMaterials.DoubleWoodenSlab = pocketMaterials[43, 2]
pocketMaterials.DoubleCobblestoneSlab = pocketMaterials[43, 3]
pocketMaterials.DoubleBrickSlab = pocketMaterials[43, 4]
pocketMaterials.StoneSlab = pocketMaterials[44, 0]
pocketMaterials.SandstoneSlab = pocketMaterials[44, 1]
pocketMaterials.WoodenSlab = pocketMaterials[44, 2]
pocketMaterials.CobblestoneSlab = pocketMaterials[44, 3]
pocketMaterials.BrickSlab = pocketMaterials[44, 4]

pocketMaterials.Brick = pocketMaterials[45, 0]
pocketMaterials.TNT = pocketMaterials[46, 0]
pocketMaterials.Bookshelf = pocketMaterials[47, 0]
pocketMaterials.MossStone = pocketMaterials[48, 0]
pocketMaterials.Obsidian = pocketMaterials[49, 0]

pocketMaterials.Torch = pocketMaterials[50, 0]
pocketMaterials.Fire = pocketMaterials[51, 0]
pocketMaterials.MonsterSpawner = pocketMaterials[52, 0]
pocketMaterials.WoodenStairs = pocketMaterials[53, 0]
pocketMaterials.Chest = pocketMaterials[54, 0]
pocketMaterials.RedstoneWire = pocketMaterials[55, 0]
pocketMaterials.DiamondOre = pocketMaterials[56, 0]
pocketMaterials.BlockofDiamond = pocketMaterials[57, 0]
pocketMaterials.CraftingTable = pocketMaterials[58, 0]
pocketMaterials.Crops = pocketMaterials[59, 0]
pocketMaterials.Farmland = pocketMaterials[60, 0]
pocketMaterials.Furnace = pocketMaterials[61, 0]
pocketMaterials.LitFurnace = pocketMaterials[62, 0]
pocketMaterials.Sign = pocketMaterials[63,0]
pocketMaterials.WoodenDoor = pocketMaterials[64, 0]
pocketMaterials.Ladder = pocketMaterials[65, 0]
pocketMaterials.Rail = pocketMaterials[66, 0]
pocketMaterials.StoneStairs = pocketMaterials[67, 0]
pocketMaterials.WallSign = pocketMaterials[68,0]
pocketMaterials.Lever = pocketMaterials[69,0]
pocketMaterials.StoneFloorPlate = pocketMaterials[70,0]
pocketMaterials.IronDoor = pocketMaterials[71, 0]
pocketMaterials.WoodFloorPlate = pocketMaterials[72,0]
pocketMaterials.RedstoneOre = pocketMaterials[73, 0]
pocketMaterials.RedstoneOreGlowing = pocketMaterials[74, 0]
pocketMaterials.RedstoneTorchOff = pocketMaterials[75, 0]
pocketMaterials.RedstoneTorchOn = pocketMaterials[76, 0]
pocketMaterials.Button = pocketMaterials[77, 0]
pocketMaterials.SnowLayer = pocketMaterials[78, 0]
pocketMaterials.Ice = pocketMaterials[79, 0]

pocketMaterials.Snow = pocketMaterials[80, 0]
pocketMaterials.Cactus = pocketMaterials[81, 0]
pocketMaterials.Clay = pocketMaterials[82, 0]
pocketMaterials.SugarCane = pocketMaterials[83, 0]
pocketMaterials.Fence = pocketMaterials[85, 0]
pocketMaterials.Pumpkin = pocketMaterials[86, 0]
pocketMaterials.Netherrack = pocketMaterials[87, 0]
pocketMaterials.SoulSand = pocketMaterials[88, 0]
pocketMaterials.Glowstone = pocketMaterials[89, 0]
pocketMaterials.NetherPortal = pocketMaterials[90, 0]
pocketMaterials.JackOLantern = pocketMaterials[91, 0]
pocketMaterials.Cake = pocketMaterials[92, 0]
pocketMaterials.InvisibleBedrock = pocketMaterials[95, 0]
pocketMaterials.Trapdoor = pocketMaterials[96, 0]

pocketMaterials.MonsterEgg = pocketMaterials[97, 0]
pocketMaterials.StoneBricks = pocketMaterials[98, 0]
pocketMaterials.BrownMushroom = pocketMaterials[99, 0]
pocketMaterials.RedMushroom = pocketMaterials[100, 0]
pocketMaterials.IronBars = pocketMaterials[101, 0]
pocketMaterials.GlassPane = pocketMaterials[102, 0]
pocketMaterials.Watermelon = pocketMaterials[103, 0]
pocketMaterials.PumpkinStem = pocketMaterials[104, 0]
pocketMaterials.MelonStem = pocketMaterials[105, 0]
pocketMaterials.Vines = pocketMaterials[106, 0]
pocketMaterials.FenceGate = pocketMaterials[107, 0]
pocketMaterials.BrickStairs = pocketMaterials[108, 0]
pocketMaterials.StoneBrickStairs = pocketMaterials[109, 0]
pocketMaterials.Mycelium = pocketMaterials[110, 0]
pocketMaterials.Lilypad = pocketMaterials[111, 0]

pocketMaterials.NetherBrick = pocketMaterials[112, 0]
pocketMaterials.NetherBrickFence = pocketMaterials[113, 0]
pocketMaterials.NetherBrickStairs = pocketMaterials[114, 0]
pocketMaterials.NetherWart = pocketMaterials[115, 0]

pocketMaterials.EnchantmentTable = pocketMaterials[116, 0]
pocketMaterials.BrewingStand = pocketMaterials[117, 0]
pocketMaterials.EndPortalFrame = pocketMaterials[120, 0]
pocketMaterials.EndStone = pocketMaterials[121, 0]
pocketMaterials.RedstoneLampoff = pocketMaterials[122, 0]
pocketMaterials.RedstoneLampon = pocketMaterials[123, 0]
pocketMaterials.ActivatorRail = pocketMaterials[126, 0]
pocketMaterials.Cocoa = pocketMaterials[127, 0]
pocketMaterials.SandstoneStairs = pocketMaterials[128, 0]
pocketMaterials.EmeraldOre = pocketMaterials[129, 0]
pocketMaterials.TripwireHook = pocketMaterials[131, 0]
pocketMaterials.Tripwire = pocketMaterials[132, 0]
pocketMaterials.BlockOfEmerald = pocketMaterials[133, 0]

pocketMaterials.SpruceWoodStairs = pocketMaterials[134, 0]
pocketMaterials.BirchWoodStairs = pocketMaterials[135, 0]
pocketMaterials.JungleWoodStairs = pocketMaterials[136, 0]

pocketMaterials.CobblestoneWall = pocketMaterials[139, 0]
pocketMaterials.FlowerPot = pocketMaterials[140, 0]
pocketMaterials.Carrots = pocketMaterials[141, 0]
pocketMaterials.Potato = pocketMaterials[142, 0]
pocketMaterials.WoodenButton = pocketMaterials[143, 0]
pocketMaterials.MobHead = pocketMaterials[144, 0]
pocketMaterials.Anvil = pocketMaterials[145, 0]
pocketMaterials.TrappedChest = pocketMaterials[146, 0]
pocketMaterials.WeightedPressurePlateLight = pocketMaterials[147, 0]
pocketMaterials.WeightedPressurePlateHeavy = pocketMaterials[148, 0]
pocketMaterials.DaylightSensor = pocketMaterials[151, 0]
pocketMaterials.BlockOfRedstone = pocketMaterials[152, 0]
pocketMaterials.NetherQuartzOre = pocketMaterials[153, 0]
pocketMaterials.BlockOfQuartz = pocketMaterials[155, 0]
pocketMaterials.DoubleWoodenSlab = pocketMaterials[157, 0]
pocketMaterials.WoodenSlab = pocketMaterials[158, 0]
pocketMaterials.StainedClay = pocketMaterials[159, 0]
pocketMaterials.AcaciaLeaves = pocketMaterials[161, 0]
pocketMaterials.AcaciaWood = pocketMaterials[162, 0]
pocketMaterials.AcaciaWoodStairs = pocketMaterials[163, 0]
pocketMaterials.DarkOakWoodStairs = pocketMaterials[164, 0]
pocketMaterials.IronTrapdoor = pocketMaterials[167, 0]
pocketMaterials.HayBale = pocketMaterials[170, 0]
pocketMaterials.Carpet = pocketMaterials[171, 0]
pocketMaterials.HardenedClay = pocketMaterials[172, 0]
pocketMaterials.BlockOfCoal = pocketMaterials[173, 0]
pocketMaterials.PackedIce = pocketMaterials[174, 0]
pocketMaterials.Sunflower = pocketMaterials[175, 0]
pocketMaterials.DaylightSensorOn = pocketMaterials[178, 0]

pocketMaterials.SpruceFenceGate = pocketMaterials[183, 0]
pocketMaterials.BirchFenceGate = pocketMaterials[184, 0]
pocketMaterials.JungleFenceGate = pocketMaterials[185, 0]
pocketMaterials.DarkOakFenceGate = pocketMaterials[186, 0]
pocketMaterials.AcaciaFenceGate = pocketMaterials[187, 0]
pocketMaterials.GrassPath = pocketMaterials[198, 0]
pocketMaterials.ItemFrame = pocketMaterials[199, 0]

pocketMaterials.Podzol = pocketMaterials[243, 0]
pocketMaterials.Beetroot = pocketMaterials[244, 0]
pocketMaterials.StoneCutter = pocketMaterials[245, 0]
pocketMaterials.GlowingObsidian = pocketMaterials[246, 0]
pocketMaterials.NetherReactor = pocketMaterials[247, 0]
pocketMaterials.NetherReactorUsed = pocketMaterials[247, 1]
pocketMaterials.UpdateGameBlock1 = pocketMaterials[248, 0]
pocketMaterials.UpdateGameBlock2 = pocketMaterials[249, 0]
pocketMaterials.info_reserved6 = pocketMaterials[255, 0]

# pocketMaterials.RedstoneRepeaterOff = alphaMaterials[93, 0] 
# pocketMaterials.RedstoneRepeaterOn = alphaMaterials[94, 0]

def printStaticDefs(name, file_name=None):
    # printStaticDefs('alphaMaterials')
    # file_name: file to write the output to
    mats = eval(name)
    msg = "MCEdit static definitions for '%s'\n\n"%name
    mats_ids = []
    for b in sorted(mats.allBlocks):
        msg += "{name}.{0} = {name}[{1},{2}]\n".format(
            b.name.replace(" ", "").replace("(", "").replace(")", ""),
            b.ID, b.blockData,
            name=name,
        )
        if b.ID not in mats_ids:
            mats_ids.append(b.ID)
    print msg
    if file_name:
        msg += "\nNumber of materials: %s\n%s"%(len(mats_ids), mats_ids)
        id_min = min(mats_ids)
        id_max = max(mats_ids)
        msg += "\n\nLowest ID: %s\nHighest ID: %s\n"%(id_min, id_max)
        missing_ids = []
        for i in range(id_min, id_max + 1):
            if i not in mats_ids:
                missing_ids.append(i)
        if missing_ids:
                msg += "\nIDs not in the list:\n%s\n(%s IDs)\n"%(missing_ids, len(missing_ids))
        open(file_name, 'w').write(msg)
        print "Written to '%s'"%file_name


_indices = rollaxis(indices((id_limit, 16)), 0, 3)


def _filterTable(filters, unavailable, default=(0, 0)):
    # a filter table is a id_limit table of (ID, data) pairs.
    table = zeros((id_limit, 16, 2), dtype='uint8')
    table[:] = _indices
    for u in unavailable:
        try:
            if u[1] == 0:
                u = u[0]
        except TypeError:
            pass
        table[u] = default
    for f, t in filters:
        try:
            if f[1] == 0:
                f = f[0]
        except TypeError:
            pass
        table[f] = t
    return table


nullConversion = lambda b, d: (b, d)


def filterConversion(table):
    def convert(blocks, data):
        if data is None:
            data = 0
        t = table[blocks, data]
        return t[..., 0], t[..., 1]

    return convert


def guessFilterTable(matsFrom, matsTo):
    """ Returns a pair (filters, unavailable)
    filters is a list of (from, to) pairs;  from and to are (ID, data) pairs
    unavailable is a list of (ID, data) pairs in matsFrom not found in matsTo.

    Searches the 'name' and 'aka' fields to find matches.
    """
    filters = []
    unavailable = []
    toByName = dict(((b.name, b) for b in sorted(matsTo.allBlocks, reverse=True)))
    for fromBlock in matsFrom.allBlocks:
        block = toByName.get(fromBlock.name)
        if block is None:
            for b in matsTo.allBlocks:
                if b.name.startswith(fromBlock.name):
                    block = b
                    break
        if block is None:
            for b in matsTo.allBlocks:
                if fromBlock.name in b.name:
                    block = b
                    break
        if block is None:
            for b in matsTo.allBlocks:
                if fromBlock.name in b.aka or fromBlock.name in b.search:
                    block = b
                    break
        if block is None:
            if "Indigo Wool" == fromBlock.name:
                block = toByName.get("Purple Wool")
            elif "Violet Wool" == fromBlock.name:
                block = toByName.get("Purple Wool")

        if block:
            if block != fromBlock:
                filters.append(((fromBlock.ID, fromBlock.blockData), (block.ID, block.blockData)))
        else:
            unavailable.append((fromBlock.ID, fromBlock.blockData))

    return filters, unavailable


allMaterials = (alphaMaterials, classicMaterials, pocketMaterials, indevMaterials)

_conversionFuncs = {}


def conversionFunc(destMats, sourceMats):
    if destMats is sourceMats:
        return nullConversion
    func = _conversionFuncs.get((destMats, sourceMats))
    if func:
        return func

    filters, unavailable = guessFilterTable(sourceMats, destMats)
    log.debug("")
    log.debug("%s %s %s", sourceMats.name, "=>", destMats.name)
    for a, b in [(sourceMats.blockWithID(*a), destMats.blockWithID(*b)) for a, b in filters]:
        log.debug("{0:20}: \"{1}\"".format('"' + a.name + '"', b.name))

    log.debug("")
    log.debug("Missing blocks: %s", [sourceMats.blockWithID(*a).name for a in unavailable])

    table = _filterTable(filters, unavailable, (35, 0))
    func = filterConversion(table)
    _conversionFuncs[(destMats, sourceMats)] = func
    return func


def convertBlocks(destMats, sourceMats, blocks, blockData):
    if sourceMats == destMats:
        return blocks, blockData

    return conversionFunc(destMats, sourceMats)(blocks, blockData)


namedMaterials = dict((i.name, i) for i in allMaterials)

block_map = BlockstateAPI.material_map[alphaMaterials].block_map
blockstates = BlockstateAPI.material_map[alphaMaterials].blockstates
idToBlockstate = BlockstateAPI.material_map[alphaMaterials].idToBlockstate
blockstateToID = BlockstateAPI.material_map[alphaMaterials].blockstateToID
stringifyBlockstate = BlockstateAPI.material_map[alphaMaterials].stringifyBlockstate
deStringifyBlockstate = BlockstateAPI.material_map[alphaMaterials].deStringifyBlockstate

for mat in allMaterials:
    if mat not in BlockstateAPI.material_map:
        continue
    for block in mat.allBlocks:
        if block == mat.Air:
            continue
        setattr(block, "Blockstate", BlockstateAPI.material_map[mat].idToBlockstate(block.ID, block.blockData))

__all__ = "indevMaterials, pocketMaterials, alphaMaterials, classicMaterials, namedMaterials, MCMaterials, BlockStateAPI".split(", ")


if '--dump-mats' in os.sys.argv:
    os.sys.argv.remove('--dump-mats')
    for n in ("indevMaterials", "pocketMaterials", "alphaMaterials", "classicMaterials"):
        printStaticDefs(n, "%s.mats"%n.split('M')[0])
        
if '--find-blockstates' in os.sys.argv:
    pe_blockstates = {'minecraft': {}}
    passed = []
    failed = []
    for block in pocketMaterials:
        ID = block.ID
        DATA = block.blockData
        pc_block = alphaMaterials.get((ID, DATA))
        if pc_block and pc_block.stringID == block.stringID:
            #print block
            passed.append(block)
        else:
            failed.append(block)
    print '{} failed block check'.format(len(failed))
    for block in failed:
        print '!{}!'.format(block)
    for block in passed:
        if block.stringID not in pe_blockstates["minecraft"]:
            pe_blockstates["minecraft"][block.stringID] = {}
            pe_blockstates["minecraft"][block.stringID]["id"] = block.ID
            pe_blockstates["minecraft"][block.stringID]["properties"] = []
        blockstate = idToBlockstate(block.ID, block.blockData)
        state = {"<data>": block.blockData}
        for (key, value) in blockstate[1].iteritems():
            state[key] = value
        pe_blockstates["minecraft"][block.stringID]['properties'].append(state)
    #with open('pe_blockstates_test.json', 'wb') as out:
    #    json.dump(pe_blockstates, out, indent=4, separators=(',', ': '))
