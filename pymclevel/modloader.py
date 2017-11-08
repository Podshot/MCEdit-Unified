# mod_loader.py
#
# D.C.-G 2017
#
# Trying to load directly the mod data from the .jar.
# Mod used to create this module is Conquest Reforged (conquest_reforged_MOD_v.1.4.51.jar, loaded with Forge).
# Changes may/will be needed for other mod loading methods.
#
# TODO:
# * Change the print statements for log entries.
# * Enhance the data gathering in mod json file to get texture orientation.
# * Enhance the numeric IDs build.
# * Implement methods for data other than blocks, like block states and entities.
#
from __future__ import unicode_literals
import os
import zipfile
import json
import re
import math
import traceback
from PIL import Image
from cStringIO import StringIO
import nbt


class ModLoader(object):
    """Loads a mod packed in a .jar file and extract needed information in a
    directory named like the mod.
    The destination directory will contain .json definition files and a texture
    one usable by MCEdit."""
    def __init__(self, file_name, output_dir, block_ids={}, force=False):
        """Initialize the object.
        :file_name: string: Full path to the .jar file. Must exists!
        :output_dir: string: The directory where to create the mod content. Must exists!
        :block_ids: dict: If given, keys are block 'idStr' and values numeric IDs as found in the mod definition in 'level.dat'
            Defaults to an empty dict.
        :force: bool: Whether to force a mod extracted data to be overwritten.
            Defaults to False. ! ! NOT IMPLEMENTED ! !"""
        print "Loading mod", file_name
        self.file_name = file_name
        self.output_dir = output_dir
        self.block_ids = block_ids

        # Let define some useful data for forein class/method usage.
        self.mod_name = None
        # Full path to the mod directory where self.texture_file and json definitions are.
        # Will be set to self.output_dir + mod name later.
        self.mod_dir = None
        # Textures file name in self.mod_dir.
        # This file will be built using the ones found in the mod .jar.
        self.texture_file = None
        # mod_info: dict: built from mcmod.info, or using 'defaults'.
        self.mod_info = None
        # version: string: mod version.
        self.version = None
        # mcversion: string: game version for which the mod works.
        self.mcversion = None
        # modid: string: the mod internal ID
        self.modid = None
        # texture_catalog: dict: keys are texture names and values coordinates (in tiles) in texture_file.
        # Made to be compatible with MCEdit texture indexing system.
        self.texture_catalog = {}
        # notex_idx is a tuple containing the 'NOTEX' coordinates in texture_file
        self.notex_idx = (-1, -1)
        # __blocks: dict: contains the block definition found in the mod. Not compatible with MCEdit block handling.
        self.__blocks = {}
        # built_json: dict: data rebuilt to be compatible with MCEdit handling
        self.built_json = {}

        # Open the jar and finish the initialization.
        self.__archive = zipfile.ZipFile(file_name)
        self.__jar_content = self.__archive.namelist()
        self.__read_mod_info()
        self.__build_texture()
        self.__load_block_models()
        self.__save_json()
        self.__archive.close()


    def __read_mod_info(self):
        """Reads the .jar root directory to find the 'mcmod.info' json file.
        Read it and build self.mod_dir, self.mod_name, self.version and self.mcversion.
        Also set self.mod_info to the parsed json object.
        If 'mcmod.info' is not found, let try to guess..."""
        arch = self.__archive
        mod_info = {}
        if "mcmod.info" in self.__jar_content:
            data = arch.read("mcmod.info").strip("[").strip("]")
            # The dependecies are a list of unquoted words. Fix that!
            deps = re.search(r'^[ ]*?"dependencies"[ ]*?:[ ]*?\[.*?\]$', data, re.M)
            if deps:
                head, _deps = deps.group().split("[")
                _deps = [a.strip() for a in _deps.split("]")[0].split(",")]
                repl = head + '["' + '", "'.join(_deps) + '"]'
                data = data.replace(deps.group(), repl)
            try:
                mod_info = json.loads(data)
            except Exception as exc:
                print "Can't load mod info because:"
                traceback.print_exc()
        self.mod_info = mod_info
        # Let define some default values in mcmod.info don't contain them.
        mod_name = os.path.splitext(self.file_name)[0]
        self.mod_name = mod_info.get("name", mod_name)
        self.version = mod_info.get("version", mod_name)
        self.mcversion = mod_info.get("mcversion", "Unknown")
        self.modid = mod_info.get("modid", mod_name)
        # dir_name = self.mod_name
        dir_name = self.modid
        if self.version != mod_name:
            dir_name += "_%s" % self.version
        self.mod_dir = os.path.join(self.output_dir, dir_name)

        print "Mod info:"
        print "  * self.mod_name: ", self.mod_name
        print "  * self.vesrion:  ", self.version
        print "  * self.mcversion:", self.mcversion
        print "  * self.modid:    ", self.modid
        print "  * self.mod_dir:  ", self.mod_dir
        print "  * self.mod_info: ", self.mod_info


    def __build_texture(self):
        """Build a texture file from the one found in the mod."""

        def get_16x16_image(fp):
            """Load an image and resize it to 16*16 pixels.
            :fp: file object: opened file descriptor to read the image."""
            img = Image.open(fp)
            if img.size != (16, 16):
                return img.resize((16, 16))
            return img

        mod_dir = self.mod_dir
        # Create the mod_dir.
        if not os.path.exists(mod_dir):
            os.makedirs(mod_dir)

        jar_content = self.__jar_content
        arch = self.__archive

        pat = "assets/.*?/textures"
        textures_entries = [a for a in jar_content if re.match(pat, a) and a.endswith(".png")]
        textures_num = len(textures_entries)

        if textures_num:
            _s = math.sqrt(textures_num)
            sq_root = int(round(_s))
            # WARNING: textue_size is in tiles of 16*16 pixels, so a size of 4*4 will be a 64*64 pixels image!
            plus = 0 # width
            pluss = [sq_root, sq_root]
            while (pluss[0] * pluss[1]) < textures_num:
                pluss[plus] += 1
                plus = int(not plus)
            width, height = pluss
            texture_size = width, height
            image_size = (width * 16, height * 16)
            self.notex_idx = width - 1, height - 1
    
#             print "textures_num", textures_num
#             print "_s", _s
#             print "sq_root", sq_root
#             print "texture_size", texture_size
#             print "verif: sq_root * sq_root, all_texture_num", sq_root * sq_root, textures_num
            
            print "Mod textures number:", textures_num
            print "Mod texture size (in 16*16 pxels tiles:", texture_size
    
            # ===============================================================
            # Texture file creation and population
            #
            # Also populate a catalog like {"texture_name": [offset_x, offset_y]}
            # This catalog will be used later by MCEdit to get the image in the texture
            # and to write json data.
            # "texture_name" is the image file name found in the .jar, without extension.
            #
            # ===============================================================
            # Create the new texture image.
            texture_catalog = {}

            # Store the tile offsets
            offset_x, offset_y = 0, 0

            self.texture_file = texture_file = os.path.join(mod_dir, "terrain.png")

            background_color = (107, 63, 127)
            foreground_color = (214, 127, 255)

            texture = Image.new("RGBA", image_size, color=background_color)
            print "Mod texture size:", texture.size

            # Populate it with the mod textures.
            print "Populating texture with mod ones."
            for img_path in textures_entries:
                fdata = arch.read(img_path)
                fimg = StringIO(fdata)
                img = get_16x16_image(fimg)
                x, y = offset_x * 16, offset_y * 16
                w, h = x + 16, y + 16
#                 print "Pasting at", offset_x, offset_y, img_path
                texture.paste(img, (x, y, w, h))
                texture_catalog[os.path.splitext(os.path.split(img_path)[1])[0]] = (offset_x, offset_y)
                if offset_x < texture_size[0] - 1:
                    offset_x += 1
                else:
                    offset_x = 0
                    offset_y += 1

            self.texture_catalog = texture_catalog

            # Finish by drawing foreground_color squares where no other image ha been put.
            print "Filling up mod texture with default one."
            notex = Image.new("RGBA", (14, 14), color=foreground_color)
            while (offset_x * offset_y) < textures_num:
                x, y = (offset_x * 16) + 1, (offset_y * 16) + 1
                w, h = x + 14, y + 14
                texture.paste(notex, (x, y, w, h))
                if offset_x < texture_size[0] - 1:
                    offset_x += 1
                else:
                    offset_x = 0
                    offset_y += 1
#             print "offsets:", offset_x, offset_y

            # Finally, save the file
            texture.save(texture_file, "png")
            print "Texture file saved:", texture_file


    def __add_to_defs(self, name, j_data, namespace, d_type):
        """Adds the a definition to the future json file internal data.
        :name: string: The name of the object to be added. Shall be the 'idStr'.
        :j_data: object: Parsed json data to extract information from.
        :namespace: string: The namespace to add the data to.
        :d_type: string: type of the data such 'blocks' or 'entities'."""
        built_json = self.built_json
        texture_catalog = self.texture_catalog
        notex_idx = self.notex_idx

        if namespace not in built_json.keys():
            built_json[namespace] = {}
        if d_type not in built_json[namespace].keys():
            built_json[namespace][d_type] = []

        # Numeric IDs are added according to self.block_ids or the order of the files in the .jar.
        oid = self.block_ids.get(namespace, {}).get(name, 0) or len(built_json[namespace][d_type]) + 1

        built_json[namespace][d_type].append({"id": oid,
                                              "idStr": name,
                                              "name": name.replace("_", " ").title(),
                                              "tex": texture_catalog.get(name, notex_idx)
                                              }
                                             )

        self.built_json = built_json


    def __load_block_models(self):
        """Loads the mod block definitions from the models/block .jar subfolders.
        Data is then contained in self.blocks"""
        arch = self.__archive
        jar_content = self.__jar_content
        pat = "assets/.*?/models/block"
        blocks_entries = [a for a in jar_content if re.match(pat, a) and a.endswith(".json")]

        # 'assets' can contain several directories with textures an json definitions.
        # Some definition file names may be duplicated between diferent folders but
        # May contain different data.
        # So let use these directory names as 'namespaces'

        blocks = {}
        namespace_pat = "assets/(.*?)/models/block"
        blocks_num = 0

        for entry in blocks_entries:
            block_name = os.path.splitext(os.path.split(entry)[1])[0]
            namespace = re.search(namespace_pat, entry).groups()[0]
            if namespace not in blocks.keys():
                blocks[namespace] = {}
            t_data = arch.read(entry)
            j_data = json.loads(t_data)
            # Rebuild the json stuff compatible with id_definitions.ids_loader interface.
            self.__add_to_defs(block_name, j_data, namespace, 'blocks')

            blocks[namespace][block_name] = j_data
            blocks_num += 1
        self.__blocks = blocks
        print "Loaded %s block models from %s entries in %s namespaces:" % (blocks_num,
                                                                            len(blocks_entries),
                                                                            len(blocks))
        for name in blocks.keys():
            print "  *", name, len(blocks[name]), "blocks."


    def __save_json(self):
        """Saves built_json object to correponding files in mo_dir 'defs' subdirectories."""
        built_json = self.built_json
        if built_json:
            mod_dir = self.mod_dir
            defs_path = os.path.join(mod_dir, "defs")
            print "Saving json data to '%s'." % defs_path
            if not os.path.exists(defs_path):
                os.makedirs(defs_path)
            for namespace in built_json.keys():
                namespace_path = os.path.join(defs_path, namespace)
                if not os.path.exists(namespace_path):
                    os.makedirs(namespace_path)
                ns_data = built_json[namespace]
                for d_type in ns_data.keys():
                    d_type_data = ns_data[d_type]
                    d_type_file = os.path.join(namespace_path, "%s.json" % d_type)
                    print "Saving '%s' data for '%s' namespace in '%s'." % (d_type, namespace, d_type_file)
                    with open(d_type_file, "w") as fout:
                        json.dump(ns_data, fout, indent=4)
        else:
            print "No json data to save."


# ------------------------------------------------------------------------------
def build_mod_ids_map(root_tag):
    """Search for Forge specific definitions in 'root_tag'.
    :root_tag: NBT_Compound object: The NBT data from a level.dat file.
        Absolutely, can be any NBT_Compoun object."""
    # Initialize a default object to be returned
    block_ids = {}
    mod_entries = {}
#     print "root_tag.keys()", root_tag.keys()
    if "FML" in root_tag.keys():
#         print root_tag["FML"].keys()
#         print root_tag["FML"].get("ModList", None)
        # We have a Forge mod, let process :)
        # Get the mod IDs from 'ModList' tag ('ModId')
        # mod_entries is a dict like object (TAG_Compound): {"ModId": "<modid>", "ModVersion <X.X.X>"}
        # It has been seen wrong mod version (for Conquest Reforged for MC 1.10.2).
        _mod_entries = root_tag["FML"].get("ModList", None) or root_tag["FML"].get("modlist", None)
        for entry in _mod_entries:
            mod_entries[entry["ModId"].value] = entry["ModVersion"].value
        # Then, parse the 'Registries::minecraft:blocks::ids' tag to find
        # which mods has to be loaded. Some mods only implement game rules
        # or UI/functionnal stuff, but no blocks/entities.
        if mod_entries:
            registries = root_tag["FML"].get("Registries", None) or root_tag["FML"].get("registries", None)
            if registries:
                # minecraft_block reflects the mod defined blocks...
                minecraft_blocks = registries.get("minecraft:blocks", None)
                # Put every definition found here in the block_ids object
                if minecraft_blocks:
                    block_names_ids = minecraft_blocks.get("ids", None)
                    # If an element in mod_entries is found here, trigger it to be loaded.
                    # TODO: Find a way to guess the .jar file name from the modid
                    # and version. May request user action to select the right .jar.
                    # This will be delayed in another function/method
                    for block_name_id in block_names_ids:
                        b_name = block_name_id["K"].value
                        b_id = block_name_id["V"].value
                        namespace, name = b_name.split(":")
                        if namespace not in block_ids:
                            block_ids[namespace] = {}
                        block_ids[namespace][name] = int(b_id)
        # Guesss the mod .jar name...

    return block_ids, mod_entries


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Let use this for tests :)
    import sys
    # modloader.py <jar_file> <output_dir>
    loader = ModLoader(sys.argv[1], sys.argv[2])
#     print loader.__dict__
#     print loader.texture_catalog
