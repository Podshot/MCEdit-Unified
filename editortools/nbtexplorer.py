# -*- coding: utf-8 -*-
#
# nbtexplorer.py
#
# D.C.-G. (LaChal) 2014
#
# Display NBT structure
#
#
from pygame import key, draw, image, Rect
from albow import Column, Row, Label, Tree, TableView, TableColumn, Button, \
    FloatField, IntField, TextFieldWrapped, AttrRef
from albow.utils import blit_in_rect
from albow.translate import _
from glbackground import Panel
from pymclevel.nbt import load, TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, \
     TAG_Double, TAG_String, TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, \
     TAG_Short_Array
from albow.theme import root
scroll_button_size = 0 + root.PaletteView.scroll_button_size
bullet_color_active = root.Tree.bullet_color_active
del root
from editortools.editortool import EditorTool
from editortools.operation import Operation
from editortools.tooloptions import ToolOptions
import copy
from directories import getDataDir
import os
from mcplatform import askOpenFile, askSaveFile

#-----------------------------------------------------------------------------
USE_BULLET_STYLES = True
USE_BULLET_TEXT = False
USE_BULLET_IMAGES = True
BULLET_FILE_NAME = 'Nbtsheet.png'

bullet_image = None

def get_bullet_image(index, w=16, h=16):
    global bullet_image
    if not bullet_image:
        bullet_image = image.load(os.path.join(getDataDir(), BULLET_FILE_NAME))
    r =  Rect(0, 0, w, h)
    line_length = int(bullet_image.get_width() / w)
    num_lines = int(bullet_image.get_height() / h)
    line = int(index / line_length)
    r.top = line * h
    r.left = (index - (line * line_length)) * w
    return bullet_image.subsurface(r)

styles = {TAG_Byte: ((20,20,200), None, 'circle', 'b'),
          TAG_Double: ((20,200,20), None, 'circle', 'd'),
          TAG_Float: ((200,20,20), None, 'circle', 'f'),
          TAG_Int: ((16,160,160), None, 'circle', 'i'),
          TAG_Long: ((200,20,200), None, 'circle', 'l'),
          TAG_Short: ((200,200,20), (0,0,0), 'circle', 's'),
          TAG_String: ((60,60,60), None, 'circle', 's'),
          TAG_Compound: (bullet_color_active, None, '', ''),
          TAG_Byte_Array: ((20,20,200), None, 'square', 'B'),
          TAG_Int_Array: ((16,160,160), None, 'square', 'I'),
          TAG_List: ((200,200,200), (0,0,0), 'square', 'L'),
          TAG_Short_Array: ((200,200,20), None, 'square', 'S'),
          }

if USE_BULLET_IMAGES and os.path.exists(os.path.join(getDataDir(), BULLET_FILE_NAME)):
    i = 0
    for key in (TAG_Byte, TAG_Double, TAG_Float, TAG_Int, TAG_Long, TAG_Short, TAG_String, TAG_Compound, TAG_Byte_Array, TAG_Int_Array, TAG_List):
        styles[key] = (get_bullet_image(i), None, 'image', '')
        i += 1

    styles[TAG_Short_Array] = styles[TAG_Int_Array]


#-----------------------------------------------------------------------------
field_types = {TAG_Byte: (IntField, (0, 256)),
             TAG_Double: (FloatField, None),
             TAG_Float: (FloatField, None),
             TAG_Int: (IntField, (-2147483647,+2147483647)),
             TAG_Long: (IntField, (-9223372036854775807,+9223372036854775807)),
             TAG_Short: (IntField, (0, 65536)),
             TAG_String: (TextFieldWrapped, None),
            }


#-----------------------------------------------------------------------------
class NBTTree(Tree):
    def __init__(self, *args, **kwargs):
        self._parent = kwargs.pop('_parent', None)
        styles = kwargs.get('styles', {})
        for key in styles.keys():
            if hasattr(key, '__name__'):
                name = key.__name__
            elif type(key) in (str, unicode):
                name = key
            else:
                name = repr(key)
            setattr(self, 'draw_%s_bullet'%name, self.draw_TAG_bullet)
        Tree.__init__(self, *args, **kwargs)

    def click_item(self, *args, **kwargs):
        Tree.click_item(self, *args, **kwargs)
        if self._parent:
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

    def draw_TAG_bullet(self, surf, bg, fg, shape, text):
        r = self.get_bullet_rect(surf)
        meth = getattr(self, 'draw_%s'%shape, None)
        if meth and USE_BULLET_STYLES:
            meth(surf, bg, r)
        else:
            self.draw_deadend_bullet(surf, self.bullet_color_inactive, fg, shape, text)
        if text and USE_BULLET_TEXT:
            buf = self.font.render(text, True, fg or self.fg_color)
            blit_in_rect(surf, buf, r, 'c')

    if USE_BULLET_STYLES and styles.get(TAG_Compound, [''] * 4)[2] != '':
        draw_opened_bullet = draw_closed_bullet = draw_TAG_bullet

#-----------------------------------------------------------------------------
class NBTExplorerOptions(ToolOptions):
    def __init__(self, tool):
        Panel.__init__(self)
        
        col = Column((Button("Load file", action=tool.loadFile), Button("OK", action=self.dismiss),))
        self.add(col)
        self.shrink_wrap()

#-----------------------------------------------------------------------------
class SlotEditor(Panel):
    def __init__(self, inventory, data):
        Panel.__init__(self)
        self.inventory = inventory
        slot, id, count, damage = data
        self.slot = slot
        self.id = TextFieldWrapped(text=id, doNotTranslate=True, width=300)
        self.count = IntField(text="%s"%count, min=-64, max=64)
        self.damage = IntField(text="%s"%damage, min=-32768, max=32767)
        header = Label(_("Inventory Slot #%s")%slot, doNotTranslate=True)
        row = Row([Label("id"), self.id,
                   Label("Count"), self.count,
                   Label("Damage"), self.damage,
                   ])
        buttons = Row([Button("Save", action=self.dismiss), Button("Cancel", action=self.cancel)])
        col = Column([header, row, buttons], spacing=2)
        self.add(col)
        self.shrink_wrap()

    def cancel(self, *args, **kwargs):
        kwargs['save'] = False
        self.dismiss(*args, **kwargs)

    def dismiss(self, *args, **kwargs):
        if kwargs.pop('save', True):
            data = [self.slot, self.id.text, self.count.text, self.damage.text]
            self.inventory.change_value(data)
        Panel.dismiss(self, *args, **kwargs)


#-----------------------------------------------------------------------------
class NBTExplorerOperation(Operation):
    def __init__(self, toolPanel):
        super(NBTExplorerOperation, self).__init__(toolPanel.editor, toolPanel.editor.level)
        self.toolPanel = toolPanel
        self.tool = self.editor.nbtTool
        self.canUndo = False

    def extractUndo(self):
        return copy.deepcopy(self.toolPanel.nbtObject['Data'])

    def perform(self, recordUndo=True):
        if self.toolPanel.nbtObject:

            orgNBT = self.toolPanel.nbtObject['Data']
            newNBT = self.toolPanel.data
#            print "%s"%orgNBT == "%s"%newNBT, orgNBT == newNBT

            if "%s"%orgNBT != "%s"%newNBT:
                if self.level.saving:
                    alert(_("Cannot perform action while saving is taking place"))
                    return
                if recordUndo:
                    self.canUndo = True
                    self.undoLevel = self.extractUndo()
                self.toolPanel.nbtObject['Data'].update(self.toolPanel.data)

    def undo(self):
        if self.undoLevel:
            self.redoLevel = self.extractUndo()
            self.toolPanel.data.update(self.undoLevel)
            self.toolPanel.nbtObject['Data'].update(self.undoLevel)
            self.update_tool()

    def redo(self):
        if self.redoLevel:
            self.toolPanel.data.update(self.redoLevel)
            self.toolPanel.nbtObject['Data'].update(self.redoLevel)
            self.update_tool()

    def update_tool(self):
        toolPanel = self.tool.panel
        if toolPanel:
            index = toolPanel.tree.selected_item_index
            toolPanel.tree.build_layout()
            toolPanel.tree.selected_item_index = index
            item = toolPanel.tree.rows[index]
            toolPanel.tree.selected_item = item
            toolPanel.displayed_item = None
            toolPanel.update_side_panel(item)

#-----------------------------------------------------------------------------
class NBTExplorerToolPanel(Panel):
    """..."""
    def __init__(self, editor, nbtObject=None, fileName=None, dontSaveRootTag=False):
        """..."""
        Panel.__init__(self)
        self.editor = editor
        self.nbtObject = nbtObject
        self.fileName = fileName
        self.dontSaveRootTag = dontSaveRootTag
        self.displayed_item = None
        self.init_data()
        header = Label("NBT Explorer")
        self.max_height = max_height = editor.mainViewport.height - editor.toolbar.height - editor.subwidgets[0].height - editor.statusLabel.height - header.height - (self.margin * 2)
        self.tree = NBTTree(height=max_height, inner_width=250, data=self.data, compound_types=[TAG_Compound], draw_zebra=False, _parent=self, styles=styles)
        col = Column([self.tree,
                      Row([
                           Button("OK", action=self.save_NBT, tooltipText="Save your change in the NBT data."),
                           Button("Reset", action=self.reset, tooltipText="Reset ALL your changes in the NBT data."),
                           Button("Close", action=self.close),
                          ],
                          margin=1, spacing=4,
                         )
                     ],
                     margin=0, spacing=2)
        col.shrink_wrap()
        row = [col, Column([Label("", width=300), ], height=max_height)]
        self.add(Column([header, Row(row)]))
        self.shrink_wrap()
        self.side_panel = None

    def save_NBT(self):
#        if hasattr(self.editor.level, 'root_tag'):
#            self.editor.level.root_tag['Data'].update(self.data)
        op = NBTExplorerOperation(self)
        self.editor.addOperation(op)
        if op.canUndo:
            self.editor.addUnsavedEdit()
        if self.fileName:
            self.editor.nbtTool.saveFile(self.fileName, self.data)

    def init_data(self):
        data = {}
        if self.nbtObject == None and hasattr(self.editor.level, 'root_tag'):
            self.nbtObject = self.editor.level.root_tag
        if self.nbtObject:
            data = copy.deepcopy(self.nbtObject['Data'])
        self.data = data

    def reset(self):
        self.editor.nbtTool.hidePanel()
        self.editor.nbtTool.showPanel()

    def close(self):
        self.editor.toolbar.selectTool(0)
        self.editor.nbtTool.hidePanel()

    def update_side_panel(self, item):
#        print item == self.displayed_item
        if item == self.displayed_item:
            return
        self.displayed_item = item
        if self.side_panel:
            self.side_panel.set_parent(None)
        items = item[2]
        rows = []
        meth = getattr(self, 'build_%s'%item[1].lower(), None)
        if meth and len(items) == 1:
            rows = meth(items)
        else:
            for itm in items:
                t = itm.__class__.__name__
                rows.append(Row([Label("Data Type:"), Label(t)]))
                field = self.build_field(itm)
                if type(field) == TextFieldWrapped:
                    field.set_size_for_text(300)
                row = Row([field,])
                rows.append(row)
        if rows:
            col = Column(rows, align='l', spacing=0, height=self.subwidgets[0].subwidgets[1].height)
            col.set_parent(self.subwidgets[0].subwidgets[1])
            col.top = self.subwidgets[0].subwidgets[1].top
            col.left = self.subwidgets[0].subwidgets[1].subwidgets[0].right
            col.bottom = self.subwidgets[0].subwidgets[1].subwidgets[0].bottom
            col.shrink_wrap()
            self.side_panel = col

    @staticmethod
    def build_field(itm):
        if type(itm) in field_types.keys():
            f, bounds = field_types[type(itm)]
            if bounds:
                field = f(ref=AttrRef(itm, 'value'), min=bounds[0], max=bounds[1])
            else:
                field = f(ref=AttrRef(itm, 'value'))
        else:
            field = Label("%s"%itm.value, align='l', doNotTranslate=True)
        return field

    @staticmethod
    def build_attributes(items):
        rows = []
        attributes = items[0]
        names = [a['Name'].value for a in attributes]
        indexes = [] + names
        names.sort()
        for name in names:
            item = attributes[indexes.index(name)]
            rows.append(Row([Label(name.split('.')[-1], align='l'), NBTExplorerToolPanel.build_field(item['Base'])],
                            margin=0))
            mods = item.get('Modifiers', [])
            for mod in mods:
                keys = mod.keys()
                keys.remove('Name')
                rows.append(Row([Label("-> Name", align='l'), NBTExplorerToolPanel.build_field(mod['Name'])],
                                 margin=0))
                keys.sort()
                for key in keys:
                    rows.append(Row([Label('    %s'%key, align='l', doNotTranslate=True, tooltipText=mod[key].__class__.__name__),
                                     NBTExplorerToolPanel.build_field(mod[key])],
                                    margin=0))
        return rows

    def build_motion(self, items):
        return self.build_pos(items)

    @staticmethod
    def build_pos(items):
        rows = []
        pos = items[0]
        rows.append(Row([Label("X", align='l'), Label("%s"%pos[0].value, align='l')]))
        rows.append(Row([Label("Y", align='l'), Label("%s"%pos[1].value, align='l')]))
        rows.append(Row([Label("Z", align='l'), Label("%s"%pos[2].value, align='l')]))
        return rows

    @staticmethod
    def build_rotation(items):
        rows = []
        rotation = items[0]
        rows.append(Row([Label("Y", align='l'), Label("%s"%rotation[0].value, align='l')]))
        rows.append(Row([Label("X", align='l'), Label("%s"%rotation[1].value, align='l')]))
        return rows

    def build_inventory(self, items):
        rows = []
        items = items[0]
        slots = [["%s"%i,"","0","0"] for i in range(36)]
        for item in items:
            s = int(item['Slot'].value)
            slots[s] = item['Slot'].value, item['id'].value.split(':')[-1], item['Count'].value, item['Damage'].value
        width = self.width / 2 - self.margin * 4
        c0w = max(15, self.font.size("00")[0]) + 4
        c2w = max(15, self.font.size("00")[0]) + 4
        c3w = max(15, self.font.size("000")[0]) + 4
        c1w = width - c0w - c2w - c3w
        font_height = self.font.size("qd")[1]
        tableCols = [TableColumn("#", c0w),
                     TableColumn("ID", c1w),
                     TableColumn("C", c2w),
                     TableColumn("D", c3w),
                     ]
        height = self.subwidgets[0].subwidgets[1].subwidgets[0].height
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
            table.selected_row = n
            if e.num_clicks > 1:
                SlotEditor(table, row_data(n)).present()
        table.click_row = click_row

        def row_is_selected(n):
            return n == table.selected_row
        table.row_is_selected = row_is_selected

        def change_value(data):
            s, i, c, d = data
            table.slots[s] = slots[s] = data
            for slot in self.data['Player']['Inventory']:
                if slot['Slot'].value == s:
                    slot['id'].value = 'minecraft:%s'%i
                    slot['Count'].value = int(c)
                    slot['Damage'].value = int(d)
        table.change_value = change_value
        rows.append(table)
        return rows


#-----------------------------------------------------------------------------
class NBTExplorerTool(EditorTool):
    """..."""
    tooltipText = "NBT Explorer\nDive into level NBT structure."

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

    def showPanel(self, fName=None, nbtObject=None, dontSaveRootTag=False):
        """..."""
        if (self.panel is None and self.editor.currentTool in (self, None)): # or nbtObject:
            self.panel = NBTExplorerToolPanel(self.editor, nbtObject=nbtObject, fileName=fName, dontSaveRootTag=dontSaveRootTag)
            self.panel.left = self.editor.left
            self.panel.centery = self.editor.centery
            self.editor.add(self.panel)

    def loadFile(self, fName=None):
        if not fName:
            fName = askOpenFile(title="Select a NBT (.dat) file...", suffixes=['dat',])
            if fName:
                dontSaveRootTag = False
                nbtObject = load(fName)
                if not nbtObject.get('Data', None):
                    nbtObject.name = 'Data'
                    dontSaveRootTag = True
                    nbtObject = TAG_Compound([nbtObject,])
                self.editor.currentTool = self
                self.showPanel(fName, nbtObject, dontSaveRootTag)
                self.optionsPanel.dismiss()

    def saveFile(self, fName, data):
        pass

