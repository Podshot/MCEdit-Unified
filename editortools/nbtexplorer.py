# -*- coding: utf-8 -*-
#
# nbtexplorer.py
#
# D.C.-G. (LaChal) 2014
#
# Display NBT structure
#
#
# TODO:
# * add local undo/redo for loaded NBT files
# * change/optimize the undo/redo when edit level NBT data
# * add a style editor and an image wrapper for the bullets
from pygame import key, draw, image, Rect, event, MOUSEBUTTONDOWN
from albow import Column, Row, Label, Tree, TableView, TableColumn, Button, \
    FloatField, IntField, TextFieldWrapped, AttrRef, ItemRef, CheckBox, Widget, \
    ScrollPanel, ask, alert, input_text_buttons, CheckBoxLabel, ChoiceButton, Menu, Frame
from albow.dialogs import Dialog
from albow.tree import TreeRow, setup_map_types_item
from albow.utils import blit_in_rect
from albow.translate import _, getLang
from glbackground import Panel
from pymclevel.nbt import load, TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, \
    TAG_Double, TAG_String, TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, \
    TAG_Short_Array, littleEndianNBT, NBTFormatError, TAG_BYTE, TAG_SHORT, TAG_INT, \
    TAG_LONG, TAG_FLOAT, TAG_DOUBLE, TAG_STRING, TAG_BYTE_ARRAY, TAG_LIST, TAG_COMPOUND, \
    TAG_INT_ARRAY, TAG_SHORT_ARRAY
from numpy import array
from albow.theme import root

scroll_button_size = 0 + root.PaletteView.scroll_button_size
bullet_color_active = root.Tree.bullet_color_active
fg_color = root.fg_color
disabled_color = root.Label.disabled_color
del root
from editortools.editortool import EditorTool
from editortools.operation import Operation
from editortools.tooloptions import ToolOptions
import copy
from directories import getDataDir
import os
import mcplatform
from config import config, DEF_ENC
from albow.resource import resource_path

# &# Protoype for blocks/items names
from pymclevel.materials import block_map, alphaMaterials

map_block = {}
for k, v in block_map.items():
    map_block[v] = k

from pymclevel.items import items as mcitems

map_items = {}
for k, v in mcitems.items.items():
    if type(v) == dict:
        names = []
        if type(v['name']) == list:
            names = v['name']
        else:
            names = [v['name']]
        for name in names:
            if name != None and name not in map_items.keys():
                map_items[name] = (k, names.index(name))

# # DEBUG
# #keys = map_items.keys()
# #keys.sort()
# #f = open('map_items.txt', 'w')
# #for k in keys:
# #    f.write('%s: %s\n'%(k, map_items[k]))
# #f.close()
# #f = open('mcitems.txt', 'w')
# #keys = mcitems.items.keys()
# #for k in keys:
# #    f.write('%s: %s\n'%(k, mcitems.items[k]))
# #f.close()

import mclangres
# &#

import struct

# -----------------------------------------------------------------------------
bullet_image = None
default_bullet_images = os.path.join(getDataDir(), "Nbtsheet.png")


def get_bullet_image(index, w=16, h=16):
    global bullet_image

    if not bullet_image:
        # # Debug for MacOS
        try:
            if config.nbtTreeSettings.defaultBulletImages.get():
                bullet_image = image.load(default_bullet_images)
            else:
                bullet_image = image.load(resource_path(config.nbtTreeSettings.bulletFileName.get()))
        except Exception, e:
            print "*** MCEDIT DEBUG: bullets image could not be loaded."
            print "*** MCEDIT DEBUG:", e
            print "*** MCEDIT DEBUG: bullets image file:", resource_path(config.nbtTreeSettings.bulletFileName.get())
            print "*** MCEDIT DEBUG: current directory:", os.getcwd()
            from pygame import Surface, draw, SRCALPHA
            bullet_image = Surface((64, 64), SRCALPHA)
            bullet_image.fill((0, 0, 0, 0))
            for i in range(4):
                for j in range(4):
                    bullet_image.fill((255/(i or 1), 255/(j or 1), 255, 255), [16*i, 16*j, 16*i+16, 16*j+16])

    r = Rect(0, 0, w, h)
    line_length = int(bullet_image.get_width() / w)
    line = int(index / line_length)
    r.top = line * h
    r.left = (index - (line * line_length)) * w
    return bullet_image.subsurface(r)


default_bullet_styles = {TAG_Byte: ((20, 20, 200), None, 'circle', 'b'),
                         TAG_Double: ((20, 200, 20), None, 'circle', 'd'),
                         TAG_Float: ((200, 20, 20), None, 'circle', 'f'),
                         TAG_Int: ((16, 160, 160), None, 'circle', 'i'),
                         TAG_Long: ((200, 20, 200), None, 'circle', 'l'),
                         TAG_Short: ((200, 200, 20), (0, 0, 0), 'circle', 's'),
                         TAG_String: ((60, 60, 60), None, 'circle', 's'),
                         TAG_Compound: (bullet_color_active, None, '', ''),
                         TAG_Byte_Array: ((20, 20, 200), None, 'square', 'B'),
                         TAG_Int_Array: ((16, 160, 160), None, 'square', 'I'),
                         TAG_List: ((200, 200, 200), (0, 0, 0), 'square', 'L'),
                         TAG_Short_Array: ((200, 200, 20), None, 'square', 'S'),
                         }
default_bullet_styles[dict] = default_bullet_styles[TAG_List]

bullet_styles = copy.deepcopy(default_bullet_styles)


def change_styles():
    global default_bullet_styles
    global bullet_styles
    if config.nbtTreeSettings.useBulletStyles.get() and \
            ((config.nbtTreeSettings.useBulletImages.get() and \
            os.path.exists(config.nbtTreeSettings.bulletFileName.get())) \
            or config.nbtTreeSettings.defaultBulletImages.get()):
        i = 0
        for key in (
                TAG_Byte, TAG_Double, TAG_Float, TAG_Int, TAG_Long, TAG_Short, TAG_String, TAG_Compound, TAG_Byte_Array,
                TAG_Int_Array, TAG_List):
            bullet_styles[key] = (get_bullet_image(i), None, 'image', '')
            i += 1

        bullet_styles[TAG_Short_Array] = bullet_styles[TAG_Int_Array]
        bullet_styles[dict] = bullet_styles[TAG_List]
    else:
        bullet_styles = copy.deepcopy(default_bullet_styles)
    return bullet_styles


change_styles()

# -----------------------------------------------------------------------------
field_types = {TAG_Byte: (IntField, (0, 256)),
               TAG_Double: (FloatField, None),
               TAG_Float: (FloatField, None),
               TAG_Int: (IntField, (-2147483647, +2147483647)),
               TAG_Long: (IntField, (-9223372036854775807, +9223372036854775807)),
               TAG_Short: (IntField, (-65535, 65536)),
               TAG_String: (TextFieldWrapped, None),
               }

array_types = {TAG_Byte_Array: field_types[TAG_Byte],
               TAG_Int_Array: field_types[TAG_Int],
               TAG_Short_Array: field_types[TAG_Short],
               }


# -----------------------------------------------------------------------------
class TAG_List_Type(Widget):
    choices = []

    def __init__(self, value=None):
        Widget.__init__(self)
        self.choiceButton = ChoiceButton(self.choices)
        self.add(self.choiceButton)
        self.shrink_wrap()

    @property
    def value(self):
        return self.choiceButton.selectedChoice


item_types_map = {TAG_Byte: ("Byte", IntField, 0),
                  TAG_Double: ("Floating point", FloatField, 0.0),
                  TAG_Float: ("Floating point", FloatField, 0.0),
                  TAG_Int: ("Integral", IntField, 0),
                  TAG_Long: ("Long", IntField, 0),
                  TAG_Short: ("Short", IntField, 0),
                  TAG_String: ("String", TextFieldWrapped, ""),
                  TAG_List: ("List", TAG_List_Type, None),
                  TAG_Compound: ("Compound", None, None),
                  TAG_Byte_Array: ("Byte Array", TextFieldWrapped, ""),
                  TAG_Int_Array: ("Int Array", TextFieldWrapped, ""),
                  TAG_Short_Array: ("Short Array", TextFieldWrapped, ""),
                  }

map_types_item = setup_map_types_item(item_types_map)

TAG_List_Type.choices = map_types_item.keys()
    

# -----------------------------------------------------------------------------
def create_base_item(self, i_type, i_name, i_value):
    return i_name, i_type(type(item_types_map[i_type][2])(i_value), i_name)


create_TAG_Byte = create_TAG_Int = create_TAG_Short = create_TAG_Long = \
    create_TAG_String = create_TAG_Double = create_TAG_Float = create_base_item


def create_TAG_Compound(self, i_type, i_name, i_value):
    return i_name, i_type([], i_name)


def create_TAG_List(self, i_type, i_name, i_value):
    return i_name, i_type([], i_name, globals()[map_types_item[i_value][0].__name__.upper()])


def create_array_item(self, i_type, i_name, i_value):
    value = i_value.strip().strip('[]').strip()
    if value != "":
        value = [int(a.strip()) for a in value.split(",") if a.strip().isdigit()]
    else:
        value = None
    return i_name, i_type(array(value, i_type.dtype), i_name)


create_TAG_Byte_Array = create_TAG_Int_Array = create_TAG_Short_Array = create_array_item

# -----------------------------------------------------------------------------
class NBTTree(Tree):
    def __init__(self, *args, **kwargs):
        styles = kwargs.get('styles', {})
        self.update_draw_bullets_methods(styles)
        global map_types_item
        self.map_types_item = setup_map_types_item(item_types_map)
        Tree.__init__(self, *args, **kwargs)
        for t in self.item_types:
            if 'create_%s' % t.__name__ in globals().keys():
                setattr(self, 'create_%s' % t.__name__, globals()['create_%s' % t.__name__])

    def _draw_opened_bullet(self, *args, **kwargs):
        return Tree.draw_opened_bullet(self, *args, **kwargs)

    def _draw_closed_bullet(self, *args, **kwargs):
        return Tree.draw_closed_bullet(self, *args, **kwargs)

    def update_draw_bullets_methods(self, styles):
        if config.nbtTreeSettings.useBulletStyles.get() and bullet_styles.get(TAG_Compound, [''] * 4)[2] != '':
            self.draw_opened_bullet = self.draw_closed_bullet = self.draw_TAG_bullet
        else:
            self.draw_opened_bullet = self._draw_opened_bullet
            self.draw_closed_bullet = self._draw_closed_bullet
        for key in styles.keys():
            if hasattr(key, '__name__'):
                name = key.__name__
            elif type(key) in (str, unicode):
                name = key
            else:
                name = repr(key)
            setattr(self, 'draw_%s_bullet' % name, self.draw_TAG_bullet)

    @staticmethod
    def add_item_to_TAG_Compound(parent, name, item):
        parent[name] = item

    def add_item_to_TAG_List(self, parent, name, item):
        if parent == self.selected_item[9]:
            idx = len(parent.value)
        else:
            idx = parent.value.index(self.selected_item[9])
        parent.insert(idx, item)

    def add_item(self, types_item=None):
        if types_item is None:
            parent = self.get_item_parent(self.selected_item)
            if parent:
                p_type = parent[7]
                if p_type == TAG_List:
                    k = parent[9].list_type
                    v = None
                    for key, value in item_types_map.items():
                        if globals().get(key.__name__.upper(), -1) == k:
                            v = value
                            break
                    if v is None:
                        return
                    types_item = {v[0]: (key, v[1], v[2])}
        Tree.add_item(self, types_item)

    def add_child(self, types_item=None):
        if types_item is None:
            parent = self.selected_item
            p_type = parent[7]
            if p_type == TAG_List:
                k = parent[9].list_type
                v = None
                for key, value in item_types_map.items():
                    if globals().get(key.__name__.upper(), -1) == k:
                        v = value
                        break
                if v is None:
                    return
                types_item = {v[0]: (key, v[1], v[2])}
        Tree.add_child(self, types_item)

    def delete_item(self):
        parent = self.get_item_parent(self.selected_item)
        if parent:
            if parent[7] == TAG_List:
                del parent[9][parent[9].value.index(self.selected_item[9])]
            else:
                del parent[9][self.selected_item[9].name]
        else:
            del self.data[self.selected_item[9].name]
        self.selected_item_index = None
        self.selected_item = None
        self.build_layout()

    def rename_item(self):
        result = input_text_buttons("Choose a name", 300, self.selected_item[3])
        if type(result) in (str, unicode):
            self.selected_item[3] = result
            self.selected_item[9].name = result
            self.build_layout()

    def click_item(self, *args, **kwargs):
        Tree.click_item(self, *args, **kwargs)
        if self._parent and self.selected_item:
            self._parent.update_side_panel(self.selected_item)

    @staticmethod
    def draw_image(surf, bg, r):
        blit_in_rect(surf, bg, r, 'c')

    @staticmethod
    def draw_square(surf, bg, r):
        draw.polygon(surf, bg, [r.topleft, r.topright, r.bottomright, r.bottomleft])

    @staticmethod
    def draw_circle(surf, bg, r):
        draw.circle(surf, bg, ((r.left + r.right) / 2, (r.top + r.bottom) / 2), min(r.height / 2, r.width / 2))

    def draw_TAG_bullet(self, surf, bg, fg, shape, text, item_text, lvl):
        r = self.get_bullet_rect(surf, lvl)
        meth = getattr(self, 'draw_%s' % shape, None)
        if meth and config.nbtTreeSettings.useBulletStyles.get():
            meth(surf, bg, r)
            self.draw_item_text(surf, r, item_text)
        else:
            self.draw_deadend_bullet(surf, self.bullet_color_inactive, fg, shape, text, item_text, lvl)
        if text and config.nbtTreeSettings.useBulletStyles.get() and config.nbtTreeSettings.useBulletText.get():
            buf = self.font.render(text, True, fg or self.fg_color)
            blit_in_rect(surf, buf, r, 'c')
        if config.nbtTreeSettings.useBulletImages.get():
            self.draw_item_text(surf, r, item_text)

    def parse_TAG_List(self, name, data):
        values = {}
        i = 0
        for value in data:
            if hasattr(value, 'get'):
                value_name = value.get('Name', None)
                if value_name:
                    value_name = value_name.value
            else:
                value_name = value.name
            values[value_name or u"%s #%03d" % (name, i)] = value
            i += 1
        return values


# -----------------------------------------------------------------------------
class NBTExplorerOptions(ToolOptions):
    def __init__(self, tool):
        ToolOptions.__init__(self, name='Panel.NBTExplorerOptions')
        self.tool = tool
        useStyleBox = CheckBoxLabel(title="Use Bullet Styles",
                                    ref=config.nbtTreeSettings.useBulletStyles)

        self.useStyleBox = useStyleBox
        useTextBox = CheckBoxLabel(title="Use Bullet Text",
                                   ref=config.nbtTreeSettings.useBulletText)
        self.useTextBox = useTextBox
        useImagesBox = CheckBoxLabel(title="Use Bullet Images",
                                     ref=config.nbtTreeSettings.useBulletImages)
        self.useImagesBox = useImagesBox

        bulletFilePath = Row((Button("Bullet Images File", action=self.open_bullet_file),
                              TextFieldWrapped(ref=config.nbtTreeSettings.bulletFileName, width=300)), margin=0)

        defaultBulletImagesBox = CheckBoxLabel(title="Reset to default",
                                         ref=config.nbtTreeSettings.defaultBulletImages)
        self.defaultBulletImagesBox = defaultBulletImagesBox

        def mouse_down(e):
            CheckBox.mouse_down(defaultBulletImagesBox.subwidgets[1], e)
            self.defaultBulletImagesBox_click(e)

        defaultBulletImagesBox.subwidgets[1].mouse_down = mouse_down

        frameContent = Column((defaultBulletImagesBox, bulletFilePath))
        color = self.bg_color
        if len(color) == 4:
            color = (max(color[0] + 200, 255), max(color[1] + 200, 255), max(color[2] + 200, 255), max(color[3] + 100,255))
        else:
            color = tuple([max([i] * 2, 255) for i in color])
        bulletFilePathFrame = Frame(frameContent, border_width=1, border_color=color)
        bulletFilePathFrame.add_centered(frameContent)

        def mouse_down(e):
            if self.bulletFilePath.subwidgets[1].enabled:
                TextFieldWrapped.mouse_down(self.bulletFilePath.subwidgets[1], e)

        bulletFilePath.subwidgets[1].mouse_down = mouse_down
        self.bulletFilePath = bulletFilePath

        def mouse_down(e):
            CheckBox.mouse_down(useImagesBox.subwidgets[1], e)
            for sub in defaultBulletImagesBox.subwidgets:
                sub.enabled = config.nbtTreeSettings.useBulletImages.get()
                if type(sub) in (CheckBox, TextFieldWrapped):
                    if config.nbtTreeSettings.useBulletImages.get():
                        sub.fg_color = fg_color
                    else:
                        sub.fg_color = disabled_color
                if type(sub) == CheckBox:
                    sub.set_enabled(config.nbtTreeSettings.useBulletImages.get())
            self.defaultBulletImagesBox_click(None)

        useImagesBox.subwidgets[0].mouse_down = useImagesBox.subwidgets[1].mouse_down = mouse_down

        def mouse_down(e):
            CheckBox.mouse_down(useStyleBox.subwidgets[1], e)
            useImagesBox.mouse_down(e)
            self.useStyleBox_click(e)

        useStyleBox.subwidgets[0].mouse_down = useStyleBox.subwidgets[1].mouse_down = mouse_down

        showAllTags = CheckBoxLabel(title="Show all the tags in the tree",
                                    ref=config.nbtTreeSettings.showAllTags)

        col = Column((
            Label("NBT Tree Settings"),
            Row((useStyleBox, useTextBox, useImagesBox)),
            bulletFilePathFrame,
            showAllTags,
            Button("OK", action=self.dismiss),
        ))
        self.add(col)
        self.shrink_wrap()
        self.useStyleBox_click(None)
        self.defaultBulletImagesBox_click(None)

    def defaultBulletImagesBox_click(self, e):
        enabled = not config.nbtTreeSettings.defaultBulletImages.get() \
                    and config.nbtTreeSettings.useBulletImages.get() \
                    and config.nbtTreeSettings.useBulletStyles.get()
        for sub in self.bulletFilePath.subwidgets:
            sub.enabled = enabled
            if type(sub) == TextFieldWrapped:
                if enabled:
                    sub.fg_color = fg_color
                else:
                    sub.fg_color = disabled_color
        global bullet_image
        bullet_image = None

    def useStyleBox_click(self, e):
        for widget in (self.useTextBox, self.useImagesBox):
            for sub in widget.subwidgets:
                sub.enabled = config.nbtTreeSettings.useBulletStyles.get()
                if type(sub) in (CheckBox, TextFieldWrapped):
                    if config.nbtTreeSettings.useBulletStyles.get():
                        sub.fg_color = fg_color
                    else:
                        sub.fg_color = disabled_color
                if type(sub) == CheckBox:
                    sub.set_enabled(config.nbtTreeSettings.useBulletStyles.get())
        for sub in self.defaultBulletImagesBox.subwidgets:
            sub.enabled = config.nbtTreeSettings.useBulletImages.get()
            if type(sub) in (CheckBox, TextFieldWrapped):
                if config.nbtTreeSettings.useBulletImages.get():
                    sub.fg_color = fg_color
                else:
                    sub.fg_color = disabled_color
            if type(sub) == CheckBox:
                sub.set_enabled(config.nbtTreeSettings.useBulletImages.get())
        self.defaultBulletImagesBox_click(None)

    def open_bullet_file(self):
        fName = mcplatform.askOpenFile(title="Choose an image file...", suffixes=['png', 'jpg', 'bmp'])
        if fName:
            config.nbtTreeSettings.bulletFileName.set(fName)
            self.bulletFilePath.subwidgets[1].set_text(fName)
            self.bulletFilePath.subwidgets[1].commit(notify=True)
            global bullet_image
            bullet_image = None

    def dismiss(self, *args, **kwargs):
        bullet_styles = change_styles()
        if hasattr(self.tool, 'panel') and self.tool.panel is not None:
            self.tool.panel.tree.styles = bullet_styles
            self.tool.panel.tree.update_draw_bullets_methods(bullet_styles)
            self.tool.panel.tree.build_layout()
        ToolOptions.dismiss(self, *args, **kwargs)


# -----------------------------------------------------------------------------
# &# Prototype for blocks/items names
class SlotEditor(Dialog):
    def __init__(self, inventory, data, *args, **kwargs):
        Dialog.__init__(self, *args, **kwargs)
        self.inventory = inventory
        slot, id, count, damage = data
        self.former_id_text = id
        self.slot = slot
        self.id = TextFieldWrapped(text=str(id), doNotTranslate=True, width=300)
        self.id.change_action = self.text_entered
        self.id.escape_action = self.cancel
        self.id.enter_action = self.ok
        self.count = IntField(text="%s" % count, min=0, max=64)
        self.damage = IntField(text="%s" % damage, min=0, max=os.sys.maxint)
        header = Label(_("Inventory Slot #%s") % slot, doNotTranslate=True)
        row = Row([Label("id"), self.id,
                   Label("Count"), self.count,
                   Label("Damage"), self.damage,
                   ])

        self.matching_items = [mclangres.translate(k) for k in map_items.keys()]
        self.matching_items.sort()
        self.selected_item_index = None
        if id in self.matching_items:
            self.selected_item_index = self.matching_items.index(id)
        self.tableview = tableview = TableView(columns=[TableColumn("", 415, 'l')])
        tableview.num_rows = lambda: len(self.matching_items)
        tableview.row_data = lambda x: (self.matching_items[x],)
        tableview.row_is_selected = lambda x: x == self.selected_item_index
        tableview.click_row = self.select_tablerow

        buttons = Row([Button("Save", action=self.dismiss), Button("Cancel", action=self.cancel)])
        col = Column([header, row, tableview, buttons], spacing=2)
        self.add(col)
        self.shrink_wrap()

        try:
            self.tableview.rows.scroll_to_item(self.selected_item_index)
        except Exception, e:
            print e
            pass

    def ok(self, *args, **kwargs):
        self.id.set_text(self.matching_items[self.selected_item_index])
        kwargs['save'] = True
        self.dismiss(*args, **kwargs)

    def select_tablerow(self, i, e):
        old_index = self.selected_item_index
        self.selected_item_index = i
        if e.num_clicks > 1 and old_index == i:
            self.id.set_text(self.matching_items[self.selected_item_index])
            self.dismiss(save=True)

    def cancel(self, *args, **kwargs):
        kwargs['save'] = False
        self.dismiss(*args, **kwargs)

    def dismiss(self, *args, **kwargs):
        if kwargs.pop('save', True):
            data = [self.slot, self.id.text, self.count.text, self.damage.text]
            self.inventory.change_value(data)
        Dialog.dismiss(self, *args, **kwargs)

    def text_entered(self):
        text = self.id.get_text()
        if self.former_id_text == text:
            return
        results = []
        for k in map_items.keys():
            k = mclangres.translate(k)
            if text.lower() in k.lower():
                results.append(k)
        results.sort()
        self.matching_items = results
        self.selected_item_index = 0
        self.tableview.rows.scroll_to_item(self.selected_item_index)

    def dispatch_key(self, name, evt):
        super(SlotEditor, self).dispatch_key(name, evt)
        if name == "key_down":
            keyname = self.root.getKey(evt)
            if keyname == "Up" and self.selected_item_index > 0:
                self.selected_item_index -= 1

            elif keyname == "Down" and self.selected_item_index < len(self.matching_items) - 1:
                self.selected_item_index += 1
            elif keyname == 'Page down':
                self.selected_item_index = min(len(self.matching_items) - 1,
                                               self.selected_item_index + self.tableview.rows.num_rows())
            elif keyname == 'Page up':
                self.selected_item_index = max(0, self.selected_item_index - self.tableview.rows.num_rows())
            if self.tableview.rows.cell_to_item_no(0, 0) != None and (self.tableview.rows.cell_to_item_no(0,
                                                                                                          0) + self.tableview.rows.num_rows() - 1 > self.selected_item_index or self.tableview.rows.cell_to_item_no(
                0, 0) + self.tableview.rows.num_rows() - 1 < self.selected_item_index):
                self.tableview.rows.scroll_to_item(self.selected_item_index)


# &#


# -----------------------------------------------------------------------------
class NBTExplorerOperation(Operation):
    def __init__(self, toolPanel):
        super(NBTExplorerOperation, self).__init__(toolPanel.editor, toolPanel.editor.level)
        self.toolPanel = toolPanel
        self.tool = self.editor.nbtTool
        self.canUndo = False

    def extractUndo(self):
        if self.toolPanel.nbtObject.get(self.toolPanel.dataKeyName):
            return copy.deepcopy(self.toolPanel.nbtObject[self.toolPanel.dataKeyName])
        else:
            return copy.deepcopy(self.toolPanel.nbtObject)

    def perform(self, recordUndo=True):
        if self.toolPanel.nbtObject:

            if self.toolPanel.nbtObject.get(self.toolPanel.dataKeyName):
                orgNBT = self.toolPanel.nbtObject[self.toolPanel.dataKeyName]
            else:
                orgNBT = self.toolPanel.nbtObject
            newNBT = self.toolPanel.data

            if "%s" % orgNBT != "%s" % newNBT:
                if self.level.saving:
                    alert(_("Cannot perform action while saving is taking place"))
                    return
                if recordUndo:
                    self.canUndo = True
                    self.undoLevel = self.extractUndo()
                if self.toolPanel.nbtObject.get(self.toolPanel.dataKeyName):
                    self.toolPanel.nbtObject[self.toolPanel.dataKeyName] = self.toolPanel.data
                else:
                    self.toolPanel.bntObject = self.toolPanel.data

    def undo(self):
        if self.undoLevel:
            self.redoLevel = self.extractUndo()
            self.toolPanel.data.update(self.undoLevel)
            if self.toolPanel.nbtObject.get(self.toolPanel.dataKeyName):
                self.toolPanel.nbtObject[self.toolPanel.dataKeyName] = self.undoLevel
            else:
                self.toolPanel.nbtObject = self.undoLevel
            self.update_tool()

    def redo(self):
        if self.redoLevel:
            self.toolPanel.data.update(self.redoLevel)
            if self.toolPanel.nbtObject.get(self.toolPanel.dataKeyName):
                self.toolPanel.nbtObject[self.toolPanel.dataKeyName] = self.redoLevel
            else:
                self.toolPanel.nbtObject = self.redoLevel
            self.update_tool()

    def update_tool(self):
        toolPanel = self.tool.panel
        if toolPanel:
            index = toolPanel.tree.selected_item_index
            toolPanel.tree.build_layout()
            toolPanel.tree.selected_item_index = index
            if index is not None:
                item = toolPanel.tree.rows[index]
                toolPanel.tree.selected_item = item
                toolPanel.displayed_item = None
                toolPanel.update_side_panel(item)


# -----------------------------------------------------------------------------
class NBTExplorerToolPanel(Panel):
    """..."""

    def __init__(self, editor, nbtObject=None, fileName=None, savePolicy=0, dataKeyName='Data', close_text="Close",
                 load_text="Open", **kwargs):
        """..."""
        Panel.__init__(self, name='Panel.NBTExplorerToolPanel')
        self.editor = editor
        self.nbtObject = nbtObject
        self.fileName = fileName
        self.savePolicy = savePolicy
        self.displayed_item = None
        self.dataKeyName = dataKeyName
        self.copy_data = kwargs.get('copy_data', True)
        self.init_data()
        btns = []
        if load_text:
            btns.append(Button(load_text, action=self.editor.nbtTool.loadFile))
        btns += [
            Button({True: "Save", False: "OK"}[fileName != None], action=kwargs.get('ok_action', self.save_NBT),
                   tooltipText="Save your change in the NBT data."),
            Button("Reset", action=kwargs.get('reset_action', self.reset),
                   tooltipText="Reset ALL your changes in the NBT data."),
        ]
        if close_text:
            btns.append(Button(close_text, action=kwargs.get('close_action', self.close)))

        btnRow = Row(btns, margin=1, spacing=4)

        btnRow.shrink_wrap()
        self.btnRow = btnRow

        if kwargs.get('no_header', False):
            self.max_height = max_height = kwargs.get('height', editor.mainViewport.height - editor.toolbar.height -
                                                      editor.subwidgets[0].height) - (
                                               self.margin * 2) - btnRow.height - 2
        else:
            title = _("NBT Explorer")
            if fileName:
                title += " - %s" % os.path.split(fileName)[-1]
            header = Label(title, doNotTranslate=True)
            self.max_height = max_height = kwargs.get('height', editor.mainViewport.height - editor.toolbar.height -
                                                      editor.subwidgets[0].height) - header.height - (
                                               self.margin * 2) - btnRow.height - 2
        self.setCompounds()
        self.tree = NBTTree(height=max_height - btnRow.height - 2, inner_width=250, data=self.data,
                            compound_types=self.compounds,
                            copyBuffer=editor.nbtCopyBuffer, draw_zebra=False, _parent=self, styles=bullet_styles)
        self.tree.update_side_panel = self.update_side_panel
        self.side_panel_width = 350
        row = [self.tree, Column([Label("", width=self.side_panel_width), ], margin=0)]
        self.displayRow = Row(row, height=max_height, margin=0, spacing=0)
        if kwargs.get('no_header', False):
            self.add(Column([self.displayRow, btnRow], margin=0))
        else:
            self.add(Column([header, self.displayRow, btnRow], margin=0))
        self.shrink_wrap()
        self.side_panel = None
        # &# Prototype for Blocks/item names
        mclangres.buildResources(lang=getLang())

    def set_update_ui(self, v):
        Panel.set_update_ui(self, v)
        if v:
            mclangres.buildResources(lang=getLang())

    # &#

    def key_down(self, e):
        self.dispatch_key('key_down', e)

    def dispatch_key(self, event_name, e):
        if not hasattr(e, 'key'):
            return
        if event_name == 'key_down':
            caught = True
            keyname = self.root.getKey(e)
            if keyname == 'Escape':
                if not self.tree.has_focus():
                    self.tree.focus()
                else:
                    self.editor.key_down(e)
            elif self.side_panel and self.side_panel.has_focus():
                self.side_panel.dispatch_key(event_name, e)
            elif keyname == 'Return':
                self.tree.dispatch_key(event_name, e)
            else:
                caught = False
            if not caught:
                self.tree.dispatch_key(event_name, e)

    def setCompounds(self):
        if config.nbtTreeSettings.showAllTags.get():
            compounds = [TAG_Compound, TAG_List]
        else:
            compounds = [TAG_Compound, ]
        self.compounds = compounds

    def save_NBT(self):
        if self.fileName:
            self.editor.nbtTool.saveFile(self.fileName, self.data, self.savePolicy)
        else:
            op = NBTExplorerOperation(self)
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    def init_data(self):
        data = {}
        if self.nbtObject is None and hasattr(self.editor.level, 'root_tag'):
            self.nbtObject = self.editor.level.root_tag
            self.copy_data = False
        if self.nbtObject:
            if self.nbtObject.get('Data'):
                if self.copy_data:
                    data = copy.deepcopy(self.nbtObject[self.dataKeyName])
                else:
                    data = self.nbtObject[self.dataKeyName]
            else:
                if self.copy_data:
                    data = copy.deepcopy(self.nbtObject)
                else:
                    data = self.nbtObject

        self.data = data
        self.setCompounds()
        if hasattr(self, 'tree'):
            self.tree.set_parent(None)
            self.tree = NBTTree(height=self.max_height - self.btnRow.height - 2, inner_width=250, data=self.data,
                                compound_types=self.compounds,
                                copyBuffer=self.editor.nbtCopyBuffer, draw_zebra=False, _parent=self,
                                styles=bullet_styles)
            self.displayRow.subwidgets[0].subwidgets.insert(0, self.tree)
            self.tree.set_parent(self.displayRow.subwidgets[0])

    def reset(self):
        self.editor.nbtTool.hidePanel()
        self.editor.nbtTool.showPanel()

    def close(self):
        self.editor.toolbar.selectTool(0)
        self.editor.nbtTool.hidePanel()

    def update_side_panel(self, item):
        if item == self.displayed_item:
            return
        self.displayed_item = item
        if self.side_panel:
            self.side_panel.set_parent(None)
        items = [a for a in item[1]]
        rows = []
        if config.nbtTreeSettings.showAllTags.get():
            meth = None
        else:
            meth = getattr(self, 'build_%s' % item[3].lower(), None)
        col = True
        if meth and len(items) == 1:
            rows = meth(items)
        else:
            height = 0
            for itm in items:
                t = itm.__class__.__name__
                rows.append(Row([Label("Data Type:"), Label(t)], margin=1))
                fields = self.build_field(itm)
                for field in fields:
                    if type(field) == TextFieldWrapped:
                        field.set_size_for_text(self.side_panel_width)
                    row = Row([field, ], margin=1)
                    rows.append(row)
                    height += row.height
            if height > self.displayRow.height:
                col = False
        if rows:
            if col:
                col = Column(rows, align='l', spacing=0, height=self.displayRow.height)
            else:
                col = ScrollPanel(rows=rows, align='l', spacing=0, height=self.displayRow.height, draw_zebra=False,
                                  inner_width=self.side_panel_width - scroll_button_size)
            col.set_parent(self.displayRow)
            col.top = self.displayRow.top
            col.left = self.displayRow.subwidgets[0].right
            col.bottom = self.displayRow.subwidgets[0].bottom
            col.shrink_wrap()
            self.side_panel = col

    @staticmethod
    def build_field(itm):
        fields = []
        if type(itm) in field_types.keys():
            f, bounds = field_types[type(itm)]
            if bounds:
                fields = [f(ref=AttrRef(itm, 'value'), min=bounds[0], max=bounds[1]), ]
            else:
                fields = [f(ref=AttrRef(itm, 'value')), ]
        elif type(itm) in array_types.keys():
            idx = 0
            for _itm in itm.value.tolist():
                f, bounds = array_types[type(itm)]
                fields.append(f(ref=ItemRef(itm.value, idx)))
                idx += 1
        elif type(itm) in (TAG_Compound, TAG_List):
            for _itm in itm.value:
                fields.append(
                    Label("%s" % (_itm.name or "%s #%03d" % (itm.name or _("Item"), itm.value.index(_itm))), align='l',
                          doNotTranslate=True))
                fields += NBTExplorerToolPanel.build_field(_itm)
        elif type(itm) not in (str, unicode):
            if type(getattr(itm, 'value', itm)) not in (str, unicode, int, float):
                fld = Label
                kw = {'align': 'l'}
            else:
                fld = TextFieldWrapped
                kw = {}
            fields = [fld("%s" % getattr(itm, 'value', itm), doNotTranslate=True, **kw), ]
        else:
            fields = [TextFieldWrapped("%s" % itm, doNotTranslata=True), ]
        return fields

    @staticmethod
    def build_attributes(items):
        rows = []
        attributes = items[0]
        names = [a['Name'].value for a in attributes]
        indexes = [] + names
        names.sort()
        for name in names:
            item = attributes[indexes.index(name)]
            rows.append(Row([Label(name.split('.')[-1], align='l')] + NBTExplorerToolPanel.build_field(item['Base']),
                            margin=0))
            mods = item.get('Modifiers', [])
            for mod in mods:
                keys = mod.keys()
                keys.remove('Name')
                rows.append(Row([Label("-> Name", align='l')] + NBTExplorerToolPanel.build_field(mod['Name']),
                                margin=0))
                keys.sort()
                for key in keys:
                    rows.append(Row(
                        [Label('    %s' % key, align='l', doNotTranslate=True, tooltipText=mod[key].__class__.__name__)] \
                        + NBTExplorerToolPanel.build_field(mod[key]),
                        margin=0))
        return rows

    def build_motion(self, items):
        return self.build_pos(items)

    @staticmethod
    def build_pos(items):
        rows = []
        pos = items[0]
        rows.append(Row([Label("X", align='l'), FloatField(ref=AttrRef(pos[0], 'value'))]))
        rows.append(Row([Label("Y", align='l'), FloatField(ref=AttrRef(pos[1], 'value'))]))
        rows.append(Row([Label("Z", align='l'), FloatField(ref=AttrRef(pos[2], 'value'))]))
        return rows

    @staticmethod
    def build_rotation(items):
        rows = []
        rotation = items[0]
        rows.append(Row([Label("Y", align='l'), FloatField(ref=AttrRef(rotation[0], 'value'))]))
        rows.append(Row([Label("X", align='l'), FloatField(ref=AttrRef(rotation[1], 'value'))]))
        return rows

    def build_inventory(self, items):
        parent = self.tree.get_item_parent(self.displayed_item)
        if parent:
            parent = parent[9]
        else:
            parent = self.data
        if 'playerGameType' in parent.keys():
            player = True
        else:
            player = False
        inventory = parent.get('Inventory', TAG_List())
        rows = []
        items = items[0]
        slots = [["%s" % i, "", "0", "0"] for i in range(36)]
        slots += [["%s" % i, "", "0", "0"] for i in range(100, 104)]
        slots_set = []
        for item, i in zip(items, range(len(items))):
            # &# Prototype for blocks/items names
            item_dict = mcitems.items.get(item['id'].value, None)
            if item_dict is None:
                item_name = item['id'].value
            else:
                if type(item_dict['name']) == list:
                    if int(item['Damage'].value) >= len(item_dict['name']):
                        block_id = map_block.get(item['id'].value, None)
                        item_name = alphaMaterials.get((int(block_id), int(item['Damage'].value))).name.rsplit('(', 1)[
                            0].strip()
                    else:
                        item_name = item_dict['name'][int(item['Damage'].value)]
                else:
                    item_name = item_dict['name']
            s = i
            _s = 0 + i
            if player:
                s = int(item['Slot'].value)
                _s = 0 + s
            slots_set.append(s)
            if s >= 100:
                s = s - 100 + 36
            if type(item_name) in (unicode, str):
                translated_item_name = mclangres.translate(item_name)
            else:
                translated_item_name = item_name
            slots[s] = _s, translated_item_name, item['Count'].value, item['Damage'].value
            # slots[s] = item['Slot'].value, item['id'].value.split(':')[-1], item['Count'].value, item['Damage'].value
            # &#
        width = self.side_panel_width - self.margin * 5
        c0w = max(15, self.font.size("000")[0]) + 4
        c2w = max(15, self.font.size("00")[0]) + 4
        c3w = max(15, self.font.size("000")[0]) + 4
        c1w = width - c0w - c2w - c3w
        font_height = self.font.size("qd")[1]
        tableCols = [TableColumn("#", c0w),
                     TableColumn("ID", c1w),
                     TableColumn("C", c2w),
                     TableColumn("D", c3w),
                     ]
        height = self.displayRow.subwidgets[0].height
        table = TableView(height=height - (self.margin * 2),
                          width=width,
                          nrows=((height - (self.margin * 2) - font_height / 2) / font_height),
                          columns=tableCols,
                          row_height=font_height,
                          header_height=font_height / 2)
        table.rows.tooltipText = "Double-click to edit"
        table.selected_row = None
        table.slots = slots

        def num_rows():
            return len(slots)

        table.num_rows = num_rows

        def row_data(n):
            return slots[n]

        table.row_data = row_data

        def click_row(n, e):
            table.focus()
            table.selected_row = n
            if e.num_clicks > 1:
                SlotEditor(table, row_data(n)).present()

        table.click_row = click_row

        def row_is_selected(n):
            return n == table.selected_row

        table.row_is_selected = row_is_selected

        def change_value(data):
            s, i, c, d = data
            s = int(s)
            s_idx = 0
            # &# Prototype for blocks/items names
            name, state = map_items.get(mclangres.untranslate(i), (i, '0'))
            if ':' not in name:
                name = 'minecraft:%s' % name
            # &#

            if s in slots_set:
                for slot in inventory:
                    ok1 = False
                    if player:
                        ok1 = slot['Slot'].value == s
                    else:
                        ok1 = inventory.index(slot) == s
                    if ok1:
                        if not i or int(c) < 1:
                            del inventory[s_idx]
                            i = ""
                            c = u'0'
                            d = u'0'
                        else:
                            # &# Prototype for blocks/items names
                            # slot['id'].value = 'minecraft:%s'%i
                            slot['id'].value = name
                            # &#
                            slot['Count'].value = int(c)
                            slot['Damage'].value = int(state)
                        break
                    s_idx += 1
            else:
                new_slot = TAG_Compound()
                if player:
                    new_slot['Slot'] = TAG_Byte(s)
                # &# Prototype for blocka/items names
                # new_slot['id'] = TAG_String('minecraft:%s'%i)
                new_slot['id'] = TAG_String(name)
                # &#
                new_slot['Count'] = TAG_Byte(int(c))
                new_slot['Damage'] = TAG_Short(int(state))
                idx = s
                for slot in inventory:
                    ok2 = False
                    if player:
                        ok2 = slot['Slot'].value >= s
                    else:
                        ok2 = inventory.index(slot) >= s
                    if ok2:
                        idx = slot['Slot'].value
                        break
                inventory.insert(s, new_slot)
                slots_set.append(s)
                # &# Prototype for blocks/items names
            #            if i == name:
            #                i = name
            # &#
            if s >= 100:
                n = s - 100 + 36
            else:
                n = s
            table.slots[n] = slots[n] = s, i, c, state

        table.change_value = change_value

        def dispatch_key(name, evt):
            keyname = self.root.getKey(evt)
            if keyname == 'Return':
                SlotEditor(table, row_data(table.selected_row)).present()
            elif keyname == "Up" and table.selected_row > 0:
                table.selected_row -= 1
                table.rows.scroll_to_item(table.selected_row)

            elif keyname == "Down" and table.selected_row < len(slots) - 1:
                table.selected_row += 1
                table.rows.scroll_to_item(table.selected_row)
            elif keyname == 'Page down':
                table.selected_row = min(len(slots) - 1, table.selected_row + table.rows.num_rows())
            elif keyname == 'Page up':
                table.selected_row = max(0, table.selected_row - table.rows.num_rows())
            someRowBool = table.rows.cell_to_item_no(0, 0) + table.rows.num_rows() - 1 != table.selected_row
            if table.rows.cell_to_item_no(0, 0) is not None and someRowBool:
                table.rows.scroll_to_item(table.selected_row)

        table.dispatch_key = dispatch_key

        rows.append(table)
        return rows


# -----------------------------------------------------------------------------
class NBTExplorerTool(EditorTool):
    """..."""
    tooltipText = "NBT Explorer\nDive into level NBT structure.\nRight-click for options"
    _alreadyHidden = False

    @property
    def alreadyHidden(self):
        return NBTExplorerTool._alreadyHidden

    @alreadyHidden.setter
    def alreadyHidden(self, v):
        NBTExplorerTool._alreadyHidden = v

    def __init__(self, editor):
        """..."""
        self.optionsPanel = NBTExplorerOptions(self)
        self.toolIconName = 'nbtexplorer'
        self.editor = editor
        self.editor.nbtTool = self

    def toolSelected(self):
        self.showPanel()

    def toolReselected(self):
        self.showPanel()

    def showPanel(self, fName=None, nbtObject=None, savePolicy=0, dataKeyName='Data'):
        """..."""
        if self.panel is None and self.editor.currentTool in (self, None):  # or nbtObject:
            # !# BAD HACK
            try:
                class fakeStdErr:
                    def __init__(self, *args, **kwargs): pass

                    def write(self, *args, **kwargs): pass

                stderr = os.sys.stderr
                os.sys.stderr = fakeStdErr()
                os.sys.stderr = stderr
            except:
                alert("Unattended data. File not loaded")
                return
            # !#
            self.panel = NBTExplorerToolPanel(self.editor, nbtObject=nbtObject, fileName=fName,
                                              savePolicy=savePolicy, dataKeyName=dataKeyName)
            self.panel.centery = (self.editor.mainViewport.height - self.editor.toolbar.height) / 2 + \
                                 self.editor.subwidgets[0].height
            self.panel.left = self.editor.left
            self.editor.add(self.panel)

    def loadFile(self, fName=None):
        nbtObject, dataKeyName, savePolicy, fName = loadFile(fName)
        if nbtObject is not None:
            self.editor.toolbar.removeToolPanels()
            self.editor.currentTool = self
            self.showPanel(fName, nbtObject, savePolicy, dataKeyName)
        self.optionsPanel.dismiss()

    def saveFile(self, fName, data, savePolicy):
        saveFile(fName, data, savePolicy)

    def keyDown(self, *args, **kwargs):
        if self.panel:
            self.panel.key_down(*args, **kwargs)


# ------------------------------------------------------------------------------
def loadFile(fName):
    if not fName:
        fName = mcplatform.askOpenFile(title=_("Select a NBT (.dat) file..."), suffixes=['dat', ])
    if fName:
        if not os.path.isfile(fName):
            alert("The selected object is not a file.\nCan't load it.")
            return
        savePolicy = 0
        data = open(fName).read()

        if struct.Struct('<i').unpack(data[:4])[0] in (3, 4):
            if struct.Struct('<i').unpack(data[4:8])[0] != len(data[8:]):
                raise NBTFormatError()
            with littleEndianNBT():
                nbtObject = load(buf=data[8:])
            savePolicy = 1
        elif struct.Struct('<i').unpack(data[:4])[0] in (1, 2):
            alert(_("Old PE level.dat, unsupported at the moment."))
        else:
            nbtObject = load(buf=data)
        if fName.endswith('.schematic'):
            nbtObject = TAG_Compound(name='Data', value=nbtObject)
            savePolicy = -1
            dataKeyName = 'Data'
        elif nbtObject.get('Data', None):
            dataKeyName = 'Data'
        elif nbtObject.get('data', None):
            dataKeyName = 'data'
        else:
            nbtObject.name = 'Data'
            dataKeyName = 'Data'
            if savePolicy == 0:
                savePolicy = -1
            nbtObject = TAG_Compound([nbtObject, ])
        return nbtObject, dataKeyName, savePolicy, fName
    return [None] * 4


def saveFile(fName, data, savePolicy):
    if fName is None:
        return
    if os.path.exists(fName):
        r = ask("File already exists.\nClick 'OK' to choose one.")
        if r == 'OK':
            folder, name = os.path.split(fName)
            suffix = os.path.splitext(name)[-1][1:]
            fName = mcplatform.askSaveFile(folder, "Choose a NBT file...", name, 'Folder\0*.dat\0*.*\0\0', suffix)
        else:
            return
    if savePolicy == -1:
        if hasattr(data, 'name'):
            data.name = ""
    if not os.path.isdir(fName):
        if savePolicy <= 0:
            data.save(fName)
        elif savePolicy == 1:
            with littleEndianNBT():
                toSave = data.save(compressed=False)
                toSave = struct.Struct('<i').pack(4) + struct.Struct('<i').pack(len(toSave)) + toSave
                with open(fName, 'w') as f:
                    f.write(toSave)
    else:
        alert("The selected object is not a file.\nCan't save it.")
