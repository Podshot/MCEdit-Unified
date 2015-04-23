from logging import getLogger
from numpy import zeros, rollaxis, indices
import traceback
from os.path import join
from collections import defaultdict
from pprint import pformat

import os

NOTEX = (0x1F0, 0x1F0)

import yaml

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


class MCMaterials(object):
    defaultColor = (0xc9, 0x77, 0xf0, 0xff)
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

        self.Air = self.addBlock(0,
                                 name="Air",
                                 texture=(0x0, 0x150),
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
            raise KeyError("No blocks named: " + key)
        if isinstance(key, (tuple, list)):
            id, blockData = key
            return self.blockWithID(id, blockData)
        return self.blockWithID(key)

    def blocksMatching(self, name):
        toReturn = []
        name = name.lower()
        spiltNames = name.split(" ")
        amount = len(spiltNames)
        for v in self.allBlocks:
            nameParts = v.name.lower().split(" ")
            for anotherName in v.aka.lower().split(" "):
                nameParts.append(anotherName)
            for anotherName in v.search.lower().split(" "):
                nameParts.append(anotherName)
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

    def blockWithID(self, id, data=0):
        if (id, data) in self.blocksByID:
            return self.blocksByID[id, data]
        else:
            bl = Block(self, id, blockData=data)
            return bl

    def addYamlBlocksFromFile(self, filename):
        try:
            import pkg_resources

            f = pkg_resources.resource_stream(__name__, filename)
        except (ImportError, IOError), e:
            print "Cannot get resource_stream for ", filename, e
            root = os.environ.get("PYMCLEVEL_YAML_ROOT", "pymclevel")  # fall back to cwd as last resort
            path = join(root, filename)

            log.exception("Failed to read %s using pkg_resources. Trying %s instead." % (filename, path))

            f = file(path)
        try:
            log.info(u"Loading block info from %s", f)
            try:
                log.debug("Trying YAML CLoader")
                blockyaml = yaml.load(f, Loader=yaml.CLoader)
            except:
                log.debug("CLoader not preset, falling back to Python YAML")
                blockyaml = yaml.load(f)
            self.addYamlBlocks(blockyaml)

        except Exception, e:
            log.warn(u"Exception while loading block info from %s: %s", f, e)
            traceback.print_exc()

    def addYamlBlocks(self, blockyaml):
        self.yamlDatas.append(blockyaml)
        for block in blockyaml['blocks']:
            try:
                self.addYamlBlock(block)
            except Exception, e:
                log.warn(u"Exception while parsing block: %s", e)
                traceback.print_exc()
                log.warn(u"Block definition: \n%s", pformat(block))

    def addYamlBlock(self, kw):
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

            for data, dir in tex_direction_data.items():
                for _i in range(texDirMap.get(dir, 0)):
                    rot90cw()
                self.blockTextures[blockID][data] = texture

    def addBlock(self, blockID, blockData=0, **kw):
        name = kw.pop('name', self.names[blockID][blockData])
        stringName = kw.pop('idStr', '')

        self.lightEmission[blockID] = kw.pop('brightness', self.defaultBrightness)
        self.lightAbsorption[blockID] = kw.pop('opacity', self.defaultOpacity)
        self.aka[blockID][blockData] = kw.pop('aka', "")
        self.search[blockID][blockData] = kw.pop('search', "")
        type = kw.pop('type', 'NORMAL')

        color = kw.pop('mapcolor', self.flatColors[blockID, blockData])
        self.flatColors[blockID, blockData] = (tuple(color) + (255,))[:4]

        texture = kw.pop('texture', None)

        if texture:
            self.blockTextures[blockID, blockData] = texture

        self.names[blockID][blockData] = name
        if blockData is 0:
            self.type[blockID] = [type] * 16
        else:
            self.type[blockID][blockData] = type

        block = Block(self, blockID, blockData, stringName)

        self.allBlocks.append(block)
        self.blocksByType[type].append(block)

        self.blocksByID[blockID, blockData] = block

        return block


alphaMaterials = MCMaterials(defaultName="Future Block!")
alphaMaterials.name = "Alpha"
alphaMaterials.addYamlBlocksFromFile("minecraft.yaml")

classicMaterials = MCMaterials(defaultName="Not present in Classic")
classicMaterials.name = "Classic"
classicMaterials.addYamlBlocksFromFile("classic.yaml")

indevMaterials = MCMaterials(defaultName="Not present in Indev")
indevMaterials.name = "Indev"
indevMaterials.addYamlBlocksFromFile("indev.yaml")

pocketMaterials = MCMaterials()
pocketMaterials.name = "Pocket"
pocketMaterials.addYamlBlocksFromFile("pocket.yaml")

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
pocketMaterials.Leaves = pocketMaterials[18, 0]
pocketMaterials.Glass = pocketMaterials[20, 0]

pocketMaterials.LapisLazuliOre = pocketMaterials[21, 0]
pocketMaterials.LapisLazuliBlock = pocketMaterials[22, 0]
pocketMaterials.Sandstone = pocketMaterials[24, 0]
pocketMaterials.Bed = pocketMaterials[26, 0]
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
pocketMaterials.WoodenStairs = pocketMaterials[53, 0]
pocketMaterials.Chest = pocketMaterials[54, 0]
pocketMaterials.DiamondOre = pocketMaterials[56, 0]
pocketMaterials.BlockofDiamond = pocketMaterials[57, 0]
pocketMaterials.CraftingTable = pocketMaterials[58, 0]
pocketMaterials.Crops = pocketMaterials[59, 0]
pocketMaterials.Farmland = pocketMaterials[60, 0]
pocketMaterials.Furnace = pocketMaterials[61, 0]
pocketMaterials.LitFurnace = pocketMaterials[62, 0]
pocketMaterials.WoodenDoor = pocketMaterials[64, 0]
pocketMaterials.Ladder = pocketMaterials[65, 0]
pocketMaterials.StoneStairs = pocketMaterials[67, 0]
pocketMaterials.IronDoor = pocketMaterials[71, 0]
pocketMaterials.RedstoneOre = pocketMaterials[73, 0]
pocketMaterials.RedstoneOreGlowing = pocketMaterials[74, 0]
pocketMaterials.SnowLayer = pocketMaterials[78, 0]
pocketMaterials.Ice = pocketMaterials[79, 0]

pocketMaterials.Snow = pocketMaterials[80, 0]
pocketMaterials.Cactus = pocketMaterials[81, 0]
pocketMaterials.Clay = pocketMaterials[82, 0]
pocketMaterials.SugarCane = pocketMaterials[83, 0]
pocketMaterials.Fence = pocketMaterials[85, 0]
pocketMaterials.Glowstone = pocketMaterials[89, 0]
pocketMaterials.InvisibleBedrock = pocketMaterials[95, 0]
pocketMaterials.Trapdoor = pocketMaterials[96, 0]

pocketMaterials.StoneBricks = pocketMaterials[98, 0]
pocketMaterials.GlassPane = pocketMaterials[102, 0]
pocketMaterials.Watermelon = pocketMaterials[103, 0]
pocketMaterials.MelonStem = pocketMaterials[105, 0]
pocketMaterials.FenceGate = pocketMaterials[107, 0]
pocketMaterials.BrickStairs = pocketMaterials[108, 0]

pocketMaterials.GlowingObsidian = pocketMaterials[246, 0]
pocketMaterials.NetherReactor = pocketMaterials[247, 0]
pocketMaterials.NetherReactorUsed = pocketMaterials[247, 1]


def printStaticDefs(name):
    # printStaticDefs('alphaMaterials')
    mats = eval(name)
    for b in sorted(mats.allBlocks):
        print "{name}.{0} = {name}[{1},{2}]".format(
            b.name.replace(" ", "").replace("(", "").replace(")", ""),
            b.ID, b.blockData,
            name=name,
        )


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

block_map = {}
for b in alphaMaterials:
    if b.ID == 0:
        b.stringID = "air"
    block_map[b.ID] = "minecraft:"+b.stringID

'''
block_map_old = {
    0: "minecraft:air", 1: "minecraft:stone", 2: "minecraft:grass", 3: "minecraft:dirt", 4: "minecraft:cobblestone",
    5: "minecraft:planks", 6: "minecraft:sapling",
    7: "minecraft:bedrock", 8: "minecraft:flowing_water", 9: "minecraft:water", 10: "minecraft:flowing_lava",
    11: "minecraft:lava", 12: "minecraft:sand", 13: "minecraft:gravel",
    14: "minecraft:gold_ore", 15: "minecraft:iron_ore", 16: "minecraft:coal_ore", 17: "minecraft:log",
    18: "minecraft:leaves", 19: "minecraft:sponge", 20: "minecraft:glass",
    21: "minecraft:lapis_ore", 22: "minecraft:lapis_block", 23: "minecraft:dispenser", 24: "minecraft:sandstone",
    25: "minecraft:noteblock", 26: "minecraft:bed",
    27: "minecraft:golden_rail", 28: "minecraft:detector_rail", 29: "minecraft:sticky_piston", 30: "minecraft:web",
    31: "minecraft:tallgrass", 32: "minecraft:deadbush",
    33: "minecraft:piston", 34: "minecraft:piston_head", 35: "minecraft:wool", 36: "minecraft:piston_extension",
    37: "minecraft:yellow_flower", 38: "minecraft:red_flower",
    39: "minecraft:brown_mushroom", 40: "minecraft:red_mushroom", 41: "minecraft:gold_block",
    42: "minecraft:iron_block", 43: "minecraft:double_stone_slab",
    44: "minecraft:stone_slab", 45: "minecraft:brick_block", 46: "minecraft:tnt", 47: "minecraft:bookshelf",
    48: "minecraft:mossy_cobblestone", 49: "minecraft:obsidian",
    50: "minecraft:torch", 51: "minecraft:fire", 52: "minecraft:mob_spawner", 53: "minecraft:oak_stairs",
    54: "minecraft:chest", 55: "minecraft:redstone_wire",
    56: "minecraft:diamond_ore", 57: "minecraft:diamond_block", 58: "minecraft:crafting_table", 59: "minecraft:wheat",
    60: "minecraft:farmland", 61: "minecraft:furnace",
    62: "minecraft:lit_furnace", 63: "minecraft:standing_sign", 64: "minecraft:wooden_door", 65: "minecraft:ladder",
    66: "minecraft:rail", 67: "minecraft:stone_stairs",
    68: "minecraft:wall_sign", 69: "minecraft:lever", 70: "minecraft:stone_pressure_plate", 71: "minecraft:iron_door",
    72: "minecraft:wooden_pressure_plate",
    73: "minecraft:redstone_ore", 74: "minecraft:lit_redstone_ore", 75: "minecraft:unlit_redstone_torch",
    76: "minecraft:redstone_torch", 77: "minecraft:stone_button",
    78: "minecraft:snow_layer", 79: "minecraft:ice", 80: "minecraft:snow", 81: "minecraft:cactus", 82: "minecraft:clay",
    83: "minecraft:reeds", 84: "minecraft:jukebox",
    85: "minecraft:fence", 86: "minecraft:pumpkin", 87: "minecraft:netherrack", 88: "minecraft:soul_sand",
    89: "minecraft:glowstone", 90: "minecraft:portal",
    91: "minecraft:lit_pumpkin", 92: "minecraft:cake", 93: "minecraft:unpowered_repeater",
    94: "minecraft:powered_repeater",
    95: "minecraft:stained_glass", 96: "minecraft:trapdoor", 97: "minecraft:monster_egg", 98: "minecraft:stonebrick",
    99: "minecraft:brown_mushroom_block", 100: "minecraft:red_mushroom_block", 101: "minecraft:iron_bars",
    102: "minecraft:glass_pane", 103: "minecraft:melon_block",
    104: "minecraft:pumpkin_stem", 105: "minecraft:melon_stem", 106: "minecraft:vine", 107: "minecraft:fence_gate",
    108: "minecraft:brick_stairs", 109: "minecraft:stone_brick_stairs",
    110: "minecraft:mycelium", 111: "minecraft:waterlily", 112: "minecraft:nether_brick",
    113: "minecraft:nether_brick_fence", 114: "minecraft:nether_brick_stairs",
    115: "minecraft:nether_wart", 116: "minecraft:enchanting_table", 117: "minecraft:brewing_stand",
    118: "minecraft:cauldron", 119: "minecraft:end_portal",
    120: "minecraft:end_portal_frame", 121: "minecraft:end_stone", 122: "minecraft:dragon_egg",
    123: "minecraft:redstone_lamp", 124: "minecraft:lit_redstone_lamp",
    125: "minecraft:double_wooden_slab", 126: "minecraft:wooden_slab", 127: "minecraft:cocoa",
    128: "minecraft:sandstone_stairs", 129: "minecraft:emerald_ore",
    130: "minecraft:ender_chest", 131: "minecraft:tripwire_hook", 132: "minecraft:tripwire",
    133: "minecraft:emerald_block", 134: "minecraft:spruce_stairs",
    135: "minecraft:birch_stairs", 136: "minecraft:jungle_stairs", 137: "minecraft:command_block",
    138: "minecraft:beacon", 139: "minecraft:cobblestone_wall",
    140: "minecraft:flower_pot", 141: "minecraft:carrots", 142: "minecraft:potatoes", 143: "minecraft:wooden_button",
    144: "minecraft:skull", 145: "minecraft:anvil",
    146: "minecraft:trapped_chest", 147: "minecraft:light_weighted_pressure_plate",
    148: "minecraft:heavy_weighted_pressure_plate", 149: "minecraft:unpowered_comparator",
    150: "minecraft:powered_comparator", 151: "minecraft:daylight_detector", 152: "minecraft:redstone_block",
    153: "minecraft:quartz_ore", 154: "minecraft:hopper",
    155: "minecraft:quartz_block", 156: "minecraft:quartz_stairs", 157: "minecraft:activator_rail",
    158: "minecraft:dropper", 159: "minecraft:stained_hardened_clay",
    160: "minecraft:stained_glass_pane", 162: "minecraft:log2", 163: "minecraft:acacia_stairs",
    164: "minecraft:dark_oak_stairs", 165: "minecraft:slime", 166: "minecraft:barrier",
    167: "minecraft:iron_trapdoor", 168: "minecraft:prismarine", 169: "minecraft:sea_lantern",
    170: "minecraft:hay_block", 171: "minecraft:carpet", 172: "minecraft:hardened_clay", 173: "minecraft:coal_block",
    174: "minecraft:packed_ice", 175: "minecraft:double_plant",
    176: "minecraft:standing_banner", 177: "minecraft:wall_banner", 178: "minecraft:daylight_detector_inverted",
    179: "minecraft:red_sandstone", 180: "minecraft:red_sandstone_stairs",
    181: "minecraft:double_stone_slab2", 182: "minecraft:stone_slab2", 183: "minecraft:spruce_fence_gate",
    184: "minecraft:birch_fence_gate", 185: "minecraft:jungle_fence_gate",
    161: "minecraft:leaves2", 186: "minecraft:dark_oak_fence_gate", 187: "minecraft:acacia_fence_gate",
    188: "minecraft:spruce_fence", 189: "minecraft:birch_fence", 190: "minecraft:jungle_fence",
    191: "minecraft:dark_oak_fence", 192: "minecraft:acacia_fence", 193: "minecraft:spruce_door",
    194: "minecraft:birch_door", 195: "minecraft:jungle_door", 196: "minecraft:acacia_door",
    197: "minecraft:dark_oak_door"
}
'''

__all__ = "indevMaterials, pocketMaterials, alphaMaterials, classicMaterials, namedMaterials, MCMaterials".split(", ")
