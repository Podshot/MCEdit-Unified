from logging import getLogger

logger = getLogger(__name__)

items_txt = """
#:mc-version Minecraft 1.8.0

# This section is for defining items.
# Do not remove quotes, the code requires this section be in a quote block to work.

# Also note MCEdit uses this file for items only (editing chest contents etc),
# not for rendering blocks.
  
#            Blocks
# IDSTR                 NAME                DAMAGE
  minecraft:stone       Stone               0
  minecraft:stone       Granite             1
  minecraft:stone       Polished_Granite    2
  minecraft:stone       Diorite             3
  minecraft:stone       Polished_Diorite    4
  minecraft:stone       Andesite            5
  minecraft:stone       Polished_Andesite   6
  minecraft:grass       Grass                  
  minecraft:dirt        Dirt                0
  minecraft:dirt        Coarse_Dirt         1
  minecraft:dirt        Podzol              2
  minecraft:cobblestone Cobblestone            
  minecraft:planks  Oak_Wooden_Planks       0
  minecraft:planks  Spruce_Wooden_Planks    1
  minecraft:planks  Birch_Wooden_Planks     2
  minecraft:planks  Jungle_Wooden_Planks    3
  minecraft:planks  Acacia_Wooden_Planks    4
  minecraft:planks  Dark_Oak_Wooden_Planks  5
  minecraft:sapling  Oak_Sapling            0
  minecraft:sapling  Spruce_Sapling         1
  minecraft:sapling  Birch_Sapling          2
  minecraft:sapling  Jungle_Sapling         3
  minecraft:sapling  Acacia_Sapling         4
  minecraft:sapling  Dark_Oak_Sapling       5
  minecraft:bedrock  Bedrock                
  minecraft:flowing_water  Water                  
  minecraft:water  Still_Water            
  minecraft:flowing_lava  Lava                   
  minecraft:lava  Still_Lava          
  minecraft:sand  Sand                      0
  minecraft:sand  Red_Sand                  1
  minecraft:gravel  Gravel
  minecraft:gold_ore  Gold_Ore               
  minecraft:iron_ore  Iron_Ore               
  minecraft:coal_ore  Coal_Ore               
  minecraft:log  Oak_Wood                0
  minecraft:log  Dark_Wood               1
  minecraft:log  Birch_Wood              2
  minecraft:log  Jungle_Wood             3
  minecraft:log  Acacia_Wood              4
  minecraft:log  Dark_Oak_Wood             5
  minecraft:leaves  Oak_Leaves              0
  minecraft:leaves  Dark_Leaves             1
  minecraft:leaves  Birch_Leaves            2
  minecraft:leaves  Jungle_Leaves           3
  minecraft:leaves  Acacia_Leaves           2
  minecraft:leaves  Dark_Oak_Leaves         3
  minecraft:sponge  Sponge                  0
  minecraft:sponge  Wet_Sponge              1
  minecraft:glass  Glass                    
  minecraft:lapis_ore  Lapis_Lazuli_Ore         
  minecraft:lapis_block  Lapis_Lazuli_Block      
  minecraft:dispenser  Dispenser                
  minecraft:sandstone   Sandstone           0
  minecraft:sandstone  Chiseled_Sandstone   1
  minecraft:sandstone  Smooth_Sandstone     2
  minecraft:noteblock  Note_Block   
  minecraft:Bed_Block  Bed_Block
  minecraft:golden_rail  Powered_Rail             
  minecraft:detector_rail  Detector_Rail            
  minecraft:sticky_piston  Sticky_Piston            
  minecraft:web  Cobweb                   
  minecraft:tallgrass  Tall_Grass(Dead_Shrub) 0
  minecraft:tallgrass  Tall_Grass             1
  minecraft:tallgrass  Tall_Grass(Fern)       2
  minecraft:deadbush  Dead_Shrub                
  minecraft:piston  Piston                   
  minecraft:piston_head  Piston(Head)            
  minecraft:wool  Wool                     0
  minecraft:wool  Orange_Wool              1
  minecraft:wool  Magenta_Wool             2
  minecraft:wool  Light_Blue_Wool          3
  minecraft:wool  Yellow_Wool              4
  minecraft:wool  Lime_Wool                5
  minecraft:wool  Pink_Wool                6
  minecraft:wool  Gray_Wool                7
  minecraft:wool  Light_Gray_Wool          8
  minecraft:wool  Cyan_Wool                9
  minecraft:wool  Purple_Wool              10
  minecraft:wool  Blue_Wool                11
  minecraft:wool  Brown_Wool               12
  minecraft:wool  Green_Wool               13
  minecraft:wool  Red_Wool                 14
  minecraft:wool  Black_Wool               15
  minecraft:piston_extension Piston_Movement_Placeholder
  minecraft:yellow_flower  Dandelion                  
  minecraft:red_flower  Poppy                0
  minecraft:red_flower  Blue_Orchid          1
  minecraft:red_flower  Allium               2
  minecraft:red_flower  Azure_Bluet          3  
  minecraft:red_flower  Red_Tulip            4
  minecraft:red_flower  Orange_Tulip         5
  minecraft:red_flower  White_Tulip          6
  minecraft:red_flower  Pink_Tulip           7
  minecraft:red_flower  Oxeye_Daisy          8  
  minecraft:brown_mushroom  Brown_Mushroom          
  minecraft:red_mushroom  Red_Mushroom             
  minecraft:gold_block  Block_of_Gold            
  minecraft:iron_block  Block_of_Iron          
  minecraft:double_stone_slab  Double_Stone_Slab        0
  minecraft:double_stone_slab  Double_Sandstone_Slab    1
  minecraft:double_stone_slab  Double_Wooden_Slab       2
  minecraft:double_stone_slab  Double_Stone_Slab        3
  minecraft:double_stone_slab  Double_Brick_Slab           4
  minecraft:double_stone_slab  Double_Stone_Brick_Slab     5
  minecraft:double_stone_slab  Double_Nether_Brick_Slab    6
  minecraft:double_stone_slab  Double_Quartz_Slab                 7
  minecraft:double_stone_slab  Smooth_Double_Stone_Slab           8
  minecraft:double_stone_slab  Smooth_Double_Sandstone_Slab       9
  minecraft:stone_slab  Stone_Slab                  0
  minecraft:stone_slab  Sandstone_Slab              1
  minecraft:stone_slab  Wooden_Slab                 2
  minecraft:stone_slab  Stone_Slab                  3
  minecraft:stone_slab  Brick_Slab                  4
  minecraft:stone_slab  Stone_Brick_Slab            5
  minecraft:stone_slab  Nether_Brick_Slab           6
  minecraft:stone_slab  Quartz_Slab                 7
  minecraft:brick_block  Bricks                 
  minecraft:tnt  TNT            0
  minecraft:tnt  Primed_TNT     1
  minecraft:bookshelf  Bookshelf                
  minecraft:mossy_cobblestone  Mossy_Cobblestone               
  minecraft:obsidian  Obsidian                
  minecraft:torch  Torch                   
  minecraft:fire  Fire                     
  minecraft:mob_spawner  Monster_Spawner         
  minecraft:oak_stairs  Oak_Wood_Stairs          
  minecraft:chest  Chest                    
  minecraft:redstone_wire  Redstone_Dust           
  minecraft:diamond_ore  Diamond_Ore             
  minecraft:diamond_block  Block_of_Diamond         
  minecraft:crafting_table  Workbench                
  minecraft:wheat Wheat                    
  minecraft:farmland  Farmland                 
  minecraft:furnace  Furnace                  
  minecraft:lit_furnace  Lit_Furnace             
  minecraft:standing_sign  Standing_Sign                     
  minecraft:ladder  Ladder                 
  minecraft:rail  Rail                     
  minecraft:stone_stairs  Stone_Stairs             
  minecraft:wall_sign  Wall_Sign                
  minecraft:lever  Lever                    
  minecraft:stone_pressure_plate  Stone_Pressure_Plate           
  minecraft:wooden_pressure_plate  Wooden_Pressure_Plate    
  minecraft:redstone_ore  Redstone_Ore            
  minecraft:lit_redstone_ore  Glowing_Redstone_Ore    
  minecraft:unlit_redstone_torch  Redstone_Torch_(Off)     
  minecraft:redstone_torch  Redstone_Torch         
  minecraft:stone_button  Stone_Button             
  minecraft:snow_layer  Snow_Layer               
  minecraft:ice  Ice                     
  minecraft:snow  Snow                     
  minecraft:cactus  Cactus                   
  minecraft:clay  Clay                     
  minecraft:reeds  Sugar_Cane              
  minecraft:jukebox  Jukebox                
  minecraft:fence  Oak_Fence                   
  minecraft:pumpkin  Pumpkin                
  minecraft:netherrack  Netherrack               
  minecraft:soul_sand  Soul_Sand              
  minecraft:glowstone  Glowstone                
  minecraft:portal  Nether_Portal                  
  minecraft:lit_pumpkin  Jack-o'-lantern          
  minecraft:cake  Cake                     
  minecraft:unpowered_repeater  Repeater_Block_(off)     
  minecraft:powered_repeater  Repeater_Block         
  minecraft:stained_glass  White_Stained_Glass                  0
  minecraft:stained_glass  Orange_Stained_Glass                 1
  minecraft:stained_glass  Magenta_Stained_Glass                2
  minecraft:stained_glass  Light_Blue_Stained_Glass             3
  minecraft:stained_glass  Yellow_Stained_Glass                 4
  minecraft:stained_glass  Lime_Stained_Glass                   5
  minecraft:stained_glass  Pink_Stained_Glass                   6
  minecraft:stained_glass  Gray_Stained_Glass                   7
  minecraft:stained_glass  Light_Gray_Stained_Glass             8
  minecraft:stained_glass  Cyan_Stained_Glass                   9
  minecraft:stained_glass  Purple_Stained_Glass                 10
  minecraft:stained_glass  Blue_Stained_Glass                   11
  minecraft:stained_glass  Brown_Stained_Glass                  12
  minecraft:stained_glass  Green_Stained_Glass                  13
  minecraft:stained_glass  Red_Stained_Glass                    14
  minecraft:stained_glass  Black_Stained_Glass                  15
  minecraft:trapdoor  Trapdoor                
  minecraft:monster_egg  Silverfish_Block_(Stone)               0  
  minecraft:monster_egg  Silverfish_Block_(Cobblestone)         1
  minecraft:monster_egg  Silverfish_Block_(Stone_Bricks)        2
  minecraft:monster_egg  Silverfish_Block_(Mossy_Stone_Bricks)  3
  minecraft:monster_egg  Silverfish_Block_(Cracked_Stone_Bricks) 4
  minecraft:monster_egg  Silverfish_Block_(Chiseled_Stone_Bricks) 5
  minecraft:stonebrick  Stone_Brick                0
  minecraft:stonebrick  Mossy_Stone_Brick          1
  minecraft:stonebrick  Cracked_Stone_Brick        2
  minecraft:stonebrick  Chiseled_Stone_Brick       3
  minecraft:brown_mushroom_block  Brown_Mushroom_Block    
  minecraft:red_mushroom_block  Red_Mushroom_Block       
  minecraft:iron_bars  Iron_Bars               
  minecraft:glass_pane  Glass_Pane               
  minecraft:melon_block  Melon                   
  minecraft:pumpkin_stem  Pumpkin_Stem             
  minecraft:melon_stem  Melon_Stem               
  minecraft:vine  Vines                   
  minecraft:fence_gate  Oak_Fence_Gate              
  minecraft:brick_stairs  Brick_Stairs            
  minecraft:stone_brick_stairs  Stone_Brick_Stairs       
  minecraft:mycelium  Mycelium                
  minecraft:waterlily  Lily_Pad                 
  minecraft:nether_brick  Nether_Brick            
  minecraft:nether_brick_fence  Nether_Brick_Fence       
  minecraft:nether_brick_stairs  Nether_Brick_Stairs                
  minecraft:enchanting_table  Enchantment_Table   
  minecraft:brewing_stand  Brewing_Stand        
  minecraft:cauldron  Cauldron                 
  minecraft:end_portal  End_Portal               
  minecraft:end_portal_frame  End_Portal_Frame         
  minecraft:end_stone  End_Stone               
  minecraft:dragon_egg  Dragon_Egg               
  minecraft:redstone_lamp  Redstone_Lamp            
  minecraft:lit_redstone_lamp  Redstone_Lamp_(on)       
  minecraft:double_wooden_slab  Double_Oak_Wood_Slab         0
  minecraft:double_wooden_slab  Double_Spruce_Wood_Slab      1
  minecraft:double_wooden_slab  Double_Birch_Wood_Slab       2
  minecraft:double_wooden_slab  Double_Jungle_Wood_Slab      3
  minecraft:double_wooden_slab  Double_Acacia_Wood_Slab      4
  minecraft:double_wooden_slab  Double_Dark_Oak_Wood_Slab    5
  minecraft:wooden_slab  Oak_Wood_Slab            0
  minecraft:wooden_slab  Spruce_Wood_Slab         1
  minecraft:wooden_slab  Birch_Wood_Slab          2
  minecraft:wooden_slab  Jungle_Wood_Slab         3
  minecraft:wooden_slab  Acacia_Wood_Slab         4
  minecraft:wooden_slab  Dark_Oak_Wood_Slab       5
  minecraft:cocoa  Cocoa_Plant             
  minecraft:sandstone_stairs  Sandstone_Stairs      
  minecraft:emerald_ore  Emerald_Ore             
  minecraft:ender_chest  Ender_Chest             
  minecraft:tripwire_hook  Tripwire_Hook           
  minecraft:tripwire  Tripwire                 
  minecraft:emerald_block  Block_of_Emerald         
  minecraft:spruce_stairs  Spruce_Wood_Stairs       
  minecraft:birch_stairs  Birch_Wood_Stairs        
  minecraft:jungle_stairs  Jungle_Wood_Stairs       
  minecraft:command_block  Command_Block            
  minecraft:beacon  Beacon                   
  minecraft:cobblestone_wall  Cobblestone_Wall                  0
  minecraft:cobblestone_wall  Mossy_Cobblestone_Wall            1
  minecraft:flower_pot  Flower_Pot             
  minecraft:carrots  Carrots                
  minecraft:potatoes  Potatoes                 
  minecraft:wooden_button  Wooden_Button           
  minecraft:skull  Mob_Head                      
  minecraft:anvil  Anvil                      0
  minecraft:anvil  Anvil_(Damaged)            1
  minecraft:anvil  Anvil_(Very_Damaged)       2
  minecraft:trapped_chest  Trapped_Chest                     
  minecraft:light_weighted_pressure_plate  Weighted_Pressure_Plate_(Light)    
  minecraft:heavy_weighted_pressure_plate  Weighted_Pressure_Plate_(Heavy)    
  minecraft:unpowered_comparator  Redstone_Comparator_(Off)     
  minecraft:powered_comparator  Redstone_Comparator_(On)       
  minecraft:daylight_detector  Daylight_Sensor                   
  minecraft:redstone_block  Block_of_Redstone                  
  minecraft:quartz_ore  Nether_Quartz_Ore                 
  minecraft:hopper  Hopper                             
  minecraft:quartz_block  Block_of_Quartz            0
  minecraft:quartz_block  Chiseled_Quartz_Block      1
  minecraft:quartz_block  Pillar_Quartz_Block        2
  minecraft:quartz_stairs  Quartz_Stairs                      
  minecraft:activator_rail  Activator_Rail                     
  minecraft:dropper  Dropper                            
  minecraft:stained_hardened_clay  White_Stained_Clay               0        
  minecraft:stained_hardened_clay  Orange_Stained_Clay              1
  minecraft:stained_hardened_clay  Magenta_Stained_Clay             2
  minecraft:stained_hardened_clay  Light_Blue_Stained_Clay          3
  minecraft:stained_hardened_clay  Yellow_Stained_Clay              4
  minecraft:stained_hardened_clay  Lime_Stained_Clay                5
  minecraft:stained_hardened_clay  Pink_Stained_Clay                6
  minecraft:stained_hardened_clay  Gray_Stained_Clay                7
  minecraft:stained_hardened_clay  Light_Gray_Stained_Clay          8
  minecraft:stained_hardened_clay  Cyan_Stained_Clay                9
  minecraft:stained_hardened_clay  Purple_Stained_Clay              10
  minecraft:stained_hardened_clay  Blue_Stained_Clay                11
  minecraft:stained_hardened_clay  Brown_Stained_Clay               12
  minecraft:stained_hardened_clay  Green_Stained_Clay               13
  minecraft:stained_hardened_clay  Red_Stained_Clay                 14
  minecraft:stained_hardened_clay  Black_Stained_Clay               15
  minecraft:stained_glass_pane  White_Stained_Glass_Pane               0        
  minecraft:stained_glass_pane  Orange_Stained_Glass_Pane              1
  minecraft:stained_glass_pane  Magenta_Stained_Glass_Pane             2
  minecraft:stained_glass_pane  Light_Blue_Stained_Glass_Pane          3
  minecraft:stained_glass_pane  Yellow_Stained_Glass_Pane              4
  minecraft:stained_glass_pane  Lime_Stained_Glass_Pane                5
  minecraft:stained_glass_pane  Pink_Stained_Glass_Pane                6
  minecraft:stained_glass_pane  Gray_Stained_Glass_Pane                7
  minecraft:stained_glass_pane  Light_Gray_Stained_Glass_Pane          8
  minecraft:stained_glass_pane  Cyan_Stained_Glass_Pane                9
  minecraft:stained_glass_pane  Purple_Stained_Glass_Pane              10
  minecraft:stained_glass_pane  Blue_Stained_Glass_Pane                11
  minecraft:stained_glass_pane  Brown_Stained_Glass_Pane               12
  minecraft:stained_glass_pane  Green_Stained_Glass_Pane               13
  minecraft:stained_glass_pane  Red_Stained_Glass_Pane                 14
  minecraft:stained_glass_pane  Black_Stained_Glass_Pane               15
  minecraft:leaves2  Acacia_Leaves      0
  minecraft:leaves2  Dark_Oak_Leaves    1
  minecraft:log2  Acacia_Wood           0
  minecraft:log2  Dark_Oak_Wood         1
  minecraft:acacia_stairs  Acacia_Wood_Stairs
  minecraft:dark_oak_stairs  Dark_Oak_Wood_Stairs
  minecraft:slime Slime_Block
  minecraft:barrier Barrier
  minecraft:iron_trapdoor  Iron_Trapdoor
  minecraft:prismarine  Prismarine       0
  minecraft:prismarine  Prismarine_Bricks       1
  minecraft:prismarine  Dark_Prismarine       2
  minecraft:sea_lantern  Sea_Lantern
  minecraft:hay_block  Hay_Block                          
  minecraft:carpet  White_Carpet               0        
  minecraft:carpet  Orange_Carpet             1
  minecraft:carpet  Magenta_Carpet             2
  minecraft:carpet  Light_Blue_Carpet         3
  minecraft:carpet  Yellow_Carpet             4
  minecraft:carpet  Lime_Carpet                5
  minecraft:carpet  Pink_Carpet                6
  minecraft:carpet  Gray_Carpet              7
  minecraft:carpet  Light_Carpet         8
  minecraft:carpet  Cyan_Carpet                9
  minecraft:carpet  Purple_Carpet              10
  minecraft:carpet  Blue_Carpet                11
  minecraft:carpet  Brown_Carpet               12
  minecraft:carpet  Green_Carpet               13
  minecraft:carpet  Red_Carpet                 14
  minecraft:carpet  Black_Carpet               15                           
  minecraft:hardened_clay  Hardened_Clay                      
  minecraft:coal_block  Block_of_Coal 
  minecraft:packed_ice Packed_Ice
  minecraft:double_plant  Large_Flowers
  minecraft:standing_banner  Free-Standing_Banner
  minecraft:wall_banner  Wall_Banner
  minecraft:daylight_detector_inverted Inverted_Daylight_Sensor
  minecraft:red_sandstone Red_Sandstone                0
  minecraft:red_sandstone Smooth_Red_Sandstone         1
  minecraft:red_sandstone Chiseled_Red_Sandstone       2
  minecraft:red_sandstone_stairs Red_Sandstone_Stairs
  minecraft:double_stone_slab2 Double_Red_Sandstone_Slab
  minecraft:stone_slab2 Red_Sandstone_Slab
  minecraft:spruce_fence_gate Spruce_Fence_Gate
  minecraft:birch_fence_gate Birch_Fence_Gate
  minecraft:jungle_fence_gate Jungle_Fence_Gate
  minecraft:dark_oak_fence_gate Dark_Oak_Fence_Gate
  minecraft:acacia_fence_gate Acacia_Fence_Gate
  minecraft:spruce_fence Spruce_Fence
  minecraft:birch_fence Birch_Fence
  minecraft:jungle_fence Jungle_Fence
  minecraft:dark_oak_fence Dark_Oak_Fence
  minecraft:acacia_fence Acacia_Fence
  minecraft:acacia_fence Acacia_Fence

# Legacy block entries:
# ID  NAME                   DAMAGE
  1       Stone               0
  1       Granite             1
  1       Polished_Granite    2
  1       Diorite             3
  1       Polished_Diorite    4
  1       Andesite            5
  1       Polished_Andesite   6
  2       Grass                  
  3        Dirt                0
  3        Coarse_Dirt         1
  3        Podzol              2
  4  Cobblestone            
  5  Oak_Wooden_Planks       0
  5  Spruce_Wooden_Planks    1
  5  Birch_Wooden_Planks     2
  5  Jungle_Wooden_Planks    3
  5  Acacia_Wooden_Planks    4
  5  Dark_Oak_Wooden_Planks  5
  6 Oak_Sapling            0
  6  Spruce_Sapling         1
  6  Birch_Sapling          2
  6  Jungle_Sapling         3
  6  Acacia_Sapling         4
  6  Dark_Oak_Sapling       5
  7  Bedrock                
  8  Water                  
  9  Still_Water            
  10  Lava                   
  11  Still_Lava          
  12  Sand                      0
  12  Red_Sand                  1
  13  Gravel
  14  Gold_Ore               
  15  Iron_Ore               
  16  Coal_Ore               
  17  Oak_Wood                0
  17  Dark_Wood               1
  17 Birch_Wood              2
  17  Jungle_Wood             3
  17  Acacia_Wood              4
  17  Dark_Oak_Wood             5
  18 Oak_Leaves              0
  18  Dark_Leaves             1
  18  Birch_Leaves            2
  18  Jungle_Leaves           3
  18  Acacia_Leaves           2
  18  Dark_Oak_Leaves         3
  19  Sponge                  0
  19  Wet_Sponge              1
  20  Glass                    
  21  Lapis_Lazuli_Ore         
  22  Lapis_Lazuli_Block      
  23  Dispenser                
  24   Sandstone           0
  24  Chiseled_Sandstone   1
  24  Smooth_Sandstone     2
  25  Note_Block   
  26  Bed_Block
  27  Powered_Rail             
  28  Detector_Rail            
  29  Sticky_Piston            
  30  Cobweb                   
  31  Tall_Grass(Dead_Shrub) 0
  31  Tall_Grass             1
  31  Tall_Grass(Fern)       2
  32  Dead_Shrub                
  33  Piston                   
  34  Piston(Head)            
  35  Wool                     0
  35  Orange_Wool              1
  35  Magenta_Wool             2
  35  Light_Blue_Wool          3
  35  Yellow_Wool              4
  35  Lime_Wool                5
  35  Pink_Wool                6
  35  Gray_Wool                7
  35  Light_Gray_Wool          8
  35  Cyan_Wool                9
  35  Purple_Wool              10
  35  Blue_Wool                11
  35  Brown_Wool               12
  35  Green_Wool               13
  35  Red_Wool                 14
  35  Black_Wool               15
  36 Piston_Movement_Placeholder
  37  Dandelion                  
  38  Poppy                0
  38  Blue_Orchid          1
  38  Allium               2
  38  Azure_Bluet          3  
  38  Red_Tulip            4
  38  Orange_Tulip         5
  38  White_Tulip          6
  38  Pink_Tulip           7
  38  Oxeye_Daisy          8  
  39  Brown_Mushroom          
  40  Red_Mushroom             
  41  Block_of_Gold            
  42  Block_of_Iron          
  43  Double_Stone_Slab        0
  43  Double_Sandstone_Slab    1
  43  Double_Wooden_Slab       2
  43  Double_Stone_Slab        3
  43  Double_Brick_Slab           4
  43  Double_Stone_Brick_Slab     5
  43  Double_Nether_Brick_Slab    6
  43  Double_Quartz_Slab                 7
  43  Smooth_Double_Stone_Slab           8
  43  Smooth_Double_Sandstone_Slab       9
  44  Stone_Slab                  0
  44 Sandstone_Slab              1
  44  Wooden_Slab                 2
  44 Stone_Slab                  3
  44  Brick_Slab                  4
  44  Stone_Brick_Slab            5
  44  Nether_Brick_Slab           6
  44  Quartz_Slab                 7
  45  Bricks                 
  46  TNT            0
  46  Primed_TNT     1
  47  Bookshelf                
  48  Mossy_Cobblestone               
  49  Obsidian                
  50  Torch                   
  51  Fire                     
  52  Monster_Spawner         
  53  Oak_Wood_Stairs          
  54  Chest                    
  55  Redstone_Dust           
  56  Diamond_Ore             
  57  Block_of_Diamond         
  58  Workbench                
  59  Wheat                    
  60  Farmland                 
  61  Furnace                  
  62  Lit_Furnace             
  63  Standing_Sign               
  64  Oak_Door_Block       
  65  Ladder                 
  66  Rail                     
  67  Stone_Stairs             
  68  Wall_Sign                
  69  Lever                    
  70  Stone_Pressure_Plate     
  71  Iron_Door_Block         
  72  Wooden_Pressure_Plate    
  73  Redstone_Ore            
  74  Glowing_Redstone_Ore    
  75  Redstone_Torch_(Off)     
  76  Redstone_Torch         
  77  Stone_Button             
  78  Snow_Layer               
  79  Ice                     
  80  Snow                     
  81  Cactus                   
  82  Clay                     
  83  Sugar_Cane              
  84  Jukebox                
  85  Oak_Fence                   
  86  Pumpkin                
  87  Netherrack               
  88  Soul_Sand              
  89  Glowstone                
  90  Nether_Portal                  
  91  Jack-o'-lantern          
  92  Cake                     
  93  Repeater_Block_(off)     
  94  Repeater_Block         
  95  White_Stained_Glass                  0
  95  Orange_Stained_Glass                 1
  95  Magenta_Stained_Glass                2
  95  Light_Blue_Stained_Glass             3
  95  Yellow_Stained_Glass                 4
  95  Lime_Stained_Glass                   5
  95  Pink_Stained_Glass                   6
  95  Gray_Stained_Glass                   7
  95  Light_Gray_Stained_Glass             8
  95  Cyan_Stained_Glass                   9
  95  Purple_Stained_Glass                 10
  95  Blue_Stained_Glass                   11
  95  Brown_Stained_Glass                  12
  95  Green_Stained_Glass                  13
  95  Red_Stained_Glass                    14
  95  Black_Stained_Glass                  15
  96  Trapdoor                
  97  Silverfish_Block_(Stone)               0  
  97  Silverfish_Block_(Cobblestone)         1
  97  Silverfish_Block_(Stone_Bricks)        2
  97  Silverfish_Block_(Mossy_Stone_Bricks)  3
  97  Silverfish_Block_(Cracked_Stone_Bricks) 4
  97  Silverfish_Block_(Chiseled_Stone_Bricks) 5
  98  Stone_Brick                0
  98  Mossy_Stone_Brick          1
  98  Cracked_Stone_Brick        2
  98  Chiseled_Stone_Brick       3
  99  Brown_Mushroom_Block    
  100  Red_Mushroom_Block       
  101  Iron_Bars               
  102  Glass_Pane               
  103  Melon                   
  104  Pumpkin_Stem             
  105  Melon_Stem               
  106  Vines                   
  107  Oak_Fence_Gate              
  108  Brick_Stairs            
  109  Stone_Brick_Stairs       
  110  Mycelium                
  111  Lily_Pad                 
  112  Nether_Brick            
  113  Nether_Brick_Fence       
  114  Nether_Brick_Stairs    
  115  Nether_Wart             
  116  Enchantment_Table   
  117  Brewing_Stand        
  118  Cauldron                 
  119  End_Portal               
  120  End_Portal_Frame         
  121  End_Stone               
  122  Dragon_Egg               
  123  Redstone_Lamp            
  124  Redstone_Lamp_(on)       
  125  Double_Oak_Wood_Slab         0
  125  Double_Spruce_Wood_Slab      1
  125  Double_Birch_Wood_Slab       2
  125  Double_Jungle_Wood_Slab      3
  125  Double_Acacia_Wood_Slab      4
  125  Double_Dark_Oak_Wood_Slab    5
  126  Oak_Wood_Slab            0
  126  Spruce_Wood_Slab         1
  126  Birch_Wood_Slab          2
  126  Jungle_Wood_Slab         3
  126  Acacia_Wood_Slab         4
  126  Dark_Oak_Wood_Slab       5
  127  Cocoa_Plant             
  128  Sandstone_Stairs      
  129  Emerald_Ore             
  130  Ender_Chest             
  131  Tripwire_Hook           
  132  Tripwire                 
  133  Block_of_Emerald         
  134  Spruce_Wood_Stairs       
  135  Birch_Wood_Stairs        
  136 Jungle_Wood_Stairs       
  137  Command_Block            
  138  Beacon                   
  139  Cobblestone_Wall                  0
  139  Mossy_Cobblestone_Wall            1
  140  Flower_Pot             
  141  Carrots                
  142  Potatoes                 
  143  Wooden_Button           
  144  Mob_Head                      
  145  Anvil                      0
  145  Anvil_(Damaged)            1
  145  Anvil_(Very_Damaged)       2
  146  Trapped_Chest                     
  147  Weighted_Pressure_Plate_(Light)    
  148  Weighted_Pressure_Plate_(Heavy)    
  149  Redstone_Comparator_(Off)     
  150  Redstone_Comparator_(On)       
  151  Daylight_Sensor                   
  152  Block_of_Redstone                  
  153  Nether_Quartz_Ore                 
  154  Hopper                             
  155  Block_of_Quartz            0
  155  Chiseled_Quartz_Block      1
  155  Pillar_Quartz_Block        2
  156  Quartz_Stairs                      
  157  Activator_Rail                     
  158  Dropper                            
  159  White_Stained_Clay               0        
  159  Orange_Stained_Clay              1
  159  Magenta_Stained_Clay             2
  159  Light_Blue_Stained_Clay          3
  159  Yellow_Stained_Clay              4
  159  Lime_Stained_Clay                5
  159  Pink_Stained_Clay                6
  159  Gray_Stained_Clay                7
  159  Light_Gray_Stained_Clay          8
  159  Cyan_Stained_Clay                9
  159  Purple_Stained_Clay              10
  159  Blue_Stained_Clay                11
  159  Brown_Stained_Clay               12
  159  Green_Stained_Clay               13
  159  Red_Stained_Clay                 14
  159  Black_Stained_Clay               15
  160  White_Stained_Glass_Pane               0        
  160  Orange_Stained_Glass_Pane              1
  160  Magenta_Stained_Glass_Pane             2
  160  Light_Blue_Stained_Glass_Pane          3
  160  Yellow_Stained_Glass_Pane              4
  160  Lime_Stained_Glass_Pane                5
  160  Pink_Stained_Glass_Pane                6
  160  Gray_Stained_Glass_Pane                7
  160  Light_Gray_Stained_Glass_Pane          8
  160  Cyan_Stained_Glass_Pane                9
  160  Purple_Stained_Glass_Pane              10
  160  Blue_Stained_Glass_Pane                11
  160  Brown_Stained_Glass_Pane               12
  160  Green_Stained_Glass_Pane               13
  160  Red_Stained_Glass_Pane                 14
  160  Black_Stained_Glass_Pane               15
  161  Acacia_Leaves      0
  161  Dark_Oak_Leaves    1
  162  Acacia_Wood           0
  162  Dark_Oak_Wood         1
  163  Acacia_Wood_Stairs
  164  Dark_Oak_Wood_Stairs
  165 Slime_Block
  166 Barrier
  167  Iron_Trapdoor
  168  Prismarine       0
  168  Prismarine_Bricks       1
  168  Dark_Prismarine       2
  169  Sea_Lantern
  170  Hay_Block                          
  171  White_Carpet               0        
  171  Orange_Carpet             1
  171  Magenta_Carpet             2
  171  Light_Blue_Carpet         3
  171  Yellow_Carpet             4
  171  Lime_Carpet                5
  171  Pink_Carpet                6
  171  Gray_Carpet              7
  171  Light_Carpet         8
  171  Cyan_Carpet                9
  171  Purple_Carpet              10
  171  Blue_Carpet                11
  171  Brown_Carpet               12
  171  Green_Carpet               13
  171  Red_Carpet                 14
  171  Black_Carpet               15                           
  172 Hardened_Clay                      
  173  Block_of_Coal 
  174 Packed_Ice
  175  Large_Flowers
  176  Free-Standing_Banner
  177  Wall_Banner
  178 Inverted_Daylight_Sensor
  179 Red_Sandstone                0
  179 Smooth_Red_Sandstone         1
  179 Chiseled_Red_Sandstone       2
  180 Red_Sandstone_Stairs
  181 Double_Red_Sandstone_Slab
  182 Red_Sandstone_Slab
  183 Spruce_Fence_Gate
  184 Birch_Fence_Gate
  185 Jungle_Fence_Gate
  186 Dark_Oak_Fence_Gate
  187 Acacia_Fence_Gate
  188 Spruce_Fence
  189 Birch_Fence
  190 Jungle_Fence
  191 Dark_Oak_Fence
  192 Acacia_Fence
  193 Spruce_Door_Block
  194 Birch_Door_Block
  195 Jungle_Door_Block
  196 Dark_Oak_Door_Block
  197 Acacia_Door_Block


#            Items
# ID  NAME                   DAMAGE     STACKSIZE
 minecraft:iron_shovel  Iron_Shovel            +250       x1
 minecraft:iron_pickaxe  Iron_Pickaxe           +250       x1
 minecraft:iron_axe  Iron_Axe               +250       x1
 minecraft:flint_and_steel  Flint_and_Steel        +64        x1
 minecraft:apple  Apple                  
 minecraft:bow  Bow                    +384
 minecraft:arrow  Arrow                  
 minecraft:coal  Coal                   0
 minecraft:charcoal  Charcoal               1
 minecraft:diamond  Diamond                
 minecraft:iron_ingot  Iron_Ingot              
 minecraft:gold_ingot  Gold_Ingot               
 minecraft:iron_sword  Iron_Sword             +250       x1
 minecraft:wooden_sword  Wooden_Sword           +59        x1
 minecraft:wooden_shovel  Wooden_Shovel          +59        x1
 minecraft:wooden_pickaxe  Wooden_Pickaxe         +59        x1
 minecraft:wooden_axe  Wooden_Axe             +59        x1
 minecraft:stone_sword  Stone_Sword            +131       x1
 minecraft:stone_shovel  Stone_Shovel           +131       x1
 minecraft:stone_pickaxe  Stone_Pickaxe          +131       x1
 minecraft:stone_axe  Stone_Axe              +131       x1
 minecraft:diamond_sword  Diamond_Sword          +1561      x1
 minecraft:diamond_shovel  Diamond_Shovel         +1561      x1
 minecraft:diamond_pickaxe  Diamond_Pickaxe        +1561      x1
 minecraft:diamond_axe  Diamond_Axe            +1561      x1
 minecraft:stick  Stick                   
 minecraft:bowl  Bowl                              x16
 minecraft:mushroom_stew  Mushroom_Stew          
 minecraft:golden_sword  Golden_Sword           +32        x1
 minecraft:golden_shovel  Golden_Shovel          +32        x1
 minecraft:golden_pickaxe  Golden_Pickaxe         +32        x1
 minecraft:golden_axe  Golden_Axe             +32        x1
 minecraft:string  String                 
 minecraft:feather  Feather                  
 minecraft:gunpowder  Gunpowder                
 minecraft:wooden_hoe  Wooden_Hoe             +59        x1
 minecraft:stone_hoe  Stone_Hoe              +131       x1
 minecraft:iron_hoe  Iron_Hoe               +250       x1
 minecraft:diamond_hoe  Diamond_Hoe            +1561      x1
 minecraft:golden_hoe  Golden_Hoe             +32        x1
 minecraft:wheat_seeds  Seeds                   
 minecraft:wheat  Wheat                   
 minecraft:bread  Bread                    
 minecraft:leather_helmet  Leather_Cap            +34
 minecraft:leather_chestplate  Leather_Tunic          +48
 minecraft:leather_leggings  Leather_Pants          +46
 minecraft:leather_boots  Leather_Boots          +40
 minecraft:chainmail_helmet  Chainmail_Helmet       +68
 minecraft:chainmail_chestplate  Chainmail_Chestplate   +96
 minecraft:chainmail_leggings  Chainmail_Leggings     +92
 minecraft:chainmail_boots  Chainmail_Boots        +80
 minecraft:iron_helmet  Iron_Helmet            +136
 minecraft:iron_chestplate  Iron_Chestplate        +192
 minecraft:iron_leggings  Iron_Leggings          +184
 minecraft:iron_boots  Iron_Boots             +160
 minecraft:diamond_helmet  Diamond_Helmet         +272
 minecraft:diamond_chestplate  Diamond_Chestplate     +384
 minecraft:diamond_leggings  Diamond_Leggings       +368
 minecraft:diamond_boots  Diamond_Boots          +320
 minecraft:golden_helmet  Golden_Helmet          +68
 minecraft:golden_chestplate  Golden_Chestplate      +96
 minecraft:golden_leggings  Golden_Leggings        +92
 minecraft:golden_boots  Golden_Boots           +80
 minecraft:flint  Flint                   
 minecraft:porkchop  Raw_Porkchop             
 minecraft:cooked_porkchop  Cooked_Porkchop          
 minecraft:painting  Painting                 
 minecraft:golden_apple  Golden_Apple           0
 minecraft:golden_apple  Enchanted_Golden_Apple     1
 minecraft:sign  Sign                              x16
 minecraft:wooden_door  Wooden_Door                       
 minecraft:bucket  Bucket                            x16
 minecraft:water_bucket  Water_Bucket                      x1
 minecraft:lava_bucket  Lava_Bucket                       x1
 minecraft:minecart  Minecart                          x1
 minecraft:saddle  Saddle                            x1
 minecraft:iron_door  Iron_Door                         x1
 minecraft:redstone  Redstone                  
 minecraft:snowball  Snowball                          x16
 minecraft:boat  Boat                              x1
 minecraft:leather  Leather                   
 minecraft:milk_bucket  Milk_Bucket                       x1
 minecraft:brick  Brick                    
 minecraft:clay_ball  Clay                              x16
 minecraft:reeds  Sugar_Canes              
 minecraft:paper  Paper                    
 minecraft:book  Book                     
 minecraft:slimeball  Slimeball                
 minecraft:chest_minecart  Minecart_with_Chest               x1
 minecraft:furnace_minecart  Minecart_with_Furnace             x1
 minecraft:egg  Egg                       
 minecraft:compass  Compass                           x1
 minecraft:fishing_rod  Fishing_Rod                       x1
 minecraft:clock  Clock                             x1
 minecraft:glowstone_dust  Glowstone_Dust            
 minecraft:fish  Raw_Fish                          0
 minecraft:fish  Raw_Salmon                        1
 minecraft:fish  Clownfish                         2
 minecraft:fish  Pufferfish                        3
 minecraft:cooked_fish  Cooked_Fish                       0
 minecraft:cooked_fish  Cooked_Salmon                     1
 minecraft:cooked_fished  Cooked_Fish                       0
 minecraft:cooked_fished  Cooked_Salmon                     1
 minecraft:dye  Ink_Sack                 0
 minecraft:dye  Rose_Red                 1
 minecraft:dye  Cactus_Green             2
 minecraft:dye  Cocoa_Beans              3
 minecraft:dye  Lapis_Lazuli             4
 minecraft:dye  Purple_Dye               5
 minecraft:dye  Cyan_Dye                 6
 minecraft:dye  Light_Gray_Dye           7
 minecraft:dye  Gray_Dye                 8
 minecraft:dye  Pink_Dye                 9
 minecraft:dye  Lime_Dye                 10
 minecraft:dye  Dandelion_Yellow         11
 minecraft:dye  Light_Blue_Dye           12
 minecraft:dye  Magenta_Dye              13
 minecraft:dye  Orange_Dye               14
 minecraft:dye  Bone_Meal                15
 minecraft:bone  Bone                     
 minecraft:sugar  Sugar                    
 minecraft:cake  Cake                              x1
 minecraft:bed  Bed                               x1
 minecraft:repeater  Redstone_Repeater       
 minecraft:cookie  Cookie                  
 minecraft:filled_map  Map                              x1
 minecraft:shears  Shears                   +238
 minecraft:melon  Melon                    
 minecraft:pumpkin_seeds  Pumpkin_Seeds            
 minecraft:melon_seeds  Melon_Seeds              
 minecraft:beef  Raw_Beef                 
 minecraft:cooked_beef  Steak                    
 minecraft:chicken  Raw_Chicken              
 minecraft:cooked_chicken  Cooked_Chicken           
 minecraft:rotten_flesh  Rotten_Flesh             
 minecraft:ender_pearl  Ender_Pearl                       x16
 minecraft:blaze_rod  Blaze_Rod                
 minecraft:ghast_tear  Ghast_Tear               
 minecraft:gold_nugget  Gold_Nugget              
 minecraft:nether_wart  Nether_Wart            
 minecraft:glass_bottle  Glass_Bottle                      x3
 minecraft:spider_eye  Spider_Eye               
 minecraft:fermented_spider_eye  Fermented_Spider_Eye     
 minecraft:blaze_powder  Blaze_Powder             
 minecraft:magma_cream  Magma_Cream              
 minecraft:brewing_stand  Brewing_Stand                     x1
 minecraft:cauldron  Cauldron                          x1
 minecraft:ender_eye  Eye_of_Ender             
 minecraft:speckled_melon  Glistering_Melon         
 minecraft:experience_bottle  Bottle_o'_Enchanting     
 minecraft:fire_charge  Fire_Charge              
 minecraft:writable_book  Book_and_Quill                    x1
 minecraft:written_book  Written_Book                      x1
 minecraft:emerald  Emerald                  
 minecraft:item_frame  Item_Frame               
 minecraft:flower_pot  Flower_Pot               
 minecraft:carrot  Carrot                   
 minecraft:potato  Potato                   
 minecraft:baked_potato  Baked_Potato             
 minecraft:poisonous_potato  Poisonous_Potato         
 minecraft:map  Empty_Map                         x1
 minecraft:golden_carrot  Golden_Carrot            
 minecraft:skull  Skeleton_Head            0
 minecraft:skull  Wither_Skeleton_Head     1
 minecraft:skull  Zombie_Head              2
 minecraft:skull  Human_Head               3
 minecraft:skull  Creeper_Head             4
 minecraft:carrot_on_a_stick  Carrot_on_a_Stick        +25
 minecraft:nether_star  Nether_Star              
 minecraft:pumpkin_pie  Pumpkin_Pie              
 minecraft:fireworks  Firework_Rocket          
 minecraft:firework_charge  Firework_Star            
 minecraft:enchanted_book  Enchanted_Book           
 minecraft:comparator  Redstone_Comparator      
 minecraft:netherbrick  Nether_Brick             
 minecraft:quartz  Nether_Quartz            
 minecraft:tnt_minecart  Minecart_with_TNT        x1
 minecraft:hopper_minecart  Minecart_with_Hopper     x1
 minecraft:prismarine_shard  Prismarine_Shard
 minecraft:prismarine_crystals  Prismarine_Crystals
 minecraft:rabbit  Raw_Rabbit
 minecraft:cooked_rabbit  Cooked_Rabbit
 minecraft:rabbit_stew  Rabbit_Stew
 minecraft:rabbit_foot  Rabbit's_Foot
 minecraft:rabbit_hide  Rabbit_Hide
 minecraft:armor_stand  Armor_Stand
 minecraft:iron_horse_armor  Iron_Horse_Armor         x1
 minecraft:gold_horse_armor  Gold_Horse_Armor         x1
 minecraft:diamond_horse_armor  Diamond_Horse_Armor      x1
 minecraft:lead  Lead                     
 minecraft:name_tag  Name_Tag
 minecraft:command_block_minecart  Minecart_with_Command_Block    x1
 minecraft:mutton  Raw_Mutton
 minecraft:cooked_mutton  Cooked_Mutton
 minecraft:banner  Black_Banner          0
 minecraft:banner  Red_Banner            1
 minecraft:banner  Green_Banner          2
 minecraft:banner  Brown_Banner          3
 minecraft:banner  Blue_Banner           4
 minecraft:banner  Purple_Banner         5
 minecraft:banner  Cyan_Banner           6
 minecraft:banner  Light_Gray_Banner     7
 minecraft:banner  Gray_Banner           8
 minecraft:banner  Pink_Banner           9
 minecraft:banner  Lime_Banner           10
 minecraft:banner  Yellow_Banner         11
 minecraft:banner  Light_Blue_Banner     12
 minecraft:banner  Magenta_Banner        13
 minecraft:banner  Orange_Banner         14
 minecraft:banner  White_Banner          15
 minecraft:spruce_door  Spruce_Door
 minecraft:birch_door  Birch_Door
 minecraft:jungle_door  Jungle_Door
 minecraft:acacia_door  Acacia_Door
 minecraft:dark_oak_door  Dark_Oak_Door
 
 
#            Legacy item entries
# ID  NAME                   DAMAGE     STACKSIZE
 256  Iron_Shovel            +250       x1
 257  Iron_Pickaxe           +250       x1
 258  Iron_Axe               +250       x1
 259  Flint_and_Steel        +64        x1
 260  Apple                  
 261  Bow                    +384
 262  Arrow                  
 263  Coal                   0
 263  Charcoal               1
 264  Diamond                
 265  Iron_Ingot              
 266  Gold_Ingot               
 267  Iron_Sword             +250       x1
 268  Wooden_Sword           +59        x1
 269  Wooden_Shovel          +59        x1
 270  Wooden_Pickaxe         +59        x1
 271  Wooden_Axe             +59        x1
 272  Stone_Sword            +131       x1
 273  Stone_Shovel           +131       x1
 274  Stone_Pickaxe          +131       x1
 275  Stone_Axe              +131       x1
 276  Diamond_Sword          +1561      x1
 277  Diamond_Shovel         +1561      x1
 278  Diamond_Pickaxe        +1561      x1
 279  Diamond_Axe            +1561      x1
 280  Stick                   
 281  Bowl                              x16
 282  Mushroom_Stew          
 283  Golden_Sword           +32        x1
 284  Golden_Shovel          +32        x1
 285  Golden_Pickaxe         +32        x1
 286  Golden_Axe             +32        x1
 287  String                 
 288  Feather                  
 289  Gunpowder                
 290  Wooden_Hoe             +59        x1
 291  Stone_Hoe              +131       x1
 292  Iron_Hoe               +250       x1
 293  Diamond_Hoe            +1561      x1
 294  Golden_Hoe             +32        x1
 295  Seeds                   
 296  Wheat                   
 297  Bread                    
 298  Leather_Cap            +34
 299  Leather_Tunic          +48
 300  Leather_Pants          +46
 301  Leather_Boots          +40
 302  Chainmail_Helmet       +68
 303  Chainmail_Chestplate   +96
 304  Chainmail_Leggings     +92
 305  Chainmail_Boots        +80
 306  Iron_Helmet            +136
 307  Iron_Chestplate        +192
 308  Iron_Leggings          +184
 309  Iron_Boots             +160
 310  Diamond_Helmet         +272
 311  Diamond_Chestplate     +384
 312  Diamond_Leggings       +368
 313  Diamond_Boots          +320
 314  Golden_Helmet          +68
 315  Golden_Chestplate      +96
 316  Golden_Leggings        +92
 317  Golden_Boots           +80
 318  Flint                   
 319  Raw_Porkchop             
 320  Cooked_Porkchop          
 321  Painting                 
 322  Golden_Apple           0
 322  Enchanted_Golden_Apple     1
 323  Sign                              x16
 324  Wooden_Door                       
 325  Bucket                            x16
 326  Water_Bucket                      x1
 327  Lava_Bucket                       x1
 328  Minecart                          x1
 329  Saddle                            x1
 330  Iron_Door                         x1
 331  Redstone                  
 332  Snowball                          x16
 333  Boat                              x1
 334  Leather                   
 335  Milk_Bucket                       x1
 336  Brick                    
 337  Clay                              x16
 338  Sugar_Canes              
 339  Paper                    
 340  Book                     
 341  Slimeball                
 342  Minecart_with_Chest               x1
 343  Minecart_with_Furnace             x1
 344  Egg                       
 345  Compass                           x1
 346  Fishing_Rod                       x1
 347  Clock                             x1
 348  Glowstone_Dust            
 349  Raw_Fish                          0
 349  Raw_Salmon                        1
 349  Clownfish                         2
 349  Pufferfish                        3
 350  Cooked_Fish                       0
 350  Cooked_Salmon                     1
 351  Ink_Sack                 0
 351  Rose_Red                 1
 351  Cactus_Green             2
 351  Cocoa_Beans              3
 351  Lapis_Lazuli             4
 351  Purple_Dye               5
 351  Cyan_Dye                 6
 351  Light_Gray_Dye           7
 351  Gray_Dye                 8
 351  Pink_Dye                 9
 351  Lime_Dye                 10
 351  Dandelion_Yellow         11
 351  Light_Blue_Dye           12
 351  Magenta_Dye              13
 351  Orange_Dye               14
 351  Bone_Meal                15
 352  Bone                     
 353  Sugar                    
 354  Cake                              x1
 355  Bed                               x1
 356  Redstone_Repeater       
 357  Cookie                  
 358  Map                               x1
 359  Shears                   +238
 360  Melon                    
 361  Pumpkin_Seeds            
 362  Melon_Seeds              
 363  Raw_Beef                 
 364  Steak                    
 365  Raw_Chicken              
 366  Cooked_Chicken           
 367  Rotten_Flesh             
 368  Ender_Pearl                       x16
 369  Blaze_Rod                
 370  Ghast_Tear               
 371  Gold_Nugget              
 372  Nether_Wart             
 373  Potion                            x1
 374  Glass_Bottle                      x3
 375  Spider_Eye               
 376  Fermented_Spider_Eye     
 377  Blaze_Powder             
 378  Magma_Cream              
 379  Brewing_Stand                     x1
 380  Cauldron                          x1
 381  Eye_of_Ender             
 382  Glistering_Melon         
 383  Spawn_Egg                
 384  Bottle_o'_Enchanting     
 385  Fire_Charge              
 386  Book_and_Quill                    x1
 387  Written_Book                      x1
 388  Emerald                  
 389  Item_Frame               
 390  Flower_Pot               
 391  Carrot                   
 392  Potato                   
 393  Baked_Potato             
 394  Poisonous_Potato         
 395  Empty_Map                         x1
 396  Golden_Carrot            
 397  Skeleton_Head            0
 397  Wither_Skeleton_Head     1
 397  Zombie_Head              2
 397  Human_Head               3
 397  Creeper_Head             4
 398  Carrot_on_a_Stick        +25
 399  Nether_Star              
 400  Pumpkin_Pie              
 401  Firework_Rocket          
 402  Firework_Star            
 403  Enchanted_Book           
 404  Redstone_Comparator      
 405  Nether_Brick             
 406  Nether_Quartz            
 407  Minecart_with_TNT        x1
 408  Minecart_with_Hopper     x1
 409  Prismarine_Shard
 410  Prismarine_Crystals
 411  Raw_Rabbit
 412  Cooked_Rabbit
 413  Rabbit_Stew
 414  Rabbit's_Foot
 415  Rabbit_Hide
 416  Armor_Stand
 417  Iron_Horse_Armor         x1
 418  Gold_Horse_Armor         x1
 419  Diamond_Horse_Armor      x1
 420  Lead                     
 421  Name_Tag
 422  Minecart_with_Command_Block    x1
 423  Raw_Mutton
 424  Cooked_Mutton
 425  Black_Banner          0
 425  Red_Banner            1
 425  Green_Banner          2
 425  Brown_Banner          3
 425  Blue_Banner           4
 425  Purple_Banner         5
 425  Cyan_Banner           6
 425  Light_Gray_Banner     7
 425  Gray_Banner           8
 425  Pink_Banner           9
 425  Lime_Banner           10
 425  Yellow_Banner         11
 425  Light_Blue_Banner     12
 425  Magenta_Banner        13
 425  Orange_Banner         14
 425  White_Banner          15
 427  Spruce_Door
 428  Birch_Door
 429  Jungle_Door
 430  Acacia_Door
 431  Dark_Oak_Door
 
#            Record entries
# ID  NAME                   DAMAGE     STACKSIZE
minecraft:record_13  C418_-_13                         x1
minecraft:record_cat  C418_-_cat                        x1
minecraft:record_blocks  C418_-_blocks                     x1
minecraft:record_chirp  C418_-_chirp                      x1
minecraft:record_far  C418_-_far                        x1
minecraft:record_mall  C418_-_mall                       x1
minecraft:record_mellohi  C418_-_mellohi                    x1
minecraft:record_stal  C418_-_stal                       x1
minecraft:record_strad  C418_-_strad                      x1
minecraft:record_ward  C418_-_ward                       x1
minecraft:record_11  C418_-_11                         x1
minecraft:record_wait  C418_-_wait                       x1

#            Legacy record entries
# ID  NAME                   DAMAGE     STACKSIZE
2256  C418_-_13                         x1
2257  C418_-_cat                        x1
2258  C418_-_blocks                     x1
2259  C418_-_chirp                      x1
2260  C418_-_far                        x1
2261  C418_-_mall                       x1
2262  C418_-_mellohi                    x1
2263  C418_-_stal                       x1
2264  C418_-_strad                      x1
2265  C418_-_ward                       x1
2266  C418_-_11                         x1
2267  C418_-_wait                       x1

#           Potions
# ID  NAME                             DAMAGE
 minecraft:potion  Water_Bottle                     0
 minecraft:potion  Awkward_Potion                   16
 minecraft:potion  Thick_Potion                     32
 minecraft:potion  Mundane_Potion                   64
 minecraft:potion  Mundane_Potion                   8192
 minecraft:potion  Regeneration_Potion_(0:45)       8193
 minecraft:potion  Swiftness_Potion_(3:00)          8194
 minecraft:potion  Fire_Resistance_Potion_(3:00)    8195
 minecraft:potion  Poison_Potion_(0:45)             8196
 minecraft:potion  Healing_Potion                   8197
 minecraft:potion  Night_Vision_Potion_(3:00)       8198
 minecraft:potion  Weakness_Potion_(1:30)           8200
 minecraft:potion  Strength_Potion_(3:00)           8201
 minecraft:potion  Slowness_Potion_(1:30)           8202
 minecraft:potion  Harming_Potion                   8204
 minecraft:potion  Water_Breathing_Potion_(3:00)    8205
 minecraft:potion  Invisibility_Potion_(3:00)       8206
 minecraft:potion  Regeneration_Potion_II_(0:22)    8225
 minecraft:potion  Swiftness_Potion_II_(1:30)       8226
 minecraft:potion  Poison_Potion_II_(0:22)          8228
 minecraft:potion  Healing_Potion_II                8229
 minecraft:potion  Strength_Potion_II_(1:30)        8233
 minecraft:potion  Leaping_Potion_II_(1:30)         8235
 minecraft:potion  Harming_Potion_II                8236
 minecraft:potion  Regeneration_Potion_(2:00)       8257
 minecraft:potion  Swiftness_Potion_(8:00)          8258
 minecraft:potion  Fire_Resistance_Potion_(8:00)    8259
 minecraft:potion  Poison_Potion_(2:00)             8260
 minecraft:potion  Night_Vision_Potion_(8:00)       8262
 minecraft:potion  Weakness_Potion_(4:00)           8264 
 minecraft:potion  Strength_Potion_(8:00)           8265
 minecraft:potion  Slowness_Potion_(1:30)           8266
 minecraft:potion  Leaping_Potion_(3:00)            8267
 minecraft:potion  Water_Breathing_Potion_(8:00)    8269
 minecraft:potion  Invisibility_Potion_(8:00)       8270
 minecraft:potion  Regeneration_Potion_II_(1:00)    8289 
 minecraft:potion  Swiftness_Potion_II_(4:00)       8290 
 minecraft:potion  Poison_Potion_II_(1:00)          8292 
 minecraft:potion  Strength_Potion_II_(4:00)        8297

#           Splash Potions
# ID  NAME                      DAMAGE
 minecraft:potion  Mundane_Splash                   16384
 minecraft:potion  Regeneration_Splash_(0:33)       16385
 minecraft:potion  Swiftness_Splash_(2:15)          16386 
 minecraft:potion  Fire_Resistance_Splash_(2:15)    16387 
 minecraft:potion  Poison_Splash_(0:33)             16388 
 minecraft:potion  Healing_Splash                   16389
 minecraft:potion  Night_Vision_Splash_(2:15)       16390
 minecraft:potion  Weakness_Splash_(1:07)           16392
 minecraft:potion  Strength_Splash_(2:15)           16393
 minecraft:potion  Slowness_Splash_(1:07)           16394
 minecraft:potion  Harming_Splash                   16396
 minecraft:potion  Breathing_Splash_(2:15)          16397
 minecraft:potion  Invisibility_Splash_(2:15)       16398
 minecraft:potion  Regeneration_Splash_II_(0:16)    16417
 minecraft:potion  Swiftness_Splash_II_(1:07)       16418
 minecraft:potion  Poison_Splash_II_(0:16)          16420
 minecraft:potion  Healing_Splash_II                16421
 minecraft:potion  Strength_Splash_II_(1:07)        16425
 minecraft:potion  Leaping_Splash_II_(1:07)         16427
 minecraft:potion  Harming_Splash_II                16428
 minecraft:potion  Regeneration_Splash_(1:30)       16449
 minecraft:potion  Swiftness_Splash_(6:00)          16450
 minecraft:potion  Fire_Resistance_Splash_(6:00)    16451
 minecraft:potion  Poison_Splash_(1:30)             16452
 minecraft:potion  Night_Vision_Splash_(6:00)       16454
 minecraft:potion  Weakness_Splash_(3:00)           16456
 minecraft:potion  Strength_Splash_(6:00)           16457
 minecraft:potion  Slowness_Splash_(3:00)           16458
 minecraft:potion  Leaping_Splash_(2:15)            16459
 minecraft:potion  Water_Breathing_Splash_(6:00)    16461
 minecraft:potion  Invisibility_Splash_(6:00)       16462
 minecraft:potion  Regeneration_Splash_II_(0:45)    16481
 minecraft:potion  Swiftness_Splash_II_(3:00)       16482 
 minecraft:potion  Poison_Splash_II_(0:45)          16484 
 minecraft:potion  Strength_Splash_II_(3:00)        16489
 
#           Legacy Potions
# ID  NAME                             DAMAGE
 373  Water_Bottle                     0
 373  Awkward_Potion                   16
 373  Thick_Potion                     32
 373  Mundane_Potion                   64
 373  Mundane_Potion                   8192
 373  Regeneration_Potion_(0:45)       8193
 373  Swiftness_Potion_(3:00)          8194
 373  Fire_Resistance_Potion_(3:00)    8195
 373  Poison_Potion_(0:45)             8196
 373  Healing_Potion                   8197
 373  Night_Vision_Potion_(3:00)       8198
 373  Weakness_Potion_(1:30)           8200
 373  Strength_Potion_(3:00)           8201
 373  Slowness_Potion_(1:30)           8202
 373  Harming_Potion                   8204
 373  Water_Breathing_Potion_(3:00)    8205
 373  Invisibility_Potion_(3:00)       8206
 373  Regeneration_Potion_II_(0:22)    8225
 373  Swiftness_Potion_II_(1:30)       8226
 373  Poison_Potion_II_(0:22)          8228
 373  Healing_Potion_II                8229
 373  Strength_Potion_II_(1:30)        8233
 373  Leaping_Potion_II_(1:30)         8235
 373  Harming_Potion_II                8236
 373  Regeneration_Potion_(2:00)       8257
 373  Swiftness_Potion_(8:00)          8258
 373  Fire_Resistance_Potion_(8:00)    8259
 373  Poison_Potion_(2:00)             8260
 373  Night_Vision_Potion_(8:00)       8262
 373  Weakness_Potion_(4:00)           8264 
 373  Strength_Potion_(8:00)           8265
 373  Slowness_Potion_(1:30)           8266
 373  Leaping_Potion_(3:00)            8267
 373  Water_Breathing_Potion_(8:00)    8269
 373  Invisibility_Potion_(8:00)       8270
 373  Regeneration_Potion_II_(1:00)    8289 
 373  Swiftness_Potion_II_(4:00)       8290 
 373  Poison_Potion_II_(1:00)          8292 
 373  Strength_Potion_II_(4:00)        8297

#           Legacy Splash Potions
# ID  NAME                      DAMAGE
 373  Mundane_Splash                   16384
 373  Regeneration_Splash_(0:33)       16385
 373  Swiftness_Splash_(2:15)          16386 
 373  Fire_Resistance_Splash_(2:15)    16387 
 373  Poison_Splash_(0:33)             16388 
 373  Healing_Splash                   16389
 373  Night_Vision_Splash_(2:15)       16390
 373  Weakness_Splash_(1:07)           16392
 373  Strength_Splash_(2:15)           16393
 373  Slowness_Splash_(1:07)           16394
 373  Harming_Splash                   16396
 373  Breathing_Splash_(2:15)          16397
 373  Invisibility_Splash_(2:15)       16398
 373  Regeneration_Splash_II_(0:16)    16417
 373  Swiftness_Splash_II_(1:07)       16418
 373  Poison_Splash_II_(0:16)          16420
 373  Healing_Splash_II                16421
 373  Strength_Splash_II_(1:07)        16425
 373  Leaping_Splash_II_(1:07)         16427
 373  Harming_Splash_II                16428
 373  Regeneration_Splash_(1:30)       16449
 373  Swiftness_Splash_(6:00)          16450
 373  Fire_Resistance_Splash_(6:00)    16451
 373  Poison_Splash_(1:30)             16452
 373  Night_Vision_Splash_(6:00)       16454
 373  Weakness_Splash_(3:00)           16456
 373  Strength_Splash_(6:00)           16457
 373  Slowness_Splash_(3:00)           16458
 373  Leaping_Splash_(2:15)            16459
 373  Water_Breathing_Splash_(6:00)    16461
 373  Invisibility_Splash_(6:00)       16462
 373  Regeneration_Splash_II_(0:45)    16481
 373  Swiftness_Splash_II_(3:00)       16482 
 373  Poison_Splash_II_(0:45)          16484 
 373  Strength_Splash_II_(3:00)        16489

#           Spawn Eggs
# ID  NAME                      DAMAGE
 minecraft:spawn_egg  Spawn_Egg_(Creeper)             50
 minecraft:spawn_egg  Spawn_Egg_(Skeleton)            51
 minecraft:spawn_egg  Spawn_Egg_(Spider)              52
 minecraft:spawn_egg  Spawn_Egg_(Zombie)              54
 minecraft:spawn_egg  Spawn_Egg_(Slime)               55
 minecraft:spawn_egg  Spawn_Egg_(Ghast)               56
 minecraft:spawn_egg  Spawn_Egg_(Zombie_Pigmen)       57
 minecraft:spawn_egg  Spawn_Egg_(Enderman)            58
 minecraft:spawn_egg  Spawn_Egg_(Cave_Spider)         59
 minecraft:spawn_egg  Spawn_Egg_(Silverfish)          60
 minecraft:spawn_egg  Spawn_Egg_(Blaze)               61
 minecraft:spawn_egg  Spawn_Egg_(Magma_Cube)          62
 minecraft:spawn_egg  Spawn_Egg_(Bat)                 65
 minecraft:spawn_egg  Spawn_Egg_(Witch)               66
 minecraft:spawn_egg  Spawn_Egg_(Endermite)           67
 minecraft:spawn_egg  Spawn_Egg_(Guardian)            68
 minecraft:spawn_egg  Spawn_Egg_(Pig)                 90
 minecraft:spawn_egg  Spawn_Egg_(Sheep)               91
 minecraft:spawn_egg  Spawn_Egg_(Cow)                 92
 minecraft:spawn_egg  Spawn_Egg_(Chicken)             93
 minecraft:spawn_egg  Spawn_Egg_(Squid)               94
 minecraft:spawn_egg  Spawn_Egg_(Wolf)                95
 minecraft:spawn_egg  Spawn_Egg_(Mooshroom)           96
 minecraft:spawn_egg  Spawn_Egg_(Ocelot)              98
 minecraft:spawn_egg  Spawn_Egg_(Horse)               100
 minecraft:spawn_egg  Spawn_Egg_(Rabbit)              101
 minecraft:spawn_egg  Spawn_Egg_(Villager)            120
 
 #        Legacy Spawn Eggs
# ID  NAME                      DAMAGE
 383  Spawn_Egg_(Creeper)             50
 383  Spawn_Egg_(Skeleton)            51
 383  Spawn_Egg_(Spider)              52
 383  Spawn_Egg_(Zombie)              54
 383  Spawn_Egg_(Slime)               55
 383  Spawn_Egg_(Ghast)               56
 383  Spawn_Egg_(Zombie_Pigmen)       57
 383  Spawn_Egg_(Enderman)            58
 383  Spawn_Egg_(Cave_Spider)         59
 383  Spawn_Egg_(Silverfish)          60
 383  Spawn_Egg_(Blaze)               61
 383  Spawn_Egg_(Magma_Cube)          62
 383  Spawn_Egg_(Bat)                 65
 383  Spawn_Egg_(Witch)               66
 383  Spawn_Egg_(Endermite)           67
 383  Spawn_Egg_(Guardian)            68
 383  Spawn_Egg_(Pig)                 90
 383  Spawn_Egg_(Sheep)               91
 383  Spawn_Egg_(Cow)                 92
 383  Spawn_Egg_(Chicken)             93
 383  Spawn_Egg_(Squid)               94
 383  Spawn_Egg_(Wolf)                95
 383  Spawn_Egg_(Mooshroom)           96
 383  Spawn_Egg_(Ocelot)              98
 383  Spawn_Egg_(Horse)               100
 383  Spawn_Egg_(Rabbit)              101
 383  Spawn_Egg_(Villager)            120

#           Groups       #Out of date
# NAME      ICON  ITEMS
# Column 1
~ Natural    2     2,3,12,24,128,44~1,13,82,79,80,78
~ Stone      1     1,4,48,67,44~3,139,140,98,109,44~5,44~0,45,108,44~4,101
~ Wood       5     17,5,53,134,135,136,126,47,85,107,20,102,30
~ NetherEnd  87    87,88,89,348,112,114,113,372,121,122
~ Ores       56    16,15,14,56,129,73,21,49,42,41,57,133,22,263~0,265,266,264,388
~ Special    54    46,52,58,54,130,61,23,25,84,116,379,380,138,146~0,321,389,323,324,330,355,65,96,390,397
~ Plants1    81    31~1,31~2,106,111,18,81,86,91,103,110
~ Plants2    6     295,361,362,6,296,338,37,38,39,40,32
~ Transport  328   66,27,28,328,342,343,333,329,398
~ Logic      331   331,76,356,69,70,72,131,77,144,33,29,123,137
~ Wool       35    35~0,35~8,35~7,35~15,35~14,35~12,35~1,35~4,35~5,35~13,35~11,35~3,35~9,35~10,35~2,35~6
~ Dye        351   351~15,351~7,351~8,351~0,351~1,351~3,351~14,351~11,351~10,351~2,351~4,351~12,351~6,351~5,351~13,351~9
# Column 2
~ TierWood   299   298,299,300,301,269,270,271,290,268
~ TierStone  303   302,303,304,305,273,274,275,291,272
~ TierIron   307   306,307,308,309,256,257,258,292,267
~ TierDiam   311   310,311,312,313,277,278,279,293,276
~ TierGold   315   314,315,316,317,284,285,286,294,283
~ Tools      261   50,261,262,259,346,359,345,347,395,358,325,326,327,335,384,385,386,387
~ Food       297   260,322,282,297,360,319,320,363,364,365,366,349,350,354,357,391,396,392,393,394,400
~ Items      318   280,281,318,337,336,353,339,340,332,376,377,382,381
~ Drops      341   344,288,334,287,352,289,367,375,341,368,369,370,371,378,399
~ Music      2257  2256,2257,2258,2259,2260,2261,2262,2263,2264,2265,2266,2267
~ Potion     373   373~0,373~16,373~32,373~8192,373~8193,373~8257,373~8225,373~8289,373~8194,373~8258,373~8226,373~8290,373~8195,373~8259,373~8197,373~8229,373~8201,373~8265,373~8233,373~8297,373~8196,373~8260,373~8228,373~8292,373~8200,373~8264,373~8202,373~8266,373~8204,373~8236,373~8198,373~8262,373~8206,373~8270,373~16384,373~16385,373~16499,373~16417,373~16481,373~16386,373~16450,373~16418,373~16482,373~16387,373~16451,373~16389,373~16421,373~16393,373~16457,373~16425,373~16489,373~16388,373~16452,373~16420,373~16484,373~16392,373~16456,373~16394,373~16458,373~16396,373~16428,373~16390,373~16454,373~16398,373~16462
~ Eggs       383   383~50,383~51,383~52,383~54,383~55,383~56,383~57,383~58,383~59,383~60,383~61,383~62,383~65,383~66,383~90,383~91,383~92,383~93,383~94,383~95,383~96,383~120

#            Enchantments
# EID  NAME                   MAX  ITEMS
+   0  Protection             4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   1  Fire_Protection        4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   2  Feather_Falling        4    301,305,309,313,317
+   3  Blast_Protection       4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   4  Projectile_Protection  4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   5  Respiration            3    298,302,306,310,314
+   6  Aqua_Affinity          1    298,302,306,310,314
+  16  Sharpness              5    268,272,267,276,283
+  17  Smite                  5    268,272,267,276,283
+  18  Bane_of_Arthropods     5    268,272,267,276,283
+  19  Knockback              2    268,272,267,276,283
+  20  Fire_Aspect            2    268,272,267,276,283
+  21  Looting                3    268,272,267,276,283
+  32  Efficiency             5    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  33  Silk_Touch             1    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  34  Unbreaking             3    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  35  Fortune                3    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  48  Power                  5    261
+  49  Punch                  2    261
+  50  Flame                  1    261
+  51  Infinity               1    261
"""


class ItemType(object):
    def __init__(self, id, name, maxdamage=0, damagevalue=0, stacksize=64):
        self.id = id
        self.name = name
        self.maxdamage = maxdamage
        self.damagevalue = damagevalue
        self.stacksize = stacksize

    def __repr__(self):
        return "ItemType({0}, '{1}')".format(self.id, self.name)

    def __str__(self):
        return "ItemType {0}: {1}".format(self.id, self.name)


class Items(object):
    items_txt = items_txt

    def __init__(self, filename=None):
        if filename is None:
            items_txt = self.items_txt
        else:
            try:
                with file(filename) as f:
                    items_txt = f.read()
            except Exception, e:
                logger.info("Error reading '%s': %s", filename, e)
                logger.info("Using internal data.")
                items_txt = self.items_txt

        self.itemtypes = {}
        self.itemgroups = []

        for line in items_txt.split("\n"):
            try:
                line = line.strip()
                if len(line) == 0:
                    continue
                if line[0] == "#":  # comment
                    continue
                if line[0] == "+":  # enchantment
                    continue
                if line[0] == "~":  # category
                    fields = line.split()
                    name, icon, items = fields[1:4]
                    items = items.split(",")
                    self.itemgroups.append((name, icon, items))
                    continue

                stacksize = 64
                damagevalue = None
                maxdamage = 0

                fields = line.split()
                if len(fields) >= 2:
                    maxdamage = None
                    id, name = fields[0:2]
                    if len(fields) > 2:
                        info = fields[2]
                        if info[0] == '(':
                            info = info[1:-1]
                        if info[0] == 'x':
                            stacksize = int(info[1:])
                        elif info[0] == '+':
                            maxdamage = int(info[1:])
                        else:
                            damagevalue = int(info)
                    # id = int(id)           #Removed for 1.8 compatibility, fields adjusted accordingly.
                    name = name.replace("_", " ")

                    self.itemtypes[(id, damagevalue)] = ItemType(id, name, maxdamage, damagevalue, stacksize)
            except Exception, e:
                print "Error reading line:", e
                print "Line: ", line
                print

        self.names = dict((item.name, item.id) for item in self.itemtypes.itervalues())

    def findItem(self, id=0, damage=None):
        item = self.itemtypes.get((id, damage))
        if item:
            return item

        item = self.itemtypes.get((id, None))
        if item:
            return item

        item = self.itemtypes.get((id, 0))
        if item:
            return item

        else:
            return ItemType(id, "Unknown Item {0}:{1}".format(id, damage), damagevalue=damage)
            # raise ItemNotFound, "Item {0}:{1} not found".format(id, damage)


class ItemNotFound(KeyError):
    pass


items = Items()
