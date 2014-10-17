'''
Created on Jul 23, 2011

@author: Rio
'''
from math import isnan

import nbt
from copy import deepcopy

__all__ = ["Entity", "TileEntity", "TileTick"]


class TileEntity(object):
    baseStructures = {
        "Furnace": (
            ("BurnTime", nbt.TAG_Short),
            ("CookTime", nbt.TAG_Short),
            ("Items", nbt.TAG_List),
        ),
        "Sign": (
            ("Items", nbt.TAG_List),
        ),
        "MobSpawner": (
            ("Items", nbt.TAG_List),
        ),
        "Chest": (
            ("Items", nbt.TAG_List),
        ),
        "Music": (
            ("note", nbt.TAG_Byte),
        ),
        "Trap": (
            ("Items", nbt.TAG_List),
        ),
        "RecordPlayer": (
            ("Record", nbt.TAG_Int),
        ),
        "Piston": (
            ("blockId", nbt.TAG_Int),
            ("blockData", nbt.TAG_Int),
            ("facing", nbt.TAG_Int),
            ("progress", nbt.TAG_Float),
            ("extending", nbt.TAG_Byte),
        ),
        "Cauldron": (
            ("Items", nbt.TAG_List),
            ("BrewTime", nbt.TAG_Int),
        ),
    }

    knownIDs = baseStructures.keys()
    maxItems = {
        "Furnace": 3,
        "Chest": 27,
        "Trap": 9,
        "Cauldron": 4,
    }
    slotNames = {
        "Furnace": {
            0: "Raw",
            1: "Fuel",
            2: "Product"
        },
        "Cauldron": {
            0: "Potion",
            1: "Potion",
            2: "Potion",
            3: "Reagent",
        }
    }

    @classmethod
    def Create(cls, tileEntityID, **kw):
        tileEntityTag = nbt.TAG_Compound()
        tileEntityTag["id"] = nbt.TAG_String(tileEntityID)
        base = cls.baseStructures.get(tileEntityID, None)
        if base:
            for (name, tag) in base:
                tileEntityTag[name] = tag()

        cls.setpos(tileEntityTag, (0, 0, 0))
        return tileEntityTag

    @classmethod
    def pos(cls, tag):
        return [tag[a].value for a in 'xyz']

    @classmethod
    def setpos(cls, tag, pos):
        for a, p in zip('xyz', pos):
            tag[a] = nbt.TAG_Int(p)
                                   

    @classmethod
    def copyWithOffset(cls, tileEntity, copyOffset, staticCommands, first):
        #You'll need to use this function twice
        #The first time with first equals to True
        #The second time with first equals to False
        eTag = deepcopy(tileEntity)
        eTag['x'] = nbt.TAG_Int(tileEntity['x'].value + copyOffset[0])
        eTag['y'] = nbt.TAG_Int(tileEntity['y'].value + copyOffset[1])
        eTag['z'] = nbt.TAG_Int(tileEntity['z'].value + copyOffset[2])
        if eTag['id'].value == "Control":
            command = eTag['Command'].value
            execute = False
            Slash = False
            if command[0] == "/":
                command = command.replace("/", "", 1)
                Slash = True
                    
            def num(x):
                try:
                    return int(x)
                except ValueError:
                    return float(x)
                
            def coordX(x):
                if first == True:
                    x = str(num(x)) + '!' + str(num(x) + copyOffset[0])
                elif staticCommands == True:
                    x = x[x.index("!") + 1:]
                    x = str(num(x) + copyOffset[0])
                else:
                    x = x[:x.index("!")]    
                return x
                    
            def coordY(y):
                if first == True:
                    y = str(num(y)) + '!' + str(num(y) + copyOffset[1]) 
                elif staticCommands == True:
                    y = y[y.index("!") + 1:]
                    y = str(num(y) + copyOffset[1])
                else:
                    y = y[:y.index("!")]    
                return y
                    
            def coordZ(z):
                if first == True:
                    z = str(num(z)) + '!' + str(num(z) + copyOffset[2])   
                elif staticCommands == True:
                    z = z[z.index("!") + 1:]
                    z = str(num(z) + copyOffset[2])
                else:
                    z = z[:z.index("!")]    
                return z       
                        
            def coords(x, y, z):
                if x[0] != "~":
                    x = coordX(x)
                if y[0] != "~":
                    y = coordY(y)
                if z[0] != "~":
                    z = coordZ(z)
                return x, y, z
                
            def selectorCoords(selector):
                char_num = 0
                x = ""
                y = ""
                z = ""
                new_selector = ""
                dont_copy = 0
                for char in selector:
                    if dont_copy != 0:
                        dont_copy -= 1
                    else:
                        if char != 'x' and char != 'y' and char != 'z':
                            new_selector += char
                            if char == '[' or char == ',':
                                letter = False
                            else:
                                letter = True
                        elif char == 'x' and letter == False:
                            new_selector += selector[char_num:char_num + 2]
                            char_x = char_num + 2
                            end_char_x = selector.find(',', char_num + 3, len(selector)-1)
                            if end_char_x == -1:
                                end_char_x = len(selector) - 1
                            x = selector[char_x:end_char_x]
                            dont_copy = len(x) + 1
                            x = coordX(x)
                            new_selector += x
                        
                        elif char == 'y' and letter == False:
                            new_selector += selector[char_num:char_num + 2]
                            char_y = char_num + 2
                            end_char_y = selector.find(',', char_num + 3, len(selector)-1)
                            if end_char_y == -1:
                                end_char_y = len(selector) - 1
                            y = selector[char_y:end_char_y]
                            dont_copy = len(y) + 1
                            y = coordY(y)
                            new_selector += y
                        elif char == 'z' and letter == False:
                            new_selector += selector[char_num:char_num + 2]
                            char_z = char_num + 2
                            end_char_z = selector.find(',', char_num + 3, len(selector)-1)
                            if end_char_z == -1:
                                end_char_z = len(selector) - 1
                            z = selector[char_z:end_char_z]
                            dont_copy = len(z) + 1
                            z = coordZ(z)
                            new_selector += z
                    char_num += 1  
                return new_selector    
                              

            # Adjust command coordinates.
            words = command.split(' ')
            
            i = 0
            for word in words:
                if word[0] == '@':
                    words[i] = selectorCoords(word)
                i += 1    
                
            if command.startswith('execute'):
                stillExecuting = True
                execute = True
                saving_command = ""
                while stillExecuting == True:
                    if Slash == True:
                        saving_command += '/'
                    x, y, z = words[2:5]
                    words[2:5] = coords(x, y, z)
                    if words[5] == 'detect':
                        x, y, z = words[6:9]
                        words[6:9] = coords(x, y, z)
                        saving_command += ' '.join(words[:9])
                        words = words[9:]
                    else:    
                        saving_command += ' '.join(words[:5])
                        words = words[5:]        
                    command = ' '.join(words)
                    saving_command += ' '
                    Slash = False
                    if command[0] == "/":
                        command = command.replace("/", "", 1)
                        Slash = True
                    words = command.split(' ')    
                    if not command.startswith('execute'):
                        stillExecuting = False        
            
            if (command.startswith('tp') and len(words) == 5) or command.startswith('particle') or command.startswith('replaceitem block') or (command.startswith('spawnpoint') and len(words) == 5) or command.startswith('stats block') or (command.startswith('summon') and len(words) >= 5):
                x, y, z = words[2:5]
                words[2:5] = coords(x, y, z)
            elif command.startswith('blockdata') or command.startswith('setblock') or (command.startswith('setworldspawn') and len(words) == 4):
                x, y, z = words[1:4]
                words[1:4] = coords(x, y, z)
            elif command.startswith('playsound') and len(words) >= 6:
                x, y, z = words[3:6]
                words[3:6] = coords(x, y, z)   
            elif command.startswith('clone'):
                x1, y1, z1, x2, y2, z2, x, y, z = words[1:10]
                x1, y1, z1 = coords(x1, y1, z1)
                x2, y2, z2 = coords(x2, y2, z2)
                x, y, z = coords(x, y, z)
                    
                words[1:10] = x1, y1, z1, x2, y2, z2, x, y, z
            elif command.startswith('fill'):
                x1, y1, z1, x2, y2, z2 = words[1:7]
                x1, y1, z1 = coords(x1, y1, z1)
                x2, y2, z2 = coords(x2, y2, z2)
                        
                words[1:7] = x1, y1, z1, x2, y2, z2
            elif command.startswith('spreadplayers'):
                x, z = words[1:3]
                if x[0] != "~":
                    x = coordX(x)
                if z[0] != "~":
                    z = coordZ(z)
                
                words[1:3] = x, z
            elif command.startswith('worldborder center') and len(words) == 4:
                x, z = words[2:4]
                if x[0] != "~":
                    x = coordX(x)
                if z[0] != "~":
                    z = coordZ(z)
                        
                words[2:4] = x, z                       
            if Slash == True:
                command = '/'
            else:
                command = ""
            command += ' '.join(words)
                  
            if execute == True:
                command = saving_command + command
            eTag['Command'].value = command    

        return eTag


class Entity(object):
    monsters = ["Creeper",
                "Skeleton",
                "Spider",
                "CaveSpider",
                "Giant",
                "Zombie",
                "Slime",
                "PigZombie",
                "Ghast",
                "Pig",
                "Sheep",
                "Cow",
                "Chicken",
                "Squid",
                "Wolf",
                "Monster",
                "Enderman",
                "Silverfish",
                "Blaze",
                "Villager",
                "LavaSlime",
                "WitherBoss",
                "Witch",
                "Endermite",
                "Guardian",
                "Rabbit",
                "Bat",
                "MushroomCow",
                "SnowMan",
                "Ozelot",
                "VillagerGolem",
                "EntityHorse"                
    ]
    projectiles = ["Arrow",
                   "Snowball",
                   "Egg",
                   "Fireball",
                   "SmallFireball",
                   "ThrownEnderpearl",
                   "EyeOfEnderSignal",
                   "ThrownPotion",
                   "ThrownExpBottle",
                   "WitherSkull",
                   "FireworksRocketEntity"
    ]

    items = ["Item",
             "XPOrb",
             "Painting",
             "EnderCrystal",
             "ItemFrame",
             "WitherSkull",
    ]
    vehicles = ["MinecartRidable",
                "MinecartChest",
                "MinecartFurnace",
                "MinecartTNT"
                "MinecartHopper"
                "MinecartSpawner"
                "MinecartCommandBlock"
                "Boat",
                ]
    tiles = ["PrimedTnt", "FallingSand"]

    @classmethod
    def Create(cls, entityID, **kw):
        entityTag = nbt.TAG_Compound()
        entityTag["id"] = nbt.TAG_String(entityID)
        Entity.setpos(entityTag, (0, 0, 0))
        return entityTag

    @classmethod
    def pos(cls, tag):
        if "Pos" not in tag:
            raise InvalidEntity(tag)
        values = [a.value for a in tag["Pos"]]

        if isnan(values[0]) and 'xTile' in tag:
            values[0] = tag['xTile'].value
        if isnan(values[1]) and 'yTile' in tag:
            values[1] = tag['yTile'].value
        if isnan(values[2]) and 'zTile' in tag:
            values[2] = tag['zTile'].value

        return values

    @classmethod
    def setpos(cls, tag, pos):
        tag["Pos"] = nbt.TAG_List([nbt.TAG_Double(p) for p in pos])

    @classmethod
    def copyWithOffset(cls, entity, copyOffset):
        eTag = deepcopy(entity)

        positionTags = map(lambda p, co: nbt.TAG_Double(p.value + co), eTag["Pos"], copyOffset)
        eTag["Pos"] = nbt.TAG_List(positionTags)

        if eTag["id"].value in ("Painting", "ItemFrame"):
            eTag["TileX"].value += copyOffset[0]
            eTag["TileY"].value += copyOffset[1]
            eTag["TileZ"].value += copyOffset[2]

        if "Riding" in eTag:
            eTag["Riding"] = copyWithOffset(cls, eTag["Riding"], copyOffset)
        return eTag

class TileTick(object):
    @classmethod
    def pos(cls, tag):
        return [tag[a].value for a in 'xyz']


class InvalidEntity(ValueError):
    pass


class InvalidTileEntity(ValueError):
    pass
