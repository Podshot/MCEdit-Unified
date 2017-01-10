'''
Created on Jul 23, 2011

@author: Rio
'''
from math import isnan

import random
import nbt
from copy import deepcopy
from pymclevel import MCEDIT_DEFS, MCEDIT_IDS

__all__ = ["Entity", "TileEntity", "TileTick"]

UNKNOWN_ENTITY_MASK = 1000


class TileEntity(object):
    baseStructures = {
        "Furnace": (
            ("BurnTime", nbt.TAG_Short),
            ("CookTime", nbt.TAG_Short),
            ("Items", nbt.TAG_List),
        ),
        "Sign": (
            ("Text1", nbt.TAG_String),
            ("Text2", nbt.TAG_String),
            ("Text3", nbt.TAG_String),
            ("Text4", nbt.TAG_String),
        ),
        "MobSpawner": (
            ("EntityId", nbt.TAG_String),
            ("SpawnData", nbt.TAG_Compound),
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
        "Control": (
            ("Command", nbt.TAG_String),
            ("CustomName", nbt.TAG_String),
            ("TrackOutput", nbt.TAG_Byte),
            ("SuccessCount", nbt.TAG_Int)
        ),
        "FlowerPot": (
            ("Item", nbt.TAG_String),
            ("Data", nbt.TAG_Int),
        ),
        "EnchantTable": (
            ("CustomName", nbt.TAG_String),
        ),
        "Dropper": (
            ("Items", nbt.TAG_List),
        ),
        "Dispenser": (
            ("Items", nbt.TAG_List),
        ),
        "Hopper": (
            ("Items", nbt.TAG_List),
        ),
    }

    otherNames = {
        "Furnace": "Furnace",
        "Sign": "Sign",
        "Monster Spawner": "MobSpawner",
        "Chest": "Chest",
        "Note Block": "Music",
        "Trapped Chest": "Chest",
        "Jukebox": "RecordPlayer",
        "Piston": "Piston",
        "Cauldron": "Cauldron",
        "Command Block": "Control",
        "FlowerPot": "FlowerPot",
        "EnchantTable": "EnchantTable",
        "Dropper": "Dropper",
        "Dispenser": "Dispenser",
        "Hopper": "Hopper",
    }

    stringNames = {
        "furnace": "Furnace",
        "lit_furnace": "Furnace",
        "standing_sign": "Sign",
        "wall_sign": "Sign",
        "mob_spawner": "MobSpawner",
        "chest": "Chest",
        "ender_chest": "Chest",
        "noteblock": "Music",
        "trapped_chest": "Chest",
        "jukebox": "RecordPlayer",
        "sticky_piston": "Piston",
        "piston": "Piston",
        "cauldron": "Cauldron",
        "command_block": "Control",
        "repeating_command_block": "Control",
        "chain_command_block": "Control",
        "flower_pot": "FlowerPot",
        "enchanting_table": "EnchantTable",
        "dropper": "Dropper",
        "dispenser": "Dispenser",
        "hopper": "Hopper",
    }

    knownIDs = baseStructures.keys()
    maxItems = {
        "Furnace": 3,
        "Chest": 27,
        "Trap": 9,
        "Cauldron": 4,
        "Dropper": 9,
        "Hopper": 5,
        "Dispenser": 9,
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
    def Create(cls, tileEntityID, pos=(0, 0, 0), **kw):
        tileEntityTag = nbt.TAG_Compound()
        # Refresh the MCEDIT_DEFS and MCEDIT_IDS objects
        from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
        _id = MCEDIT_DEFS.get(tileEntityID, tileEntityID)
        tileEntityTag["id"] = nbt.TAG_String(_id)
        base = cls.baseStructures.get(tileEntityID, None)
        if base:
            for (name, tag) in base:
                tileEntityTag[name] = tag()
                if tileEntityID == "Control":
                    if name == "CustomName":
                        tileEntityTag[name] = nbt.TAG_String("@")
                    elif name == "SuccessCount":
                        tileEntityTag[name] = nbt.TAG_Int(0)
                elif tileEntityID == "MobSpawner":
                    entity = kw.get("entity")
                    if name == "EntityId":
                        tileEntityTag[name] = nbt.TAG_String(MCEDIT_DEFS.get("Pig", "Pig"))
                    if name == "SpawnData":
                        spawn_id = nbt.TAG_String(MCEDIT_DEFS.get("Pig", "Pig"), "id")
                        tileEntityTag["SpawnData"] = tag()
                        if entity:
                            for k, v in entity.iteritems():
                                tileEntityTag["SpawnData"][k] = deepcopy(v)
                        else:
                            tileEntityTag["SpawnData"].add(spawn_id)

        cls.setpos(tileEntityTag, pos)
        return tileEntityTag

    @classmethod
    def pos(cls, tag):
        return [tag[a].value for a in 'xyz']

    @classmethod
    def setpos(cls, tag, pos):
        for a, p in zip('xyz', pos):
            tag[a] = nbt.TAG_Int(p)

    @classmethod
    def copyWithOffset(cls, tileEntity, copyOffset, staticCommands, moveSpawnerPos, first, cancelCommandBlockOffset=False):
        # You'll need to use this function twice
        # The first time with first equals to True
        # The second time with first equals to False
        eTag = deepcopy(tileEntity)
        eTag['x'] = nbt.TAG_Int(tileEntity['x'].value + copyOffset[0])
        eTag['y'] = nbt.TAG_Int(tileEntity['y'].value + copyOffset[1])
        eTag['z'] = nbt.TAG_Int(tileEntity['z'].value + copyOffset[2])

        def num(x):
            try:
                return int(x)
            except ValueError:
                return float(x)

        def coordX(x, argument):
            if first:
                x = str(num(x)) + '!' + str(num(x) + copyOffset[0])
            elif argument and x.find("!") >= 0:
                x = x[x.index("!") + 1:]
                x = str(num(x) + copyOffset[0])
            elif not argument and x.find("!") >= 0:
                x = x[:x.index("!")]
            return x

        def coordY(y, argument):
            if first:
                y = str(num(y)) + '!' + str(num(y) + copyOffset[1])
            elif argument and y.find("!") >= 0:
                y = y[y.index("!") + 1:]
                y = str(num(y) + copyOffset[1])
            elif not argument and y.find("!") >= 0:
                y = y[:y.index("!")]
            return y

        def coordZ(z, argument):
            if first:
                z = str(num(z)) + '!' + str(num(z) + copyOffset[2])
            elif argument and z.find("!") >= 0:
                z = z[z.index("!") + 1:]
                z = str(num(z) + copyOffset[2])
            elif not argument and z.find("!") >= 0:
                z = z[:z.index("!")]
            return z

        def coords(x, y, z, argument):
            if x[0] != "~":
                x = coordX(x, argument)
            if y[0] != "~":
                y = coordY(y, argument)
            if z[0] != "~":
                z = coordZ(z, argument)
            return x, y, z

        if eTag['id'].value == 'MobSpawner' or MCEDIT_IDS.get(eTag['id'].value) == 'DEF_BLOCKS_MOB_SPAWNER':
            mobs = []
            if 'SpawnData' in eTag:
                mob = eTag['SpawnData']
                if mob:
                    mobs.append(mob)
            if 'SpawnPotentials' in eTag:
                potentials = eTag['SpawnPotentials']
                for p in potentials:
                    if 'properties' in p:
                        mobs.extend(p["Properties"])
                    elif 'Entity' in p:
                        mobs.extend(p["Entity"])

            for mob in mobs:
                # Why do we get a unicode object as tag 'mob'?
                if "Pos" in mob and mob != "Pos":
                    if first:
                        pos = Entity.pos(mob)
                        x, y, z = [str(part) for part in pos]
                        x, y, z = coords(x, y, z, moveSpawnerPos)
                        mob['Temp1'] = nbt.TAG_String(x)
                        mob['Temp2'] = nbt.TAG_String(y)
                        mob['Temp3'] = nbt.TAG_String(z)
                    elif 'Temp1' in mob and 'Temp2' in mob and 'Temp3' in mob:
                        x = mob['Temp1']
                        y = mob['Temp2']
                        z = mob['Temp3']
                        del mob['Temp1']
                        del mob['Temp2']
                        del mob['Temp3']
                        parts = []
                        for part in (x, y, z):
                            part = str(part)
                            part = part[13:len(part) - 2]
                            parts.append(part)
                        x, y, z = parts
                        pos = [float(p) for p in coords(x, y, z, moveSpawnerPos)]
                        Entity.setpos(mob, pos)

        if (eTag['id'].value == "Control" or MCEDIT_IDS.get(eTag['id'].value) == 'DEF_BLOCKS_COMMAND_BLOCK') and not cancelCommandBlockOffset:
            command = eTag['Command'].value
            oldCommand = command

            def selectorCoords(selector):
                old_selector = selector
                try:
                    char_num = 0
                    new_selector = ""
                    dont_copy = 0
                    if len(selector) > 4:
                        if '0' <= selector[3] <= '9':
                            new_selector = selector[:3]
                            end_char_x = selector.find(',', 4, len(selector) - 1)
                            if end_char_x == -1:
                                end_char_x = len(selector) - 1
                            x = selector[3:end_char_x]
                            x = coordX(x, staticCommands)
                            new_selector += x + ','

                            end_char_y = selector.find(',', end_char_x + 1, len(selector) - 1)
                            if end_char_y == -1:
                                end_char_y = len(selector) - 1
                            y = selector[end_char_x + 1:end_char_y]
                            y = coordY(y, staticCommands)
                            new_selector += y + ','

                            end_char_z = selector.find(',', end_char_y + 1, len(selector) - 1)
                            if end_char_z == -1:
                                end_char_z = len(selector) - 1
                            z = selector[end_char_y + 1:end_char_z]
                            z = coordZ(z, staticCommands)
                            new_selector += z + ',' + selector[end_char_z + 1:]

                        else:
                            for char in selector:
                                if dont_copy != 0:
                                    dont_copy -= 1
                                else:
                                    if (char != 'x' and char != 'y' and char != 'z') or letter:
                                        new_selector += char
                                        if char == '[' or char == ',':
                                            letter = False
                                        else:
                                            letter = True

                                    elif char == 'x' and not letter:
                                        new_selector += selector[char_num:char_num + 2]
                                        char_x = char_num + 2
                                        end_char_x = selector.find(',', char_num + 3, len(selector) - 1)
                                        if end_char_x == -1:
                                            end_char_x = len(selector) - 1
                                        x = selector[char_x:end_char_x]
                                        dont_copy = len(x) + 1
                                        x = coordX(x, staticCommands)
                                        new_selector += x

                                    elif char == 'y' and not letter:
                                        new_selector += selector[char_num:char_num + 2]
                                        char_y = char_num + 2
                                        end_char_y = selector.find(',', char_num + 3, len(selector) - 1)
                                        if end_char_y == -1:
                                            end_char_y = len(selector) - 1
                                        y = selector[char_y:end_char_y]
                                        dont_copy = len(y) + 1
                                        y = coordY(y, staticCommands)
                                        new_selector += y

                                    elif char == 'z' and not letter:
                                        new_selector += selector[char_num:char_num + 2]
                                        char_z = char_num + 2
                                        end_char_z = selector.find(',', char_num + 3, len(selector) - 1)
                                        if end_char_z == -1:
                                            end_char_z = len(selector) - 1
                                        z = selector[char_z:end_char_z]
                                        dont_copy = len(z) + 1
                                        z = coordZ(z, staticCommands)
                                        new_selector += z
                                char_num += 1
                    else:
                        new_selector = old_selector

                except:
                    new_selector = old_selector
                finally:
                    return new_selector

            try:
                execute = False
                Slash = False
                if command[0] == "/":
                    command = command[1:]
                    Slash = True

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
                    while stillExecuting:
                        if Slash:
                            saving_command += '/'
                        x, y, z = words[2:5]
                        words[2:5] = coords(x, y, z, staticCommands)
                        if words[5] == 'detect':
                            x, y, z = words[6:9]
                            words[6:9] = coords(x, y, z, staticCommands)
                            saving_command += ' '.join(words[:9])
                            words = words[9:]
                        else:
                            saving_command += ' '.join(words[:5])
                            words = words[5:]
                        command = ' '.join(words)
                        saving_command += ' '
                        Slash = False
                        if command[0] == "/":
                            command = command[1:]
                            Slash = True
                        words = command.split(' ')
                        if not command.startswith('execute'):
                            stillExecuting = False

                if (command.startswith('tp') and len(words) == 5) or command.startswith(
                        'particle') or command.startswith('replaceitem block') or (
                            command.startswith('spawnpoint') and len(words) == 5) or command.startswith('stats block') or (
                            command.startswith('summon') and len(words) >= 5):
                    x, y, z = words[2:5]
                    words[2:5] = coords(x, y, z, staticCommands)
                elif command.startswith('blockdata') or command.startswith('setblock') or (
                            command.startswith('setworldspawn') and len(words) == 4):
                    x, y, z = words[1:4]
                    words[1:4] = coords(x, y, z, staticCommands)
                elif command.startswith('playsound') and len(words) >= 6:
                    x, y, z = words[3:6]
                    words[3:6] = coords(x, y, z, staticCommands)
                elif command.startswith('clone'):
                    x1, y1, z1, x2, y2, z2, x, y, z = words[1:10]
                    x1, y1, z1 = coords(x1, y1, z1, staticCommands)
                    x2, y2, z2 = coords(x2, y2, z2, staticCommands)
                    x, y, z = coords(x, y, z, staticCommands)

                    words[1:10] = x1, y1, z1, x2, y2, z2, x, y, z
                elif command.startswith('fill'):
                    x1, y1, z1, x2, y2, z2 = words[1:7]
                    x1, y1, z1 = coords(x1, y1, z1, staticCommands)
                    x2, y2, z2 = coords(x2, y2, z2, staticCommands)

                    words[1:7] = x1, y1, z1, x2, y2, z2
                elif command.startswith('spreadplayers'):
                    x, z = words[1:3]
                    if x[0] != "~":
                        x = coordX(x, staticCommands)
                    if z[0] != "~":
                        z = coordZ(z, staticCommands)

                    words[1:3] = x, z
                elif command.startswith('worldborder center') and len(words) == 4:
                    x, z = words[2:4]
                    if x[0] != "~":
                        x = coordX(x, staticCommands)
                    if z[0] != "~":
                        z = coordZ(z, staticCommands)

                    words[2:4] = x, z
                if Slash:
                    command = '/'
                else:
                    command = ""
                command += ' '.join(words)

                if execute:
                    command = saving_command + command
                eTag['Command'].value = command
            except:
                eTag['Command'].value = oldCommand

        return eTag


class Entity(object):
    entityList = {
        "Item": 1,
        "XPOrb": 2,
        "LeashKnot": 8,
        "Painting": 9,
        "Arrow": 10,
        "Snowball": 11,
        "Fireball": 12,
        "SmallFireball": 13,
        "ThrownEnderpearl": 14,
        "EyeOfEnderSignal": 15,
        "ThrownPotion": 16,
        "ThrownExpBottle": 17,
        "ItemFrame": 18,
        "WitherSkull": 19,
        "PrimedTnt": 20,
        "FallingSand": 21,
        "FireworksRocketEntity": 22,
        "ArmorStand": 30,
        "MinecartCommandBlock": 40,
        "Boat": 41,
        "MinecartRideable": 42,
        "MinecartChest": 43,
        "MinecartFurnace": 44,
        "MinecartTNT": 45,
        "MinecartHopper": 46,
        "MinecartSpawner": 47,
        "Mob": 48,
        "Monster": 49,
        "Creeper": 50,
        "Skeleton": 51,
        "Spider": 52,
        "Giant": 53,
        "Zombie": 54,
        "Slime": 55,
        "Ghast": 56,
        "PigZombie": 57,
        "Enderman": 58,
        "CaveSpider": 59,
        "Silverfish": 60,
        "Blaze": 61,
        "LavaSlime": 62,
        "EnderDragon": 63,
        "WitherBoss": 64,
        "Bat": 65,
        "Witch": 66,
        "Endermite": 67,
        "Guardian": 68,
        "Pig": 90,
        "Sheep": 91,
        "Cow": 92,
        "Chicken": 93,
        "Squid": 94,
        "Wolf": 95,
        "MushroomCow": 96,
        "SnowMan": 97,
        "Ozelot": 98,
        "VillagerGolem": 99,
        "EntityHorse": 100,
        "Rabbit": 101,
        "Villager": 120,
        "EnderCrystal": 200}

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

    maxItems = {
        "MinecartChest": 27,
        "MinecartHopper": 5,
        "EntityHorse": 15
    }

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
        else:
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
    def copyWithOffset(cls, entity, copyOffset, regenerateUUID=False):
        eTag = deepcopy(entity)

        # Need to check the content of the copy to regenerate the possible sub entities UUIDs.
        # A simple fix for the 1.9+ minecarts is proposed.

        positionTags = map(lambda p, co: nbt.TAG_Double(p.value + co), eTag["Pos"], copyOffset)
        eTag["Pos"] = nbt.TAG_List(positionTags)

        # Also match the 'minecraft:XXX' names
#         if eTag["id"].value in ("Painting", "ItemFrame", u'minecraft:painting', u'minecraft:item_frame'):
#             print "#" * 40
#             print eTag
#             eTag["TileX"].value += copyOffset[0]
#             eTag["TileY"].value += copyOffset[1]
#             eTag["TileZ"].value += copyOffset[2]

        # Trying more agnostic way
        if eTag.get('TileX') and eTag.get('TileY') and eTag.get('TileZ'):
            eTag["TileX"].value += copyOffset[0]
            eTag["TileY"].value += copyOffset[1]
            eTag["TileZ"].value += copyOffset[2]

        if "Riding" in eTag:
            eTag["Riding"] = Entity.copyWithOffset(eTag["Riding"], copyOffset)

        # # Fix for 1.9+ minecarts
        if "Passengers" in eTag:
            passengers = nbt.TAG_List()
            for passenger in eTag["Passengers"]:
                passengers.append(Entity.copyWithOffset(passenger, copyOffset, regenerateUUID))
            eTag["Passengers"] = passengers
        # #

        if regenerateUUID:
            # Courtesy of SethBling
            eTag["UUIDMost"] = nbt.TAG_Long((random.getrandbits(47) << 16) | (1 << 12) | random.getrandbits(12))
            eTag["UUIDLeast"] = nbt.TAG_Long(-((7 << 60) | random.getrandbits(60)))
        return eTag

    @classmethod
    def getId(cls, v):
        return cls.entityList.get(v, 'No ID')


class PocketEntity(Entity):
    unknown_entity_top = UNKNOWN_ENTITY_MASK + 0
    entityList = {"Chicken": 10,
                  "Cow": 11,
                  "Pig": 12,
                  "Sheep": 13,
                  "Wolf": 14,
                  "Villager": 15,
                  "Mooshroom": 16,
                  "Squid": 17,
                  "Rabbit": 18,
                  "Bat": 19,
                  "Iron Golem": 20,
                  "Snow Golem": 21,
                  "Ocelot": 22,
                  "EntityHorse": 23,
                  "Zombie": 32,
                  "Creeper": 33,
                  "Skeleton": 34,
                  "Spider": 35,
                  "Zombie Pigman": 36,
                  "Slime": 37,
                  "Enderman": 38,
                  "Silverfish": 39,
                  "Cave Spider": 40,
                  "Ghast": 41,
                  "Magma Cube": 42,
                  "Blaze": 43,
                  "Zombie Villager": 44,
                  "Witch": 45,
                  "Guardian": 49,
                  "WitherBoss": 52,
                  "EnderDragon": 53,
                  "Endermite": 55,
                  "Player": 63,
                  "Item": 64,
                  "PrimedTnt": 65,
                  "FallingSand": 66,
                  "ThrownExpBottle": 68,
                  "XPOrb": 69,
                  "EyeOfEnderSignal": 70,
                  "EnderCrystal": 71,
                  "Fishing Rod Bobber": 77,
                  "Arrow": 80,
                  "Snowball": 81,
                  "Egg": 82,
                  "Painting": 83,
                  "MinecartRideable": 84,
                  "Fireball": 85,
                  "ThrownPotion": 86,
                  "ThrownEnderpearl": 87,
                  "LeashKnot": 88,
                  "WitherSkull": 89,
                  "Boat": 90,
                  "Lightning": 93,
                  "Blaze Fireball": 94,
                  "Minecart with Hopper": 96,
                  "Minecart with TNT": 97,
                  "Minecart with Chest": 98}

    @classmethod
    def getNumId(cls, v):
        """Retruns the numeric ID of an entity, or a generated one if the entity is not known.
        The generated one is generated like this: 'UNKNOWN_ENTITY_MASK + X', where 'X' is a number.
        The first unknown entity will have the numerical ID 1001, the second one 1002, and so on.
        :v: the entity string ID to search for."""
        id = cls.getId(v)
        if type(id) != int and v not in cls.entityList.keys():
            id = cls.unknown_entity_top + 1
            cls.entityList[v] = cls.entityList['Entity %s'%id] = id
            cls.unknown_entity_top += 1
        return id


class TileTick(object):
    @classmethod
    def pos(cls, tag):
        return [tag[a].value for a in 'xyz']


class InvalidEntity(ValueError):
    pass


class InvalidTileEntiy(ValueError):
    pass
