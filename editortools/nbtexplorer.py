# -*- coding: utf-8 -*-
#
# nbtexplorer.py
#
# D.C.-G. (LaChal) 2014
#
# Display NBT structure
#
from pygame import key, draw
from albow import Column, Row, Label, Tree, TableView, TableColumn, Button, \
    FloatField, IntField, TextFieldWrapped
from albow.theme import root
scroll_button_size = 0 + root.PaletteView.scroll_button_size
del root
from albow.utils import blit_in_rect
from albow.translate import _
from glbackground import Panel
from pymclevel.nbt import load, TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, \
     TAG_Double, TAG_String, TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, \
     TAG_Short_Array
from editortools.editortool import EditorTool
import copy

#-----------------------------------------------------------------------------
USE_BULLET_STYLES = False
USE_BULLET_TEXT = False

styles = {TAG_Byte: ((20,20,200), None, 'circle', 'b'),
          TAG_Byte_Array: ((20,20,200), None, 'square', 'B'),
          TAG_Double: ((20,200,20), None, 'circle', 'd'),
          TAG_Float: ((200,20,20), None, 'circle', 'f'),
          TAG_Int: ((16,160,160), None, 'circle', 'i'),
          TAG_Int_Array: ((16,160,160), None, 'square', 'I'),
          TAG_List: ((200,200,200), (0,0,0), 'square', 'L'),
          TAG_Long: ((200,20,200), None, 'circle', 'l'),
          TAG_Short: ((200,200,20), (0,0,0), 'circle', 's'),
          TAG_Short_Array: ((200,200,20), None, 'square', 'S'),
          TAG_String: ((60,60,60), None, 'circle', 's'),
          }


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

    def draw_square(self, surf, bg, r):
        draw.polygon(surf, bg, [r.topleft, r.topright, r.bottomright, r.bottomleft])

    def draw_circle(self, surf, bg, r):
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
class NBTExplorerToolPanel(Panel):
    """..."""
    def __init__(self, editor):
        """..."""
        Panel.__init__(self)
        self.editor = editor
        self.displayed_item = None
        self.init_data()
        header = Label("NBT Explorer")
        self.max_height = max_height = editor.mainViewport.height - editor.toolbar.height - editor.subwidgets[0].height - editor.statusLabel.height - header.height - (self.margin * 2)
        self.tree = NBTTree(height=max_height, inner_width=250, data=self.data, compound_types=[TAG_Compound], draw_zebra=False, _parent=self, styles=styles)
        col = Column([self.tree,
                      Row([
                           Button("Save", action=self.save_NBT),
                           Button("Reset", action=self.reset, tooltipText="Reset ALL your changes in the NBT data."),
                           Button("Close", action=self.close),
                          ],
                          margin=1, spacing=4,
                         )
                     ],
                     margin=0, spacing=2)
        col.shrink_wrap()
        row = [col,]
        row.append(Column([Label("", width=300),], height=max_height))
        self.add(Column([header, Row(row)]))
        self.shrink_wrap()
        self.side_panel = None

    def save_NBT(self):
        if hasattr(self.editor.level, 'root_tag'):
            self.editor.level.root_tag['Data'].update(self.data)

    def init_data(self):
        data = {}
        if hasattr(self.editor.level, 'root_tag'):
            data = copy.deepcopy(self.editor.level.root_tag['Data'])
        self.data = data

    def reset(self):
        self.editor.nbtTool.hidePanel()
        self.editor.nbtTool.showPanel()

    def close(self):
        self.parent.nbtTool.hidePanel()

    def key_down(self, evt):
        if key.name(evt.key) == 'escape':
            self.dismiss()
        else:
            self.editor.key_down(evt)

    def key_up(self, evt):
        self.editor.key_up(evt)

    def mouse_down(self, e):
        if e not in self:
            self.dismiss()

    def update_side_panel(self, item):
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
                if type(itm) in field_types.keys():
                    f, bounds = field_types[type(itm)]
                    if f == TextFieldWrapped:
                        field = f(text=itm.value, width=300)
                    if bounds:
                        field = f(text="%s"%itm.value, min=bounds[0], max=bounds[1])
                    else:
                        field = f(text="%s"%itm.value)
                    row = Row([field,])
                else:
                    row = Row([Label("%s"%itm.value, align='l'),])
                if f == TextFieldWrapped:
                    row.width = 250
                rows.append(row)
        if rows:
            col = Column(rows, align='l', spacing=0, height=self.subwidgets[0].subwidgets[1].height)
            col.set_parent(self.subwidgets[0].subwidgets[1])
            col.top = self.subwidgets[0].subwidgets[1].top
            col.left = self.subwidgets[0].subwidgets[1].subwidgets[0].right
            col.bottom = self.subwidgets[0].subwidgets[1].subwidgets[0].bottom
#            col.shrink_wrap()
            self.side_panel = col


    def build_attributes(self, items):
        rows = []
        attributes = items[0]
        names = [a['Name'].value for a in attributes]
        indexes = [] + names
        names.sort()
        for name in names:
            item = attributes[indexes.index(name)]
            rows.append(Row([Label(name.split('.')[-1], align='l'), Label("%s"%item['Base'].value, align='l')],  margin=0))
            mods = item.get('Modifiers', [])
            for mod in mods:
                keys = mod.keys()
                keys.remove('Name')
                rows.append(Row([Label('-> Name', align='l'), Label("%s"%mod['Name'].value, align='l')], margin=0))
                keys.sort()
                for key in keys:
                    rows.append(Row([Label('    %s'%key, align='l'), Label("%s"%mod[key].value, align='l')], margin=0))
        return rows

    def build_motion(self, items):
        return self.build_pos(items)

    def build_pos(self, items):
        rows = []
        pos = items[0]
        rows.append(Row([Label("X", align='l'), Label("%s"%pos[0].value, align='l')]))
        rows.append(Row([Label("Y", align='l'), Label("%s"%pos[1].value, align='l')]))
        rows.append(Row([Label("Z", align='l'), Label("%s"%pos[2].value, align='l')]))
        return rows

    def build_rotation(self, items):
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
    tooltipText = "Dive into level NBT structure."
    def __init__(self, editor):
        """..."""
        self.toolIconName = 'nbtexplorer'
        self.editor = editor
        self.editor.nbtTool = self

    def hidePanel(self):
        self.editor.remove(self.panel)
        self.panel = None

    def toolSelected(self):
        self.showPanel()

    def toolReselected(self):
        self.showPanel()

    def showPanel(self):
        """..."""
        if self.panel is None and self.editor.currentTool in (self, None):
            self.panel = NBTExplorerToolPanel(self.editor)
            self.panel.left = self.editor.left
            self.panel.centery = self.editor.centery
            self.editor.add(self.panel)

