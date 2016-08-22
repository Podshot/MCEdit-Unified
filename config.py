"""Copyright (c) 2010-2012 David Rio Vierra

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""

"""
config.py
Configuration settings and storage.
"""
import logging
import collections
import ConfigParser

from locale import getdefaultlocale
DEF_ENC = getdefaultlocale()[1]
if DEF_ENC is None:
    DEF_ENC = "UTF-8"

import directories
import weakref

log = logging.getLogger(__name__)


class Config(object):
    def __init__(self, config_definitions):
        log.info("Loading config...")
        self.config = ConfigParser.RawConfigParser([], ConfigDict)
        self.config.observers = {}
        try:
            self.config.read(self.getPath())
        except Exception, e:
            log.warn("Error while reading configuration file mcedit.ini: {0}".format(e))

        self.transformConfig()
        self._sections = {}
        for (sectionKey, sectionName), items in config_definitions.iteritems():
            self._sections[sectionKey] = ConfigSection(self.config, sectionName, items)
            setattr(self, sectionKey, self._sections[sectionKey])
        self.save()

    def __getitem__(self, section):
        return self._sections[section]

    @staticmethod
    def getPath():
        return directories.configFilePath

    @staticmethod
    def transformKey(value, n=0):
        if 'left' in value and len(value) > 5:
            value = value[5:]
        elif 'right' in value and len(value) > 6:
            value = value[6:]
        if 'a' <= value <= 'z':
            value = value.replace(value[0], value[0].upper(), 1)
        if n >= 36 and "Ctrl-" not in value:
            value = "Ctrl-" + value
        if value == "Mouse3":
            value = "Button 3"
        elif value == "Mouse4":
            value = "Scroll Up"
        elif value == "Mouse5":
            value = "Scroll Down"
        elif value == "Mouse6":
            value = "Button 4"
        elif value == "Mouse7":
            value = "Button 5"
        return value

    @staticmethod
    def convert(key):
        vals = key.replace('-', ' ').translate(None, '()').lower().split(' ')
        return vals[0] + "".join(x.title() for x in vals[1:])

    def reset(self):
        for section in self.config.sections():
            self.config.remove_section(section)

    def transformConfig(self):
        if self.config.has_section("Version") and self.config.has_option("Version", "version"):
            version = self.config.get("Version", "version")
        else:
            self.reset()
            return

        if version == "1.1.1.1":
            n = 1
            for (name, value) in self.config.items("Keys"):
                if name != "Swap View" and name != "Toggle Fps Counter":
                    self.config.set("Keys", name, self.transformKey(value, n))
                elif name == "Swap View":
                    self.config.set("Keys", "View Distance", self.transformKey(value, n))
                    self.config.set("Keys", "Swap View", "None")
                elif name == "Toggle Fps Counter":
                    self.config.set("Keys", "Debug Overlay", self.transformKey(value, n))
                    self.config.set("Keys", "Toggle Fps Counter", "None")
                n += 1
            if self.config.get("Keys", "Brake") == "Space":
                version = "1.1.2.0-update"
            else:
                version = "1.1.2.0-new"
            self.config.set("Version", "version", version)
            self.save()

    def save(self):
        try:
            cf = file(self.getPath(), 'w')
            self.config.write(cf)
            cf.close()
        except Exception as e:
            log.error("Error saving configuration settings to mcedit.ini: {0}".format(e))


class ConfigSection(object):
    def __init__(self, config, section, items):
        self.section = section
        if not config.has_section(section):
            config.add_section(section)
        self._items = {}
        for item in items:
            if isinstance(item, ConfigValue):
                value = item
            elif type(item[2]) in ListValue.allowedTypes:
                value = ListValue(item[0], item[1], item[2])
            else:
                value = ConfigValue(item[0], item[1], item[2])
            value.config = config
            value.section = section
            self._items[value.key] = value
            value.get()
            if value.section == "Keys" and value.config.get(value.section, value.name) == "Delete":
                value.config.set(value.section, value.name, "Del")

    def __getitem__(self, key):
        return self._items[key]

    def __getattr__(self, key):
        return self.__getitem__(key)

    def items(self):
        return [(i.name, i.get()) for k, i in self._items.iteritems()]


class ConfigValue(object):

    allowedTypes = [int, float, bool, basestring, str, unicode]

    def __init__(self, key, name, default=None):
        if default is None:
            default = name
            name = key
        self.key = key
        self.name = name
        self.default = default
        self.type = type(default)
        if self.type not in self.allowedTypes:
            raise TypeError("Invalid config type %s" % repr(self.type))

    def get(self):
        try:
            if self.type is bool:
                return self.config.getboolean(self.section, self.name)
            if self.type is unicode:
                return self.type(self.config.get(self.section, self.name).decode(DEF_ENC))
            return self.type(self.config.get(self.section, self.name))
        except:
            if self.default is None:
                raise

            self.set(self.default)
            return self.default

    def getRaw(self):
        return self.config.get(self.section, self.name)

    def _setter(self, setter):
        def _s(s, value):
            if setter is not None:
                setter(s, value)
            return self.set(value)
        return _s

    def set(self, value):
        log.debug("Property Change: %15s %30s = %s", self.section, self.name, value)
        if self.type is unicode and type(value) is unicode:
            value = value.encode(DEF_ENC)
        self.config.set(self.section, self.name, str(value))
        self._notifyObservers(value)

    def addObserver(self, target, attr=None, callback=None):
        """ Register 'target' for changes in the config var named by section and name.
        When the config is changed, calls setattr with target and attr.
        attr may be None; it will be created from the name by lowercasing the first
        word, uppercasing the rest, and removing spaces.
        e.g. "block buffer" becomes "blockBuffer"
        """
        observers = self.config.observers.setdefault((self.section, self.name), {})
        if not attr:
            attr = self.key
        log.debug("Subscribing %s.%s", target, attr)

        attr = intern(attr)
        targetref = weakref.ref(target)
        observers.setdefault((targetref, attr), callback)

        val = self.get()

        setattr(target, attr, val)
        if callback:
            callback(val)

    def _notifyObservers(self, value):
        observers = self.config.observers.get((self.section, self.name), {})
        newObservers = {}
        for targetref, attr in observers:
            target = targetref()
            if target:
                log.debug("Notifying %s", target)
                setattr(target, attr, value)
                callback = observers[targetref, attr]
                if callback:
                    callback(value)

                newObservers[targetref, attr] = callback

        self.config.observers[(self.section, self.name)] = newObservers

    def property(self, setter=None):
        assert self.default is not None

        this = self

        def _getter(self):
            return this.get()

        return property(_getter, self._setter(setter), None)

    def __repr__(self):
        return "<%s>" % " ".join((
            self.__class__.__name__,
            "section=%r" % self.section,
            "key=%r" % self.key,
            "name=%r" % self.name,
            "default=%s" % self.default,
            "type=%s" % self.type
        ))

    def __int__(self):
        return int(self.get())

    def __float__(self):
        return float(self.get())

    def __bool__(self):
        return bool(self.get())


class ListValue(ConfigValue):

    allowedTypes = [list, tuple]

    def __init__(self, key, name, default=None):
        if default is None or len(default) < 1:
            raise ValueError("Default value %s is empty." % repr(default))
        self.subtype = type(default[0])
        super(ListValue, self).__init__(key, name, default)

    def get(self):
        try:
            return self.type(self.subtype(x.strip()) for x in self._config.get(self.section, self.name).translate(None, '[]()').split(','))
        except:
            if self.default is None:
                raise

            self.set(self.default)
            return self.default

    def __repr__(self):
        return "<%s>" % " ".join((
            self.__class__.__name__,
            "section=%r" % self.section,
            "key=%r" % self.key,
            "name=%r" % self.name,
            "default=%s" % self.default,
            "type=%s" % self.type,
            "subtype=%s" % self.subtype
        ))


class ColorValue(ListValue):
    allowedTypes = [tuple]
    defaultColors = {}

    def __init__(self, key, name, default=None):
        super(ColorValue, self).__init__(key, name, default)
        ColorValue.defaultColors[name] = self

    def get(self):
        values = super(ColorValue, self).get()
        return tuple(min(max(x, 0.0), 1.0) for x in values)


class ConfigDict(collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        self.dict = dict(*args, **kwargs)
        self.keyorder = []

    def keys(self):
        return list(self.keyorder)

    def items(self):
        return list(self.__iteritems__())

    def __iteritems__(self):
        return ((k, self.dict[k]) for k in self.keys())

    def __iter__(self):
        return self.keys().__iter__()

    def __getitem__(self, k):
        return self.dict[k]

    def __setitem__(self, k, v):
        self.dict[k] = v
        if k not in self.keyorder:
            self.keyorder.append(k)

    def __delitem__(self, k):
        del self.dict[k]
        if k in self.keyorder:
            self.keyorder.remove(k)

    def __contains__(self, k):
        return self.dict.__contains__(k)

    def __len__(self):
        return self.dict.__len__()

    def copy(self):
        k = ConfigDict()
        k.dict = self.dict.copy()
        k.keyorder = list(self.keyorder)
        return k

# Quick Reference:
# 7 Bedrock
# 9 Still_Water
# 11 Still_Lava
# 14 Gold_Ore
# 15 Iron_Ore
# 16 Coal_Ore
# 21 Lapis_Lazuli_Ore
# 24 Sandstone
# 49 Obsidian
# 56 Diamond_Ore
# 73 Redstone_Ore
# 129 Emerald_Ore
# 153 Nether_Quartz_Ore
hiddableOres = [7, 16, 15, 21, 73, 14, 56, 153]

definitions = {
    ("keys", "Keys"): [
        ("forward", "forward", "W"),
        ("back", "back", "S"),
        ("left", "left", "A"),
        ("right", "right", "D"),
        ("up", "up", "Space"),
        ("down", "down", "Shift"),
        ("brake", "brake", "C"),
        ("sprint", "sprint", "None"),

        ("rotateClone", "rotate (clone)", "E"),
        ("rollClone", "roll (clone)", "R"),
        ("flip", "flip", "F"),
        ("mirror", "mirror", "G"),

        ("rotateBrush", "rotate (brush)", "E"),
        ("rollBrush", "roll (brush)", "G"),
        ("increaseBrush", "increase brush", "R"),
        ("decreaseBrush", "decrease brush", "F"),

        ("replaceShortcut", "replace shortcut", "R"),

        ("swap", "swap", "X"),

        ("panLeft", "pan left", "J"),
        ("panRight", "pan right", "L"),
        ("panUp", "pan up", "I"),
        ("panDown", "pan down", "K"),
        ("toggleView", "toggle view", "Tab"),

        ("resetReach", "reset reach", "Button 3"),
        ("increaseReach", "increase reach", "Scroll Up"),
        ("decreaseReach", "decrease reach", "Scroll Down"),

        ("confirmConstruction", "confirm construction", "Return"),

        ("openLevel", "open level", "O"),
        ("newLevel", "new level", "N"),
        ("deleteBlocks", "delete blocks", "Del"),
        ("lineTool", "line tool", "Z"),

        ("longDistanceMode", "long-distance mode", "Alt-Z"),
        ("flyMode", "fly mode", "None"),

        ("debugOverlay", "debug overlay", "0"),
        ("showBlockInfo", "show block info", "Alt"),
        ("pickBlock", "pick block", "Alt"),
        ("selectChunks", "select chunks", "Z"),
        ("deselectChunks", "deselect chunks", "Alt"),
        ("brushLineTool", "brush line tool", "Z"),
        ("snapCloneToAxis", "snap clone to axis", "Ctrl"),
        ("blocksOnlyModifier", "blocks-only modifier", "Alt"),
        ("fastIncrementModifierHold", "fast increment modifier", "Ctrl"),
        ("fastNudge", "fast nudge", "None"),

        ("takeAScreenshot", "take a screenshot", "F6"),

        ("quit", "quit", "Ctrl-Q"),
        ("viewDistance", "view distance", "Ctrl-F"),
        ("selectAll", "select all", "Ctrl-A"),
        ("deselect", "deselect", "Ctrl-D"),
        ("cut", "cut", "Ctrl-X"),
        ("copy", "copy", "Ctrl-C"),
        ("paste", "paste", "Ctrl-V"),
        ("reloadWorld", "reload world", "Ctrl-R"),
        ("open", "open", "Ctrl-O"),
        ("quickLoad", "quick load", "Ctrl-L"),
        ("undo", "undo", "Ctrl-Z"),
        ("redo", "redo", "Ctrl-Y"),
        ("save", "save", "Ctrl-S"),
        ("saveAs", "save as", "Ctrl-Alt-S"),
        ("newWorld", "new world", "Ctrl-N"),
        ("closeWorld", "close world", "Ctrl-W"),
        ("worldInfo", "world info", "Ctrl-I"),
        ("gotoPanel", "goto panel", "Ctrl-G"),
        ("exportSelection", "export selection", "Ctrl-E"),
        ("toggleRenderer", "toggle renderer", "Ctrl-M"),
        ("uploadWorld", "upload world", "Ctrl-U"),

        ("select", "select", "1"),
        ("brush", "brush", "2"),
        ("clone", "clone", "3"),
        ("fillAndReplace", "fill and replace", "4"),
        ("filter", "filter", "5"),
        ("importKey", "import", "6"),
        ("players", "players", "7"),
        ("worldSpawnpoint", "world spawnpoint", "8"),
        ("chunkControl", "chunk control", "9"),
        ("nbtExplorer", "nbt explorer", "None"),
    ],
    ("version", "Version"): [
        ("version", "version", "1.1.2.0")
    ],
    ("settings", "Settings"): [
        ("flyMode", "Fly Mode", False),
        ("enableMouseLag", "Enable Mouse Lag", False),
        ("longDistanceMode", "Long Distance Mode", False),
        ("shouldResizeAlert", "Window Size Alert", True),
        ("closeMinecraftWarning", "Close Minecraft Warning", True),
        ("skin", "MCEdit Skin", "[Current]"),
        ("fov", "Field of View", 70.0),
        ("spaceHeight", "Space Height", 64),
        ("blockBuffer", "Block Buffer", 256 * 1048576),
        ("reportCrashes", "report crashes new", False),
        ("reportCrashesAsked", "report crashes asked", False),
        ("staticCommandsNudge", "Static Coords While Nudging", False),
        ("moveSpawnerPosNudge", "Change Spawners While Nudging", False),
        ("rotateBlockBrush", "rotateBlockBrushRow", True),
        ("langCode", "Language String", "en_US"),
        ("viewDistance", "View Distance", 8),
        ("targetFPS", "Target FPS", 30),
        ("windowWidth", "window width", 1152),
        ("windowHeight", "window height", 864),
        ("windowMaximized", "window maximized", False),
        ("windowMaximizedHeight", "window maximized height", 0),
        ("windowMaximizedWidth", "window maximized width", 0),
        ("windowX", "window x", 0),
        ("windowY", "window y", 0),
        ("windowShowCmd", "window showcmd", 1),
        ("setWindowPlacement", "SetWindowPlacement", True),
        ("showHiddenOres", "show hidden ores", False),
        ("hiddableOres", "hiddable ores", hiddableOres),
        ] + [
            ("showOre%s" % i, "show ore %s" % i, True) for i in hiddableOres
        ] + [
        ("fastLeaves", "fast leaves", True),
        ("roughGraphics", "rough graphics", False),
        ("showChunkRedraw", "show chunk redraw", True),
        ("drawSky", "draw sky", True),
        ("drawFog", "draw fog", True),
        ("showCeiling", "show ceiling", True),
        ("drawEntities", "draw entities", True),
        ("drawMonsters", "draw monsters", True),
        ("drawItems", "draw items", True),
        ("drawTileEntities", "draw tile entities", True),
        ("drawTileTicks", "draw tile ticks", False),
        ("drawUnpopulatedChunks", "draw unpopulated chunks", True),
        ("drawChunkBorders", "draw chunk borders", False),
        ("vertexBufferLimit", "vertex buffer limit", 384),
        ("vsync", "vertical sync", 0),
        ("viewMode", "View Mode", "Camera"),
        ("undoLimit", "Undo Limit", 20),
        ("recentWorlds", "Recent Worlds", ['']),
        ("resourcePack", "Resource Pack", u"Default"),
        ("maxCopies", "Copy stack size", 32),
        ("superSecretSettings", "Super Secret Settings", False),
        ("compassToggle", "Compass Toggle", True),
        ("compassSize", "Compass Size", 60),
        ("fogIntensity", "Fog Intensity", 20),
        ("fontProportion", "Fonts Proportion", 100),
        ("downloadPlayerSkins", "Download Player Skins", True),
        ("maxViewDistance", "Max View Distance", 32),
        ("drawPlayerHeads", "Draw Player Heads", True),
        ("showQuickBlockInfo", "Show Block Info when hovering", True),
        ("savePositionOnClose", "Save camera position on close", False),
        ("showWindowSizeWarning", "Show window size warning", True)
    ],
    ("controls", "Controls"): [
        ("mouseSpeed", "mouse speed", 5.0),
        ("cameraAccel", "camera acceleration", 125.0),
        ("cameraDrag", "camera drag", 100.0),
        ("cameraMaxSpeed", "camera maximum speed", 60.0),
        ("cameraBrakingSpeed", "camera braking speed", 8.0),
        ("invertMousePitch", "invert mouse pitch", False),
        ("autobrake", "autobrake", True),
        ("swapAxes", "swap axes looking down", False)
    ],
    ("brush", "Brush"): [
        ("brushSizeL", "Brush Shape L", 3),
        ("brushSizeH", "Brush Shape H", 3),
        ("brushSizeW", "Brush Shape W", 3),
        ("updateBrushOffset", "Update Brush Offset", False),
        ("chooseBlockImmediately", "Choose Block Immediately", False),
        ("alpha", "Alpha", 0.66)
    ],
    ("clone", "Clone"): [
        ("copyAir", "Copy Air", True),
        ("copyWater", "Copy Water", True),
        ("copyBiomes", "Copy Biomes", False),
        ("staticCommands", "Change Coordinates", False),
        ("moveSpawnerPos", "Change Spawners Pos", False),
        ("regenerateUUID", "Regenerate UUIDs", True),
        ("placeImmediately", "Place Immediately", True)
    ],
    ("fill", "Fill"): [
        ("chooseBlockImmediately", "Choose Block Immediately", True),
        ("chooseBlockImmediatelyReplace", "Choose Block Immediately for Replace", True)
    ],
    ("spawn", "Spawn"): [
        ("spawnProtection", "Spawn Protection", True)
    ],
    ("selection", "Selection"): [
        ("showPreviousSelection", "Show Previous Selection", True),
        ("color", "Color", "white")
    ],
    ("selectionColors", "Selection Colors"): [
        ColorValue("white", "white", (1.0, 1.0, 1.0)),
        ColorValue("blue", "blue", (0.75, 0.75, 1.0)),
        ColorValue("green", "green", (0.75, 1.0, 0.75)),
        ColorValue("red", "red", (1.0, 0.75, 0.75)),
        ColorValue("teal", "teal", (0.75, 1.0, 1.0)),
        ColorValue("pink", "pink", (1.0, 0.75, 1.0)),
        ColorValue("yellow", "yellow", (1.0, 1.0, 0.75)),
        ColorValue("grey", "grey", (0.6, 0.6, 0.6)),
        ColorValue("black", "black", (0.0, 0.0, 0.0))
    ],
    ("fastNudgeSettings", "Fast Nudge Settings"): [
        ("blocksWidth", "Blocks Width", False),
        ("blocksWidthNumber", "Blocks Width Number", 16),
        ("selectionWidth", "Selection Width", False),
        ("selectionWidthNumber", "Selection Width Number", 16),
        ("pointsWidth", "Points Width", False),
        ("pointsWidthNumber", "Points Width Number", 16),
        ("cloneWidth", "clone Width", True),
        ("cloneWidthNumber", "Clone Width Number", 16),
        ("importWidth", "Import Width", False),
        ("importWidthNumber", "Import Width Number", 8),
    ],
    ("nbtTreeSettings", "NBT Tree Settings"): [
        ("useBulletStyles", "Use Bullet Styles", True),
        ("useBulletText", "Use Bullet Text", False),
        ("useBulletImages", "Use Bullet Images", True),
        ("defaultBulletImages", "Default Bullet Images", True),
        ("bulletFileName", "Bullet Images File", directories.os.path.join(directories.getDataDir(), 'Nbtsheet.png')),
        ("showAllTags", "Show all the tags in the tree", False),
    ],
    ("Filter Keys", "Filter Keys"): [],
    ("session", "Session",): [
        ("override", "Override", False)
    ],
    ("commands", "Commands"): [
        ("sorting", "Sorting", "chain"),
        ("space", "Space", True),
        ("fileFormat", "File Format", "txt")
    ],
    ("schematicCopying", "Schematics Copying"): [
        ("cancelCommandBlockOffset", "Cancel Command Block Offset", False)
    ]
}


config = None

if config is None:
    config = Config(definitions)
