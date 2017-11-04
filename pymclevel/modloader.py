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
# * Read the Json data to retrieve the elements in the texture_catalog.
# * Write corresponding .json files using collected data.
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


class ModLoader(object):
    """Loads a mod packed in a .jar file and extract needed information in a
    directory named like the mod.
    The destination directory will contin .json definition files and a texture
    one usable by MCEdit."""
    def __init__(self, file_name, output_dir):
        """Initialize the object.
        :file_name: string: Full path to the .jar file. Must exists!
        :output_dir: string: The directory where to create the mod content. Must exists!"""
        print "Loading mod", file_name
        self.file_name = file_name
        self.output_dir = output_dir

        # Let define some useful data for forein class/method usage.
        self.mod_name = None
        # Full path to the mod directory where self.texture_file and json definitions are.
        # Will be set to self.output_dir + mod name later.
        self.mod_dir = None
        # Textures file name in self.mod_dir.
        # This file will be built using the ones found in the mod .jar.
        self.texture_file = None
        self.mod_info = None
        self.version = None
        self.mcversion = None
        self.modid = None
        self.texture_catalog = {}

        # Open the jar and finish the initialization.
        self.__archive = zipfile.ZipFile(file_name)
        self.__jar_content = self.__archive.namelist()
        self.__read_mod_info()
        self.__build_texture()
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
        dir_name = self.mod_name
        if self.version != mod_name:
            dir_name += "_%s" % self.version
        self.mod_dir = os.path.join(self.output_dir, dir_name)
        self.modid = mod_info.get("modid", mod_name)

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

        pat = "assets{0}.*?{0}textures".format(os.path.sep)
        textures_entries = [a for a in jar_content if re.match(pat, a) and a.endswith(".png")]
        textures_num = len(textures_entries)

        if textures_num:
            _s = math.sqrt(textures_num)
            sq_root = int(round(_s))
            # WARNING: textue_size is in tiles of 16*16 pixels, so a size of 4*4 will be a 64*64 pixels image!
            texture_size = (sq_root, sq_root)
            image_size = (sq_root * 16, sq_root * 16)
    
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


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Let use this for tests :)
    import sys
    # modloader.py <jar_file> <output_dir>
    loader = ModLoader(sys.argv[1], sys.argv[2])
#     print loader.__dict__
    print loader.texture_catalog
