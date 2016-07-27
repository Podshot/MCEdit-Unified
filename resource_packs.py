# -*- coding: utf-8 -*-
#!# If the comman line parameter '--debug-packs' is given, the logging level is set to debug.
#!# Otherwise, it is set to critical.
from PIL import Image
import zipfile
import directories
import os
import shutil
from config import config
from cStringIO import StringIO

import locale
import traceback
from utilities.misc import Singleton

DEF_ENC = locale.getdefaultlocale()[1]
if DEF_ENC is None:
    DEF_ENC = "UTF-8"

try:
    import resource  # @UnresolvedImport
    resource.setrlimit(resource.RLIMIT_NOFILE, (500,-1))
except:
    pass

#!# Debugging .zip resource pack not loaded bug.

import logging

level = 50
if '--debug-packs' in os.sys.argv:
    level = 10

log = logging.getLogger(__name__)
log.setLevel(level)

#!#


def step(slot):
    '''
    Utility method for multiplying the slot by 16
    
    :param slot: Texture slot
    :type slot: int
    '''
    return slot << 4

'''
Empty comment lines like:
#
are for texture spaces that I don't know what should go there
'''
textureSlots = {
    # Start Top Row
    "grass_top": (step(0),step(0)),
    "stone": (step(1),step(0)),
    "dirt": (step(2),step(0)),
    "grass_side": (step(3),step(0)),
    "planks_oak": (step(4),step(0)),
    "stone_slab_side": (step(5),step(0)),
    "stone_slab_top": (step(6),step(0)),
    "brick": (step(7),step(0)),
    "tnt_side": (step(8),step(0)),
    "tnt_top": (step(9),step(0)),
    "tnt_bottom": (step(10),step(0)),
    "web": (step(11),step(0)),
    "flower_rose": (step(12),step(0)),
    "flower_dandelion": (step(13),step(0)),
    #
    "sapling_oak": (step(15),step(0)),
    "flower_blue_orchid": (step(16),step(0)),
    "flower_allium": (step(17),step(0)),
    "flower_houstonia": (step(18),step(0)),
    "flower_tulip_red": (step(19),step(0)),
    "sapling_roofed_oak": (step(20),step(0)),
    # End Top Row

    # Start Second Row
    "cobblestone": (step(0),step(1)),
    "bedrock": (step(1),step(1)),
    "sand": (step(2),step(1)),
    "gravel": (step(3),step(1)),
    "log_oak": (step(4),step(1)),
    "log_oak_top": (step(5),step(1)),
    "iron_block": (step(6),step(1)),
    "gold_block": (step(7),step(1)),
    "diamond_block": (step(8),step(1)),
    "emerald_block": (step(9),step(1)),
    #
    "red_sand": (step(11),step(1)),
    "mushroom_red": (step(12),step(1)),
    "mushroom_brown": (step(13),step(1)),
    "sapling_jungle": (step(14),step(1)),
    "fire_layer_0": (step(15),step(1)),
    "flower_tulip_orange": (step(16),step(1)),
    "flower_tulip_white": (step(17),step(1)),
    "flower_tulip_pink": (step(18),step(1)),
    "flower_oxeye_daisy": (step(19),step(1)),
    "sapling_acacia": (step(20),step(1)),
    # End Second Row

    # Start Third Row
    "gold_ore": (step(0),step(2)),
    "iron_ore": (step(1),step(2)),
    "coal_ore": (step(2),step(2)),
    "bookshelf": (step(3),step(2)),
    "cobblestone_mossy": (step(4),step(2)),
    "obsidian": (step(5),step(2)),
    #
    "tallgrass": (step(7),step(2)),
    #
    "beacon": (step(9),step(2)),
    "dropper_front_horizontal": (step(10),step(2)),
    "crafting_table_top": (step(11),step(2)),
    "furnace_front_off": (step(12),step(2)),
    "furnace_side": (step(13),step(2)),
    "dispenser_front_horizontal": (step(14),step(2)),
    "fire_layer_1": (step(15),step(2)),
    #
    #
    #
    #
    "daylight_detector_side": (step(20),step(2)),
    # End Third Row

    # Start Fourth Row
    "sponge": (step(0), step(3)),
    "glass": (step(1), step(3)),
    "diamond_ore": (step(2), step(3)),
    "redstone_ore": (step(3), step(3)),
    #
    #
    "stonebrick": (step(6), step(3)),
    "deadbush": (step(7), step(3)),
    "fern": (step(8), step(3)),
    "dirt_podzol_top": (step(9), step(3)),
    "dirt_podzol_side": (step(10), step(3)),
    "crafting_table_side": (step(11), step(3)),
    "crafting_table_front": (step(12), step(3)),
    "furnace_front_on": (step(13), step(3)),
    "furnace_top": (step(14), step(3)),
    "sapling_spruce": (step(15), step(3)),
    #
    #
    #
    #
    # End Fourth Row

    # Start Fifth Row
    "wool_colored_white": (step(0), step(4)),
    "mob_spawner": (step(1), step(4)),
    "snow": (step(2), step(4)),
    "ice": (step(3), step(4)),
    "grass_side_snowed": (step(4), step(4)),
    "cactus_top": (step(5), step(4)),
    "cactus_side": (step(6), step(4)),
    "cactus_bottom": (step(7), step(4)),
    "clay": (step(8), step(4)),
    "reeds": (step(9), step(4)),
    "jukebox_side": (step(10), step(4)),
    "jukebox_top": (step(11), step(4)),
    "waterlily": (step(12), step(4)),
    "mycelium_side": (step(13), step(4)),
    "mycelium_top": (step(14), step(4)),
    "sapling_birch": (step(15), step(4)),
    #
    #
    "dropper_front_vertical": (step(18), step(4)),
    "daylight_detector_inverted_top": (step(19), step(4)),
    # End Fifth Row

    # Start Sixth Row
    "torch_on": (step(0), step(5)),
    "door_wood_upper": (step(1), step(5)),
    "door_iron_upper": (step(2), step(5)),
    "ladder": (step(3), step(5)),
    "trapdoor": (step(4), step(5)),
    "iron_bars": (step(5), step(5)),
    "farmland_wet": (step(6), step(5)),
    "farmland_dry": (step(7), step(5)),
    "wheat_stage_0": (step(8), step(5)),
    "wheat_stage_1": (step(9), step(5)),
    "wheat_stage_2": (step(10), step(5)),
    "wheat_stage_3": (step(11), step(5)),
    "wheat_stage_4": (step(12), step(5)),
    "wheat_stage_5": (step(13), step(5)),
    "wheat_stage_6": (step(14), step(5)),
    "wheat_stage_7": (step(15), step(5)),
    #
    #
    "dispenser_front_vertical": (step(18), step(5)),
    #
    # End Sixth Row

    # Start Seventh Row
    "lever": (step(0), step(6)),
    "door_wood_lower": (step(1), step(6)),
    "door_iron_lower": (step(2), step(6)),
    "redstone_torch_on": (step(3), step(6)),
    "stonebrick_mossy": (step(4), step(6)),
    "stonebrick_cracked": (step(5), step(6)),
    "pumpkin_top": (step(6), step(6)),
    "netherrack": (step(7), step(6)),
    "soul_sand": (step(8), step(6)),
    "glowstone": (step(9), step(6)),
    "piston_top_sticky": (step(10), step(6)),
    "piston_top_normal": (step(11), step(6)),
    "piston_side": (step(12), step(6)),
    "piston_bottom": (step(13), step(6)),
    "piston_inner": (step(14), step(6)),
    "pumpkin_stem_disconnected": (step(15), step(6)),
    #
    #
    #
    # End Seventh Row

    # Start Eigth Row
    "rail_normal_turned": (step(0),step(7)),
    "wool_colored_black": (step(1),step(7)),
    "wool_colored_gray": (step(2),step(7)),
    "redstone_torch_off": (step(3),step(7)),
    "log_spruce": (step(4),step(7)),
    "log_birch": (step(5),step(7)),
    "pumpkin_side": (step(6),step(7)),
    "pumpkin_face_off": (step(7),step(7)),
    "pumpkin_face_on": (step(8),step(7)),
    "cake_top": (step(9),step(7)),
    "cake_side": (step(10),step(7)),
    "cake_inner": (step(11),step(7)),
    "cake_bottom": (step(12),step(7)),
    "mushroom_block_skin_red": (step(13),step(7)),
    "mushroom_block_skin_brown": (step(14),step(7)),
    "pumpkin_stem_connected": (step(15),step(7)),
    #
    #
    "repeater_off_west": (step(18),step(7)),
    #
    # End Eigth Row

    # Start Ninth Row
    "rail_normal": (step(0),step(8)),
    "wool_colored_red": (step(1),step(8)),
    "wool_colored_magenta": (step(2),step(8)),
    "repeater_off_south": (step(3),step(8)),
    "leaves_spruce": (step(4),step(8)),
    #
    "bed_feet_top": (step(6),step(8)),
    "bed_head_top": (step(7),step(8)),
    "melon_side": (step(8),step(8)),
    "melon_top": (step(9),step(8)),
    #
    #
    #
    "mushroom_block_skin_stem": (step(13),step(8)),
    "mushroom_block_inside": (step(14),step(8)),
    "vine": (step(15),step(8)),
    #
    #
    "repeater_off_north": (step(18),step(8)),
    #
    # End Ninth Row

    # Start Tenth Row
    "lapis_block": (step(0),step(9)),
    "wool_colored_green": (step(1),step(9)),
    "wool_colored_lime": (step(2),step(9)),
    "repeater_on_south": (step(3),step(9)),
    #
    "bed_feet_end": (step(5),step(9)),
    "bed_feet_side": (step(6),step(9)),
    "bed_head_side": (step(7),step(9)),
    "bed_head_end": (step(8),step(9)),
    "log_jungle": (step(9),step(9)),
    "cauldron_side": (step(10),step(9)),
    "cauldron_bottom": (step(11),step(9)),
    "brewing_stand_base": (step(12),step(9)),
    "brewing_stand": (step(13),step(9)),
    "endframe_top": (step(14),step(9)),
    "endframe_side": (step(15),step(9)),
    "double_plant_sunflower_bottom": (step(16),step(9)),
    #
    "repeater_off_east": (step(18),step(9)),
    "structure_block_data": (step(19),step(9)),
    "structure_block_corner": (step(20),step(9)),
    # End Tenth Row

    # Start Eleventh Row
    "lapis_ore": (step(0),step(10)),
    "wool_colored_brown": (step(1),step(10)),
    "wool_colored_yellow": (step(2),step(10)),
    "rail_golden": (step(3),step(10)),
    "redstone_dust_cross": (step(4),step(10)),
    #
    "enchanting_table_top": (step(6),step(10)),
    "dragon_egg": (step(7),step(10)),
    "cocoa_stage_2": (step(8),step(10)),
    "cocoa_stage_1": (step(9),step(10)),
    "cocoa_stage_0": (step(10),step(10)),
    "emerald_ore": (step(11),step(10)),
    "trip_wire_source": (step(12),step(10)),
    "trip_wire": (step(13),step(10)),
    "endframe_eye": (step(14),step(10)),
    "end_stone": (step(15),step(10)),
    "double_plant_syringa_bottom": (step(16),step(10)),
    "double_plant_syringa_top": (step(17),step(10)),
    "repeater_on_west": (step(18),step(10)),
    "structure_block_save": (step(19),step(10)),
    "structure_block_load": (step(20),step(10)),
    # End Eleventh Row

    # Start Twelfth Row
    "sandstone_top": (step(0),step(11)),
    "wool_colored_blue": (step(1),step(11)),
    "wool_colored_light_blue": (step(2),step(11)),
    "rail_golden_powered": (step(3),step(11)),
    #
    "redstone_dust_line": (step(5),step(11)),
    "enchanting_table_side": (step(6),step(11)),
    "enchanting_table_bottom": (step(7),step(11)),
    "command_block": (step(8),step(11)),
    "itemframe_backround": (step(9),step(11)),
    "flower_pot": (step(10),step(11)),
    "comparator_off_south": (step(11),step(11)),
    "comparator_on_south": (step(12),step(11)),
    "daylight_detector_top": (step(13),step(11)),
    "redstone_block": (step(14),step(11)),
    "quartz_ore": (step(15),step(11)),
    "double_plant_grass_bottom": (step(16),step(11)),
    "double_plant_grass_top": (step(17),step(11)),
    "repeater_on_north": (step(18),step(11)),
    "command_block_back": (step(19),step(11)),
    "command_block_conditional": (step(20),step(11)),
    "command_block_front": (step(21),step(11)),
    "command_block_side": (step(22),step(11)),
    "bone_block_top": (step(19),step(11)),
    # End Twelfth Row

    # Start Thriteenth Row
    "sandstone_normal": (step(0),step(12)),
    "wool_colored_purple": (step(1),step(12)),
    "wool_colored_pink": (step(2),step(12)),
    "rail_detector": (step(3),step(12)),
    "leaves_jungle": (step(4),step(12)),
    #
    "planks_spruce": (step(6),step(12)),
    "planks_jungle": (step(7),step(12)),
    "carrots_stage_0": (step(8),step(12)),
    "carrots_stage_1": (step(9),step(12)),
    "carrots_stage_2": (step(10),step(12)),
    "carrots_stage_3": (step(11),step(12)),
    "potatoes_stage_3": (step(12),step(12)),
    #
    "piston_right": (step(14),step(12)),
    "piston_down": (step(15),step(12)),
    "double_plant_fern_bottom": (step(16),step(12)),
    "double_plant_fern_top": (step(17),step(12)),
    "repeater_on_east": (step(18),step(12)),
    "repeating_command_block_back": (step(19),step(12)),
    "repeating_command_block_conditional": (step(20),step(12)),
    "repeating_command_block_front": (step(21),step(12)),
    "repeating_command_block_side": (step(22),step(12)),
    "bone_block_side": (step(19),step(12)),
    # End Thriteenth Row

    # Start Fourteenth Row
    "sandstone_bottom": (step(0),step(13)),
    "wool_colored_cyan": (step(1),step(13)),
    "wool_colored_orange": (step(2),step(13)),
    "redstone_lamp_off": (step(3),step(13)),
    "redstone_lamp_on": (step(4),step(13)),
    "stonebrick_carved": (step(5),step(13)),
    "planks_birch": (step(6),step(13)),
    "anvil_base": (step(7),step(13)),
    "anvil_top_damaged_1": (step(8),step(13)),
    "quatrz_block_top": (step(9),step(13)),
    "rail_activator": (step(10),step(13)),
    "rail_activator_powered": (step(11),step(13)),
    "coal_block": (step(12),step(13)),
    "log_acacia_top": (step(13),step(13)),
    "piston_left": (step(14),step(13)),
    "magma": (step(18),step(13)),
    #
    "double_plant_rose_bottom": (step(16),step(13)),
    "double_plant_rose_top": (step(17),step(13)),
    "chain_command_block_back": (step(19),step(11)),
    "chain_command_block_conditional": (step(20),step(11)),
    "chain_command_block_front": (step(21),step(11)),
    "chain_command_block_side": (step(22),step(11)),
    # End Fourteenth Row

    # Start Fifteenth Row
    "nether_brick": (step(0),step(14)),
    "wool_colored_silver": (step(1),step(14)),
    "nether_wart_stage_0": (step(2),step(14)),
    "nether_wart_stage_1": (step(3),step(14)),
    "nether_wart_stage_2": (step(4),step(14)),
    "sandstone_carved": (step(5),step(14)),
    "sandstone_smooth": (step(6),step(14)),
    "anvil_top_damaged_0": (step(7),step(14)),
    "anvil_top_damaged_2": (step(8),step(14)),
    "log_spruce_top": (step(9),step(14)),
    "log_birch_top": (step(10),step(14)),
    "log_jungle_top": (step(11),step(14)),
    "log_big_oak_top": (step(12),step(14)),
    "lava_still": (step(13),step(14)),
    #
    #
    "double_plant_paeonia_bottom": (step(16),step(14)),
    "double_plant_paeonia_top": (step(17),step(14)),
    "nether_wart_block": (step(18),step(14)),
    # End Fifteenth Row

    # Start Sixteenth Row
    "planks_acacia": (step(0),step(15)),
    "planks_big_oak": (step(1),step(15)),
    #
    "log_acacia": (step(3),step(15)),
    "log_big_oak": (step(4),step(15)),
    "hardened_clay": (step(5),step(15)),
    "portal": (step(6),step(15)),
    #
    "quatrz_block_chiseled": (step(8),step(15)),
    "quartz_block_chiseled_top": (step(9),step(15)),
    "quartz_block_lines": (step(10),step(15)),
    "quartz_block_lines_top": (step(11),step(15)),
    #
    #
    #
    #
    #
    "slime": (step(17),step(15)),
    "red_nether_brick": (step(18),step(15)),
    # End Sixteenth Row

    # Start Seventeenth Row
    "ice_packed": (step(0),step(16)),
    "hay_block_side": (step(1),step(16)),
    "hay_block_top": (step(2),step(16)),
    "iron_trapdoor": (step(3),step(16)),
    "stone_granite": (step(4),step(16)),
    "stone_grantie_smooth": (step(5),step(16)),
    "stone_diorite": (step(6),step(16)),
    "stone_diorite_smooth": (step(7),step(16)),
    "stone_andesite": (step(8),step(16)),
    "stone_andesite_smooth": (step(9),step(16)),
    #
    #
    #
    #
    #
    #
    #
    #
    #
    "frosted_ice_0": (step(19), step(16)),
    # End Seventeenth Row

    # Start Eigteenth Row
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    "prismarine_bricks": (step(16),step(17)),
    "prismarine_dark": (step(17),step(17)),
    "prismarine_rough": (step(18),step(17)),
    "purpur_pillar": (step(19),step(17)),
    # End Eigteenth Row

    # Start Ninteenth Row
    "hardened_clay_stained_white": (step(0),step(18)),
    "hardened_clay_stained_orange": (step(1),step(18)),
    "hardened_clay_stained_magenta": (step(2),step(18)),
    "hardened_clay_stained_light_blue": (step(3),step(18)),
    "hardened_clay_stained_yellow": (step(4),step(18)),
    "hardened_clay_stained_lime": (step(5),step(18)),
    "hardened_clay_stained_pink": (step(6),step(18)),
    "hardened_clay_stained_gray": (step(7),step(18)),
    "hardened_clay_stained_silver": (step(8),step(18)),
    "hardened_clay_stained_cyan": (step(9),step(18)),
    "hardened_clay_stained_purple": (step(10),step(18)),
    "hardened_clay_stained_blue": (step(11),step(18)),
    "hardened_clay_stained_brown": (step(12),step(18)),
    "hardened_clay_stained_green": (step(13),step(18)),
    "hardened_clay_stained_red": (step(14),step(18)),
    "hardened_clay_stained_black": (step(15),step(18)),
    "sponge_wet": (step(16),step(18)),
    "sea_lantern": (step(17),step(18)),
    "end_bricks": (step(18),step(18)),
    "purpur_pillar_top": (step(19),step(18)),
    # End Ninteenth Row

    # Start Twentieth Row
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    "hay_block_side_rotated": (step(16),step(19)),
    "quartz_block_lines_rotated": (step(17),step(19)),
    "purpur_block": (step(18),step(19)),
    # End Twentieth Row

    # Start Twentyfirst Row
    "red_sandstone_bottom": (step(0),step(20)),
    "red_sandstone_carved": (step(1),step(20)),
    "red_sandstone_normal": (step(2),step(20)),
    "red_sandstone_smooth": (step(3),step(20)),
    "red_sandstone_top": (step(4),step(20)),
    "door_spruce_upper": (step(5),step(20)),
    "door_birch_upper": (step(6),step(20)),
    "door_jungle_upper": (step(7),step(20)),
    "door_acacia_upper": (step(8),step(20)),
    "door_dark_oak_upper": (step(9),step(20)),
    # 
    # 
    # 
    # 
    # 
    # 
    # 
    #
    "chorus_plant": (step(13),step(20)),
    "chorus_flower_dead": (step(14),step(20)),
    "chorus_flower": (step(15),step(20)),
    "end_rod": (step(16),step(20)),
    # End Twentyfirst Row

    # Start MISC

    # Start More Bed Textures
    "bed_head_side_flipped": (step(1),step(21)),
    "bed_feet_side_flipped": (step(2),step(21)),
    "bed_head_top_flipped": (step(1),step(22)),
    "bed_feet_top_flipped": (step(2),step(22)),
    "bed_feet_top_bottom": (step(3),step(21)),
    "bed_head_top_bottom": (step(3),step(22)),
    "bed_feet_top_top": (step(4),step(22)),
    "bed_head_top_top": (step(4),step(21)),
    # End More Bed Textures

    # Start Comparator Block
    }

class MultipartTexture(object):
    
    def __init__(self, texture_objects):
        self.subclasses = []
        self.runAnyways = []
        self.texture_dict = {}
        for subcls in self.__class__.__subclasses__(): # This is why I love Python
            self.subclasses.append(subcls)
        for cls in self.subclasses:
            instance = cls(texture_objects)
            if instance.runAnyway:
                self.runAnyways.append(instance)
            else:
                self.texture_dict[instance.target] = instance
            
        
class LeverTexture(MultipartTexture):
    target = "lever"
    runAnyway = False
    
    def __init__(self, texture_objects):
        self.texture_objects = texture_objects
    
    def parse_texture(self):
        if "lever" not in self.texture_objects or "cobblestone" not in self.texture_objects:
            return None
        lever = self.texture_objects["lever"].copy()
        cobblestone = self.texture_objects["cobblestone"].copy()
        base_1 = cobblestone.crop((5, 4, 11, 12))
        lever.paste(base_1, (10, 0, 16, 8))
    
        base_2 = cobblestone.crop((5, 0, 11, 3))
        lever.paste(base_2, (10, 8, 16, 11))

        base_3 = cobblestone.crop((4, 0, 12, 3))
        lever.paste(base_3, (2, 0, 10, 3))
        return lever
    
class StandingSignTexture(MultipartTexture):
    target = ""
    runAnyway = True
    position = (step(20), step(5))
    
    def __init__(self, texture_objects):
        self.texture_objects = texture_objects
        
    def parse_texture(self):
        if "planks_oak" not in self.texture_objects or "log_oak" not in self.texture_objects:
            return None
        planks = self.texture_objects["planks_oak"].copy()
        log_tex = self.texture_objects["log_oak"].copy()
        
        sign = planks.crop((0, 7, 16, 16))
        log_tex.paste(sign, (0, 7, 16, 16))
        if log_tex.mode != "RGBA":
            log_tex = log_tex.convert("RGBA")
        return log_tex


class IResourcePack(object):
    '''
    Sets all base variables for a Resource Pack
    '''

    def __init__(self):
        self.__stop = False
        texture_path = os.path.join(directories.parentDir, "textures", self._pack_name)
        self.texture_path = texture_path
        self._isEmpty = False
        self._too_big = False
        self.big_textures_counted = 0
        self.big_textures_max = 10
        self.block_image = {}
        self.propogated_textures = []
        self.all_texture_slots = []
        self.old_terrain = Image.open(os.path.join(directories.getDataDir(), 'terrain.png'))
        for texx in xrange(0,33):
            for texy in xrange(0,33):
                self.all_texture_slots.append((step(texx),step(texy)))
        self._terrain_name = self._pack_name.replace(" ", "_")+".png"
        self._terrain_path = os.path.join("terrain-textures", self._terrain_name.replace(" ", "_"))

    @property
    def pack_name(self):
        '''
        The name of the Resource Pack
        '''
        return self._pack_name

    @property
    def terrain_name(self):
        '''
        Name of the parsed texture PNG file
        '''
        return self._terrain_name

    def terrain_path(self):
        '''
        Path to the parsed PNG file
        '''
        return self._terrain_path

    @property
    def isEmpty(self):
        '''
        Returns true if the Resource Pack doesn't replace the minimum amount of textures
        '''
        return self._isEmpty

    @property
    def tooBig(self):
        '''
        Returns true if the Resource Pack has a greater resolution than 32x32
        '''
        return self._too_big

    def parse_terrain_png(self):
        '''
        Parses each block texture into a usable PNG file like terrain.png
        '''
        multiparts = MultipartTexture(self.block_image)
        log.debug("Parsing terrain.png")
        new_terrain = Image.new("RGBA", (512, 512), None)
        for tex in self.block_image.keys():
            if not self.__stop and tex in textureSlots.keys():
                try:
                    if tex not in multiparts.texture_dict:
                        image = self.block_image[tex]
                    else:
                        image = multiparts.texture_dict[tex].parse_texture()
                        if image is None:
                            continue
                    log.debug("    Image is %s"%tex)
                    log.debug("        Image mode: %s"%image.mode)
                    if image.mode != "RGBA":
                        try:
                            image = image.convert("RGBA")
                            log.debug("        Image converted to RGBA.")
                        except Exception, ee:
                            print "* * *", tex, ee
                    slot = textureSlots[tex]
                    try:
                        new_terrain.paste(image, slot, image)
                    except Exception, eee:
                        print "* * * new_terrain error:", eee
                    self.propogated_textures.append(slot)
                    log.debug("        Image pasted and propagated.")
                except Exception as e:
                    try:
                        # Print the resource pack 'raw' name.
                        print "An Exception occurred while trying to parse textures for {}".format(self._pack_name)
                        log.debug("An Exception occurred while trying to parse textures for {}".format(self._pack_name))
                    except:
                        # I for a reason it fails, print the 'representation' of it.
                        print "An Exception occurred while trying to parse textures for {}".format(repr(self._pack_name))
                        log.debug("An Exception occurred while trying to parse textures for {}".format(repr(self._pack_name)))
                    traceback.print_stack()
                    print "Exception Message: "+str(e)
                    log.debug("Exception Message: "+str(e))
                    print "Exception type: "+str(type(e))
                    log.debug("Exception type: "+str(type(e)))
                    print e
                    self.__stop = True
                    self._isEmpty = True
                    log.debug("Parsing stopped.")
                    log.debug("Resource pack considered as empty.")
                    pass
        for runAnyway in multiparts.runAnyways:
            parsed_texture = runAnyway.parse_texture()
            if parsed_texture is not None:
                new_terrain.paste(parsed_texture, runAnyway.position, parsed_texture)
                self.propogated_textures.append(runAnyway.position)
        copy = self.old_terrain.copy()

        log.debug("Correcting textures...")
        for t in self.all_texture_slots:
            if t not in self.propogated_textures:
                old_tex = copy.crop((t[0],t[1],t[0]+16,t[1]+16))
                new_terrain.paste(old_tex, t, old_tex)
        log.debug("    Done.")

        log.debug("Saving %s."%self._terrain_path)
        new_terrain.save(self._terrain_path)
        log.debug("    Done.")
        try:
            os.remove(self._pack_name.replace(" ", "_")+".png")
        except:
            pass
        if not self.propogated_textures:
            os.remove(self._terrain_path)
            self._isEmpty = True
            log.debug("No propagated textures.\nTexture pack considered as empty.")
            #print u"{} did not replace any textures".format(self._pack_name)

        del self.block_image
        if hasattr(self, 'fps'):
            log.debug("    Closing file descriptors.")
            for f in self.fps:
                f.close()
            log.debug("        Done")
        log.debug("Parsing terrain.png ended.")

    def handle_too_big_packs(self):
        '''
        Removes the parsed PNG file
        '''
        self._too_big = True
        log.debug("Resource pack is too big.")
        #print u"{} seems to be a higher resolution than supported".format(self._pack_name)
        try:
            os.remove(self._terrain_path)
        except:
            pass
        del self.block_image


class ZipResourcePack(IResourcePack):
    '''
    Represents a single Resource Pack that is in a zip file
    '''

    def __init__(self, zipfileFile, noEncConvert=False):
        self.zipfile = zipfileFile
        log.debug("Zip file: %s"%zipfileFile)
        self._pack_name = os.path.splitext(os.path.split(zipfileFile)[-1])[0]
        log.debug("Pack name: %s"%self._pack_name)
        # Define a list of opened textures file objects to be cleaned when operations are finished.
        self.fps = []
        IResourcePack.__init__(self)

        if not os.path.exists(self._terrain_path):
            try:
                self.open_pack()
            except Exception, e:
                if 'seek' not in e:
                    print "Error while trying to load one of the resource packs: {}".format(e)

    def open_pack(self):
        '''
        Opens the zip file and puts texture data into a dictionary, where the key is the texture file name, and the value is a PIL.Image instance
        '''
        zfile = zipfile.ZipFile(self.zipfile)
        self.fps = []
        for name in zfile.infolist():
            if name.filename.endswith(".png") and not name.filename.split(os.path.sep)[-1].startswith("._"):
#                 log.debug("Image found: %s"%name.filename)
                filename = "assets/minecraft/textures/blocks"
                if name.filename.startswith(filename) and name.filename.replace(filename+"/", "").replace(".png","") in textureSlots:
                    log.debug("            Is a possible texture.")
                    block_name = os.path.normpath(name.filename).split(os.path.sep)[-1]
                    block_name = block_name.split(".")[0]
                    #zfile.extract(name.filename, self.texture_path)
                    log.debug("            Block name: %s"%block_name)
                    log.debug("            Opening %s"%name)
                    fp = zfile.open(name)
                    #!# Sending this 'fp' file descriptor to PIL.Image does not work, because such
                    #!# descriptors are not seekable.
                    #!# But, reading the fd data and writing it to a temporary file seem to work...
                    log.debug("                Done. (%s, seekable: %s, readable: %s)"%(type(fp), fp.seekable(), fp.readable()))
                    log.debug("            Saving fp data to temp file.")
                    fp1 = StringIO()
                    fp1.write(fp.read())
                    fp.close()
                    fp1.seek(0)
                    log.debug("                Done.")
                    #possible_texture = Image.open(os.path.join(self.texture_path, os.path.normpath(name.filename)))
                    try:
                        possible_texture = Image.open(fp1)
                        log.debug("            File descriptor for %s opened."%block_name)
                        log.debug("            Is %s."%repr(possible_texture.size))
                    except Exception, e:
                        log.debug("            Can't open descriptor for %s"%block_name)
                        log.debug("            System said:")
                        log.debug("            %s"%repr(e))
                    if possible_texture.size == (16, 16):
                        self.block_image[block_name] = possible_texture
                        if block_name.startswith("repeater_") or block_name.startswith("comparator_"):
                            self.block_image[block_name+"_west"] = possible_texture.rotate(-90)
                            self.block_image[block_name+"_north"] = possible_texture.rotate(180)
                            self.block_image[block_name+"_east"] = possible_texture.rotate(90)
                            self.block_image[block_name+"_south"] = possible_texture
                        if block_name == "piston_side":
                            self.block_image["piston_up"] = possible_texture
                            self.block_image["piston_left"] = possible_texture.rotate(90)
                            self.block_image["piston_down"] = possible_texture.rotate(180)
                            self.block_image["piston_right"] = possible_texture.rotate(-90)
                        if block_name == "hay_block_side":
                            self.block_image["hay_block_side_rotated"] = possible_texture.rotate(-90)
                        if block_name == "quartz_block_lines":
                            self.block_image["quartz_block_lines_rotated"] = possible_texture.rotate(-90)
                        if block_name.startswith("bed_"):
                            if block_name == "bed_head_side":
                                self.block_image["bed_head_side_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                            if block_name == "bed_feet_side":
                                self.block_image["bed_feet_side_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                            if block_name == "bed_head_top":
                                self.block_image["bed_head_top_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                                self.block_image["bed_head_top_bottom"] = possible_texture.rotate(-90)
                                self.block_image["bed_head_top_top"] = possible_texture.rotate(90)
                            if block_name == "bed_feet_top":
                                self.block_image["bed_feet_top_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                                self.block_image["bed_feet_top_bottom"] = possible_texture.rotate(-90)
                                self.block_image["bed_feet_top_top"] = possible_texture.rotate(90)
                        log.debug("             Is loaded.")
                    else:
                        if possible_texture.size == (32, 32):
                            self.block_image[block_name] = possible_texture.resize((16, 16))
                            log.debug("             Is loaded.")
                        elif possible_texture.size == (64, 64) or possible_texture.size == (128, 128) or possible_texture.size == (256, 256):
                            self.big_textures_counted += 1
                            log.debug("             Is too big.")
                        else:
                            self.block_image[block_name] = possible_texture.crop((0,0,16,16))
                            log.debug("             Is loaded.")
                    self.fps.append(fp1)
        if self.big_textures_counted >= self.big_textures_max:
            self.handle_too_big_packs()
        else:
            self.parse_terrain_png()


class FolderResourcePack(IResourcePack):

    def __init__(self, folder, noEncConvert=False):
        self._folder = folder
        self._pack_name = self._folder.replace(" ", "_")
        IResourcePack.__init__(self)
        self._full_path = os.path.join(directories.getMinecraftProfileDirectory(directories.getSelectedProfile()), "resourcepacks", self._folder)
        self.texture_path = os.path.join(directories.parentDir, "textures", self._pack_name)
        if not os.path.exists(self._terrain_path):
            self.add_textures()

    def add_textures(self):
        '''
        Scraps the block textures folder and puts texture data into a dictionary with exactly identical structure as ZipResourcePack
        '''
        base_path = os.path.join(self._full_path, "assets", "minecraft", "textures", "blocks")
        if os.path.exists(base_path):
            files = os.listdir(base_path)
            for tex_file in files:
                if tex_file.endswith(".png") and not tex_file.startswith("._") and tex_file.replace(".png","") in textureSlots:
                    possible_texture = Image.open(os.path.join(base_path, tex_file))
                    block_name = tex_file[:-4]
                    if possible_texture.size == (16, 16):
                        self.block_image[block_name] = possible_texture
                        if block_name.startswith("repeater_") or block_name.startswith("comparator_"):
                            self.block_image[block_name+"_west"] = possible_texture.rotate(-90)
                            self.block_image[block_name+"_north"] = possible_texture.rotate(180)
                            self.block_image[block_name+"_east"] = possible_texture.rotate(90)
                            self.block_image[block_name+"_south"] = possible_texture
                        if block_name == "piston_side":
                            self.block_image["piston_up"] = possible_texture
                            self.block_image["piston_left"] = possible_texture.rotate(90)
                            self.block_image["piston_down"] = possible_texture.rotate(180)
                            self.block_image["piston_right"] = possible_texture.rotate(-90)
                        if block_name == "hay_block_side":
                            self.block_image["hay_block_side_rotated"] = possible_texture.rotate(-90)
                        if block_name == "quartz_block_lines":
                            self.block_image["quartz_block_lines_rotated"] = possible_texture.rotate(-90)
                        if block_name.startswith("bed_"):
                            if block_name == "bed_head_side":
                                self.block_image["bed_head_side_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                            if block_name == "bed_feet_side":
                                self.block_image["bed_feet_side_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                            if block_name == "bed_head_top":
                                self.block_image["bed_head_top_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                                self.block_image["bed_head_top_bottom"] = possible_texture.rotate(-90)
                                self.block_image["bed_head_top_top"] = possible_texture.rotate(90)
                            if block_name == "bed_feet_top":
                                self.block_image["bed_feet_top_flipped"] = possible_texture.transpose(Image.FLIP_LEFT_RIGHT)
                                self.block_image["bed_feet_top_bottom"] = possible_texture.rotate(-90)
                                self.block_image["bed_feet_top_top"] = possible_texture.rotate(90)
                    else:
                        if possible_texture.size == (32, 32):
                            self.block_image[block_name] = possible_texture.resize((16, 16))
                        if possible_texture.size == (64, 64) or possible_texture.size == (128, 128) or possible_texture.size == (256, 256):
                            self.big_textures_counted += 1
                        else:
                            self.block_image[block_name] = possible_texture.crop((0,0,16,16))
        if self.big_textures_counted >= self.big_textures_max:
            self.handle_too_big_packs()
        else:
            self.parse_terrain_png()


class DefaultResourcePack(IResourcePack):
    '''
    Represents the default Resource Pack that is always present
    '''

    def __init__(self):
        self._isEmpty = False
        self._too_big = False
        self._terrain_path = os.path.join(directories.getDataDir(), "terrain.png")
        self._pack_name = "Default"

    def terrain_path(self):
        return self._terrain_path

    @property
    def isEmpty(self):
        return self._isEmpty

    @property
    def tooBig(self):
        return self._too_big

@Singleton
class ResourcePackHandler:
    '''
    A single point to manage which Resource Pack is being used and to provide the paths to each parsed PNG
    '''
    Instance = None
    
    def setup_reource_packs(self):
        '''
        Handles parsing of Resource Packs and removing ones that are either have to0 high of a resolution, or don't replace any textures
        '''
        log.debug("Setting up the resource packs.")
        self._resource_packs = {}
        try:
            os.mkdir("terrain-textures")
        except OSError:
            pass
        self._resource_packs["Default Resource Pack"] = DefaultResourcePack()

        if os.path.exists(os.path.join(directories.getMinecraftProfileDirectory(directories.getSelectedProfile()), "resourcepacks")):
            log.debug("Gathering zipped packs...")
            zipResourcePacks = directories.getAllOfAFile(unicode(os.path.join(directories.getMinecraftProfileDirectory(directories.getSelectedProfile()), "resourcepacks")), ".zip")
            log.debug("Gatering folder packs...")
            folderResourcePacks = os.listdir(unicode(os.path.join(directories.getMinecraftProfileDirectory(directories.getSelectedProfile()), "resourcepacks")))
            log.debug("Processing zipped packs...")
            for zip_tex_pack in zipResourcePacks:
                zrp = ZipResourcePack(zip_tex_pack)
                if not zrp.isEmpty:
                    if not zrp.tooBig:
                        self._resource_packs[zrp.pack_name] = zrp
            log.debug("Processing folder packs...")
            for folder_tex_pack in folderResourcePacks:
                if os.path.isdir(os.path.join(directories.getMinecraftProfileDirectory(directories.getSelectedProfile()), "resourcepacks", folder_tex_pack)):
                    frp = FolderResourcePack(folder_tex_pack)
                    if not frp.isEmpty:
                        if not frp.tooBig:
                            self._resource_packs[frp.pack_name] = frp
        for tex in self._resource_packs.keys():
            pack = self._resource_packs[tex]
            if not os.path.exists(pack.terrain_path()):
                del self._resource_packs[tex]
        try:
            shutil.rmtree(os.path.join(directories.parentDir, "textures"))
        except:
            print "Could not remove \"textures\" directory"
            pass

    def __init__(self):
        try:
            os.mkdir(os.path.join(directories.parentDir, "textures"))
        except OSError:
            pass
        self.setup_reource_packs()
        self._selected_resource_pack = config.settings.resourcePack.get()
        if self._selected_resource_pack not in self._resource_packs.keys():
            self.set_selected_resource_pack_name("Default Resource Pack")

    @property
    def resource_packs(self):
        '''
        A dictionary of Resource Packs, where the key is the pack's file/folder name, and the value is the path to the parsed PNG
        '''
        return self._resource_packs

    def get_available_resource_packs(self):
        '''
        Returns the names of all the Resource Packs that can be used
        '''
        return self._resource_packs.keys()

    def reload_resource_packs(self):
        '''
        Reparses all Resource Packs
        '''
        self.setup_resource_packs()
        
    def reparse_resource_pack(self, packName):
        if packName in self._resource_packs:
            pack = self._resource_packs[packName]
            if isinstance(pack, FolderResourcePack):
                pack.add_textures()
            elif isinstance(pack, ZipResourcePack):
                pack.open_pack()

    def get_selected_resource_pack_name(self):
        '''
        Returns the currently selected Resource Pack's name
        '''
        return self._selected_resource_pack

    def set_selected_resource_pack_name(self, name):
        '''
        Sets the currently selected Resource Pack
        
        :param name: Name of the Resource Pack
        '''
        config.settings.resourcePack.set(name)
        self._selected_resource_pack = name

    def get_selected_resource_pack(self):
        '''
        Returns the selected Resource Pack instance. Can be an instance of either DefaultResourcePack, ZipResourcePack or FolderResourcePack
        '''
        return self._resource_packs[self._selected_resource_pack]

#packs = ResourcePackHandler()
