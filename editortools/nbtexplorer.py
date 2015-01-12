# -*- coding: utf-8 -*-
#
# nbtexplorer.py
#
# D.C.-G. (LaChal) 2014
#
# Display NBT structure
#
from pygame import key
from albow import Column, Row, Label, Tree, TableView, TableColumn
from albow.theme import root
scroll_button_size = 0 + root.PaletteView.scroll_button_size
del root
from albow.translate import _
from glbackground import Panel
from pymclevel.nbt import load, TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, \
     TAG_Double, TAG_String, TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, \
     TAG_Short_Array
from editortools.editortool import EditorTool


#-----------------------------------------------------------------------------
class NBTTree(Tree):
    def __init__(self, *args, **kwargs):
        self._parent = kwargs.pop('_parent', None)
        Tree.__init__(self, *args, **kwargs)

    def click_item(self, *args, **kwargs):
        Tree.click_item(self, *args, **kwargs)
        if self._parent:
            self._parent.update_side_panel(self.selected_item)

    def parse_TAG_List(self, name, data):
        value = {}
        for i in range(len(data)):
            item = data[i]
            value["%s%s%s"%(name, ("0" * (len(data) - 1)), i)] = item
        return value

#-----------------------------------------------------------------------------
class NBTInvetory(Column):
    pass


#-----------------------------------------------------------------------------
class NBTExplorerToolPanel(Panel):
    """..."""
    def __init__(self, editor):
        """..."""
        Panel.__init__(self)
        self.editor = editor
        self.displayed_item = None
        data = {}
        if hasattr(editor.level, 'root_tag'):
            data = editor.level.root_tag['Data']
        header = Label("NBT Explorer")
        self.max_height = max_height = editor.mainViewport.height - editor.toolbar.height - editor.subwidgets[0].height - editor.statusLabel.height - header.height - (self.margin * 2)
        col = NBTTree(height=max_height, inner_width=250, data=data, compound_types=[TAG_Compound], draw_zebra=False, _parent=self)
        col.shrink_wrap()
        row = [col,]
        row.append(Column([Label("", width=250),], height=max_height))
        self.add(Column([header, Row(row)]))
        self.shrink_wrap()
        self.side_panel = None

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
        items = item[2]
        rows = []
        meth = getattr(self, 'build_%s'%item[1].lower(), None)
        if meth and len(items) == 1:
            rows = meth(items)
        else:
            for itm in items:
                rows.append(Row([Label("%s"%itm.value, align='l'),]))
        if rows:
            if self.side_panel:
                self.side_panel.set_parent(None)
            col = Column(rows, align='l')
            col.set_parent(self.subwidgets[0].subwidgets[1])
            col.topleft = self.subwidgets[0].subwidgets[1].subwidgets[0].topright
            col.shrink_wrap()
            self.side_panel = col

    def build_attributes(self, items):
        rows = []
        attributes = items[0]
        print attributes
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
        width = self.width / 2 - self.margin * 4 - scroll_button_size
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
        table = TableView(height=self.max_height - (self.margin * 2),
                          width=width,
                          nrows=((self.max_height - (self.margin * 2) - font_height / 2) / font_height),
                          columns=tableCols,
                          row_height=font_height,
                          header_height=font_height / 2)
        def num_rows():
            return len(slots)
        table.num_rows = num_rows
        def row_data(n):
            return slots[n]
        table.row_data = row_data
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

