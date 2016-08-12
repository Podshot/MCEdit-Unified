# -*- coding: utf-8 -*-
#
# tree.py
#
# (c) D.C.-G. 2014
#
# Tree widget for albow
#
from albow.widget import Widget
from albow.menu import Menu
from albow.fields import IntField, FloatField, TextFieldWrapped
from albow.controls import CheckBox, AttrRef, Label, Button
from albow.dialogs import ask, alert, input_text_buttons
from albow.translate import _
from extended_widgets import ChoiceButton
from theme import ThemeProperty
from layout import Column, Row
from dialogs import Dialog
from palette_view import PaletteView
from scrollpanel import ScrollRow
from utils import blit_in_rect
from pygame import image, Surface, Rect, SRCALPHA, draw, event
import copy


#-----------------------------------------------------------------------------
item_types_map = {dict: ("Compound", None, {}),
                  int: ("Integer", IntField, 0),
                  float: ("Floating point", FloatField, 0.0),
                  unicode: ("Text", TextFieldWrapped, ""),
                  bool: ("Boolean", CheckBox, True),
                 }

def setup_map_types_item(mp=None):
    if not mp:
        mp = item_types_map
    map_types_item = {}
    for k, v in mp.items():
        if v[0] in map_types_item.keys():
            _v = map_types_item.pop(v[0])
            map_types_item[u"%s (%s)"%(_(v[0]), _v[0].__name__)] = _v
            map_types_item[u"%s (%s)"%(_(v[0]), k.__name__)] = (k, v[1], v[2])
        else:
            map_types_item[v[0]] = (k, v[1], v[2])
    return map_types_item

map_types_item = setup_map_types_item()


#-----------------------------------------------------------------------------
# Tree item builder methods
def create_base_item(self, i_type, i_name, i_value):
    return i_name, type(i_type)(i_value)

create_dict = create_int = create_float = create_unicode = create_bool = create_base_item


#-----------------------------------------------------------------------------
class SetupNewItemPanel(Dialog):
    def __init__(self, type_string, types=map_types_item, ok_action=None):
        self.type_string = type_string
        self.ok_action = ok_action
        title = Label("Choose default data")
        self.t, widget, self.v = types[type_string]
        self.n = u""
        w_name = TextFieldWrapped(ref=AttrRef(self, 'n'))
        self.w_value = self.get_widget(widget)
        col = Column([Column([title,]), Label(_("Item Type: %s")%type_string, doNotTranslate=True), Row([Label("Name"), w_name], margin=0), Row([Label("Value"), self.w_value], margin=0), Row([Button("OK", action=ok_action or self.dismiss_ok), Button("Cancel", action=self.dismiss)], margin=0)], margin=0, spacing=2)
        Dialog.__init__(self, client=col)

    def dismiss_ok(self):
        self.dismiss((self.t, self.n, getattr(self.w_value, 'value', map_types_item.get(self.type_string, [None,] * 3)[2])))

    def get_widget(self, widget):
        if hasattr(widget, 'value'):
            value = widget(value=self.v)
        elif hasattr(widget, 'text'):
            value = widget(text=self.v)
        elif widget is None:
            value = Label("This item type is a container. Add chlidren later.")
        else:
            msg = "*** Error in SelectItemTypePanel.__init__():\n    Widget <%s> has no 'text' or 'value' member."%widget
            print msg
            value = Label(msg)
        return value


#-----------------------------------------------------------------------------
class SelectItemTypePanel(Dialog):
    def __init__(self, title, responses, default=None, ok_action=None):
        self.response = responses[0]
        self.ok_action = ok_action
        title = Label(title)
        self.w_type = ChoiceButton(responses)
        col = Column([title, self.w_type, Row([Button("OK", action=ok_action or self.dismiss_ok), Button("Cancel", action=ok_action or self.dismiss)], margin=0)], margin=0, spacing=2)
        Dialog.__init__(self, client=col)

    def dismiss_ok(self):
        self.dismiss(self.w_type.selectedChoice)


#-----------------------------------------------------------------------------
def select_item_type(ok_action, types=map_types_item):
    if len(types) > 1:
        choices = types.keys()
        choices.sort()
        result = SelectItemTypePanel("Choose item type", responses=choices, default=None).present()
    else:
        result = types.keys()[0]
    if type(result) in (str, unicode):
        return SetupNewItemPanel(result, types, ok_action).present()
    return None


#-----------------------------------------------------------------------------
class TreeRow(ScrollRow):
    def click_item(self, n, e):
        self.parent.click_item(n, e.local)

    def mouse_down(self, e):
        if e.button == 3:
            _e = event.Event(e.type, {'alt': e.alt, 'meta': e.meta, 'ctrl': e.ctrl,
                              'shift': e.shift, 'button': 1, 'cmd': e.cmd,
                              'local': e.local, 'pos': e.pos,
                              'num_clicks': e.num_clicks})
            ScrollRow.mouse_down(self, _e)
            self.parent.show_menu(e.local)
        else:
            ScrollRow.mouse_down(self, e)


#-----------------------------------------------------------------------------
class Tree(Column):
    """..."""
    rows = []
    row_margin = 2
    column_margin = 2
    bullet_size = ThemeProperty('bullet_size')
    bullet_color_active = ThemeProperty('bullet_color_active')
    bullet_color_inactive = ThemeProperty('bullet_color_inactive')

    def __init__(self, *args, **kwargs):
        self.menu = [("Add", "add_item"),
                     ("Delete", "delete_item"),
                     ("New child", "add_child"),
                     ("Rename", "rename_item"),
                     ("", ""),
                     ("Cut", "cut_item"),
                     ("Copy", "copy_item"),
                     ("Paste", "paste_item"),
                     ("Paste as child", "paste_child"),
                     ]
        if not hasattr(self, 'map_types_item'):
            global map_types_item
            self.map_types_item = setup_map_types_item()
        self.selected_item_index = None
        # cached_item_index is set to False during startup to avoid a predefined selected item to be unselected when closed
        # the first time.
        self.cached_selected_item_index = False
        self.selected_item = None
        self.clicked_item = None
        self.copyBuffer = kwargs.pop('copyBuffer', None)
        self._parent = kwargs.pop('_parent', None)
        self.styles = kwargs.pop('styles', {})
        self.compound_types = [dict,] + kwargs.pop('compound_types', [])
        self.item_types = self.compound_types + kwargs.pop('item_types', [a[0] for a in self.map_types_item.values()] or [int, float, unicode, bool])
        for t in self.item_types:
            if 'create_%s'%t.__name__ in globals().keys():
                setattr(self, 'create_%s'%t.__name__, globals()['create_%s'%t.__name__])
        self.show_fields = kwargs.pop('show_fields', False)
        self.deployed = []
        self.data = data = kwargs.pop("data", {})
        self.draw_zebra = draw_zebra = kwargs.pop('draw_zebra', True)
#        self.inner_width = kwargs.pop('inner_width', 'auto')
        self.inner_width = kwargs.pop('inner_width', 500)
        self.__num_rows = len(data.keys())
        self.build_layout()
#        row_height = self.font.size(' ')[1]
        row_height = self.font.get_linesize()
        self.treeRow = treeRow = TreeRow((self.inner_width, row_height), 10, draw_zebra=draw_zebra)
        Column.__init__(self, [treeRow,], **kwargs)

    def dispatch_key(self, name, evt):
        if not hasattr(evt, 'key'):
            return
        if name == "key_down":
            keyname = self.root.getKey(evt)
            if keyname == "Up" and self.selected_item_index > 0:
                if self.selected_item_index is None:
                    self.selected_item_index = -1
                self.selected_item_index = max(self.selected_item_index - 1, 0)
                keyname = 'Return'
            elif keyname == "Down" and self.selected_item_index < len(self.rows) - 1:
                if self.selected_item_index is None:
                    self.selected_item_index = -1
                self.selected_item_index += 1
                keyname = 'Return'
            elif keyname == 'Page down':
                if self.selected_item_index is None:
                    self.selected_item_index = -1
                self.selected_item_index = min(len(self.rows) - 1, self.selected_item_index + self.treeRow.num_rows())
                keyname = 'Return'
            elif keyname == 'Page up':
                if self.selected_item_index is None:
                    self.selected_item_index = -1
                self.selected_item_index = max(0, self.selected_item_index - self.treeRow.num_rows())
                keyname = 'Return'

            if self.treeRow.cell_to_item_no(0, 0) is not None and (self.treeRow.cell_to_item_no(0, 0) + self.treeRow.num_rows() -1 > self.selected_item_index or self.treeRow.cell_to_item_no(0, 0) + self.treeRow.num_rows() -1 < self.selected_item_index):
                self.treeRow.scroll_to_item(self.selected_item_index)

            if keyname == 'Return' and self.selected_item_index != None:
                self.select_item(self.selected_item_index)
                if self.selected_item[7] in self.compound_types:
                    self.deploy(self.selected_item[6])
                if self.selected_item is not None and hasattr(self, "update_side_panel"):
                    self.update_side_panel(self.selected_item)

    def cut_item(self):
        self.copyBuffer = ([] + self.selected_item, 1)
        self.delete_item()

    def copy_item(self):
        self.copyBuffer = ([] + self.selected_item, 0)

    def paste_item(self):
        parent = self.get_item_parent(self.selected_item)
        name = self.copyBuffer[0][3]
        old_name = u"%s"%self.copyBuffer[0][3]
        if self.copyBuffer[1] == 0:
            name = input_text_buttons("Choose a name", 300, self.copyBuffer[0][3])
        else:
            old_name = ""
        if name and type(name) in (str, unicode) and name != old_name:
            new_item = copy.deepcopy(self.copyBuffer[0][9])
            if hasattr(new_item, 'name'):
                new_item.name = name
            self.add_item_to(parent, (name, new_item))

    def paste_child(self):
        name = self.copyBuffer[0][3]
        old_name = u"%s"%self.copyBuffer[0][3]
        names = []
        children = self.get_item_children(self.selected_item)
        if children:
            names = [a[3] for a in children]
        if name in names:
            name = input_text_buttons("Choose a name", 300, self.copyBuffer[0][3])
        else:
            old_name = ""
        if name and type(name) in (str, unicode) and name != old_name:
            new_item = copy.deepcopy(self.copyBuffer[0][9])
            if hasattr(new_item, 'name'):
                new_item.name = name
            self.add_item_to(self.selected_item, (name, new_item))

    @staticmethod
    def add_item_to_dict(parent, name, item):
        parent[name] = item

    def add_item_to(self, parent, (name, item)):
        if parent is None:
            tp = 'dict'
            parent = self.data
        else:
            tp = parent[7].__name__
            parent = parent[9]
        if not name:
            i = 0
            name = 'Item %03d'%i
            while name in self.data.keys():
                i += 1
                name = 'Item %03d'%i
        meth = getattr(self, 'add_item_to_%s'%tp, None)
        if meth:
            meth(parent, name, item)
            self.build_layout()
        else:
            alert(_("No function implemented to add items to %s type.")%type(parent).__name__, doNotTranslate=True)

    def add_item(self, types_item=None):
        r = select_item_type(None, types_item or self.map_types_item)
        if type(r) in (list, tuple):
            t, n, v = r
            meth = getattr(self, 'create_%s'%t.__name__, None)
            if meth:
                new_item = meth(self, t, n, v)
                self.add_item_to(self.get_item_parent(self.selected_item), new_item)

    def add_child(self, types_item=None):
        r = select_item_type(None, types_item or self.map_types_item)
        if type(r) in (list, tuple):
            t, n, v = r
            meth = getattr(self, 'create_%s'%t.__name__, None)
            if meth:
                new_item = meth(self, t, n, v)
                self.add_item_to(self.selected_item, new_item)

    def delete_item(self):
        parent = self.get_item_parent(self.selected_item) or self.data
        del parent[self.selected_item]
        self.selected_item_index = None
        self.selected_item = None
        self.build_layout()

    def rename_item(self):
        result = input_text_buttons("Choose a name", 300, self.selected_item[3])
        if type(result) in (str, unicode):
            self.selected_item[3] = result
            self.build_layout()

    def get_item_parent(self, item):
        if item:
            pid = item[4]
            for itm in self.rows:
                if pid == itm[6]:
                    return itm

    def get_item_children(self, item):
        children = []
        if item:
            if item[6] in self.deployed:
                cIds = item[5]
                idx = self.rows.index(item)
                for child in self.rows[idx:]:
                    if child[8] == item[8] + 1 and child[4] == item[6]:
                        children.append(child)
            else:
                k = item[3]
                v = item[9]
                lvl = item[8]
                id = item[6]
                aId = len(self.rows) + 1
                meth = getattr(self, 'parse_%s'%v.__class__.__name__, None)
                if meth is not None:
                    _v = meth(k, v)
                else:
                    _v = v
                ks = _v.keys()
                ks.sort()
                ks.reverse()
                for a in ks:
                    b = _v[a]
                    itm = [lvl + 1, a, b, id, [], aId]
                    itm = [None, None, None, a, id, [], aId, type(b), lvl + 1, b]
                    children.insert(0, itm)
                    aId += 1
        return children

    def show_menu(self, pos):
        if self.menu:
            m = Menu("Menu", self.menu, handler=self)
            i = m.present(self, pos)
            if i > -1:
                meth = getattr(self, self.menu[i][1], None)
                if meth:
                    meth()

    def cut_item_enabled(self):
        return self.selected_item is not None

    def copy_item_enabled(self):
        return self.cut_item_enabled()

    def paste_item_enabled(self):
        return self.copyBuffer is not None

    def paste_child_enabled(self):
        if not self.selected_item:
            return False
        return self.paste_item_enabled() and self.selected_item[7] in self.compound_types

    def add_item_enabled(self):
        return True

    def add_child_enabled(self):
        if not self.selected_item:
            return False
        return self.selected_item[7] in self.compound_types

    def delete_item_enabled(self):
        return self.selected_item is not None

    def rename_item_enabled(self):
        return self.selected_item is not None

    def build_layout(self):
        data = self.data
        parent = 0
        children = []
        keys = data.keys()
        keys.sort()
        items = [[0, a, data[a], parent, children, keys.index(a) + 1] for a in keys]
        rows = []
        w = 50
        aId = len(items) + 1
        while items:
            lvl, k, v, p, c, id = items.pop(0)
            t = None
            _c = False
            fields = []
            c = [] + c
            # If the 'v' object is a dict containing the keys 'value' and 'tooltipText',
            # extract the text, and override the 'v' object with the 'value' value.
            if type(v) == dict and len(v.keys()) and ('value' in v.keys() and 'tooltipText' in v.keys()):
                t = v['tooltipText']
                if type(t) not in (str, unicode):
                    t = repr(t)
                v = v['value']
            if type(v) in self.compound_types:
                meth = getattr(self, 'parse_%s'%v.__class__.__name__, None)
                if meth is not None:
                    _v = meth(k, v)
                else:
                    _v = v
                ks = _v.keys()
                ks.sort()
                ks.reverse()
                for a in ks:
                    b = _v[a]
                    if id in self.deployed:
                        itm = [lvl + 1, a, b, id, [], aId]
                        items.insert(0, itm)
                        c.append(aId)
                    _c = True
                    aId += 1
            else:
                if type(v) in (list, tuple):
                    fields = v
                elif type(v) not in self.compound_types or hasattr(self._parent, 'build_%s'%k.lower()):
                    fields = [v,]
            head = Surface((self.bullet_size * (lvl + 1) + self.font.size(k)[0], self.bullet_size), SRCALPHA)
            if _c:
                meth = getattr(self, 'draw_%s_bullet'%{False: 'closed', True: 'opened'}[id in self.deployed])
            else:
                meth = getattr(self, 'draw_%s_bullet'%v.__class__.__name__, None)
                if not meth:
                    meth = self.draw_deadend_bullet
            bg, fg, shape, text = self.styles.get(type(v),
                                                  ({True: self.bullet_color_active, False: self.bullet_color_inactive}[_c],
                                                   self.fg_color, 'square', ''),
                                                 )
            try:
                meth(head, bg, fg, shape, text, k, lvl)
            except:
                pass
            rows.append([head, fields, [w] * len(fields), k, p, c, id, type(v), lvl, v, t])
        self.rows = rows
        return rows

    def deploy(self, n):
        id = self.rows[n][6]
        if id in self.deployed:
            while id in self.deployed:
                self.deployed.remove(id)
        else:
            self.deployed.append(id)
        self.build_layout()
        l = (self.clicked_item[3], self.clicked_item[4])
        if type(self.cached_selected_item_index) != bool:
            if self.cached_selected_item_index and self.cached_selected_item_index < self.num_rows():
                r = self.rows[self.cached_selected_item_index]
                r = (r[3], r[4])
            else:
                r = (-1, -1)
        else:
            r = l
            self.cached_selected_item_index = self.selected_item_index

        if l == r:
            self.selected_item_index = self.cached_selected_item_index
        else:
            self.cached_selected_item_index = self.selected_item_index
            self.selected_item_index = None

    def click_item(self, n, pos):
        """..."""
        self.clicked_item = row = self.rows[n]
        r = self.get_bullet_rect(row[0], row[8])
        x = pos[0]
        if self.margin + r.left - self.treeRow.hscroll <= x <= self.margin + self.treeRow.margin + r.right - self.treeRow.hscroll:
            self.deploy(n)
        else:
            self.select_item(n)

    def select_item(self, n):
        self.selected_item_index = n
        self.selected_item = self.rows[n]

    def get_bullet_rect(self, surf, lvl):
        r = Rect(0, 0, self.bullet_size, self.bullet_size)
        r.left = self.bullet_size * lvl
        r.inflate_ip(-4, -4)
        return r

    def draw_item_text(self, surf, r, text):
        buf = self.font.render(unicode(text), True, self.fg_color)
        blit_in_rect(surf, buf, Rect(r.right, r.top, surf.get_width() - r.right, r.height), 'c')

    def draw_deadend_bullet(self, surf, bg, fg, shape, text, item_text, lvl):
        r = self.get_bullet_rect(surf, lvl)
        draw.polygon(surf, bg, [r.midtop, r.midright, r.midbottom, r.midleft])
        self.draw_item_text(surf, r, item_text)

    def draw_closed_bullet(self, surf, bg, fg, shape, text, item_text, lvl):
        r = self.get_bullet_rect(surf, lvl)
        draw.polygon(surf, bg, [r.topleft, r.midright, r.bottomleft])
        self.draw_item_text(surf, r, item_text)

    def draw_opened_bullet(self, surf, bg, fg, shape, text, item_text, lvl):
        r = self.get_bullet_rect(surf, lvl)
        draw.polygon(surf, bg, [r.topleft, r.midbottom, r.topright])
        self.draw_item_text(surf, r, item_text)

    def draw_tree_cell(self, surf, i, data, cell_rect, column):
        """..."""
        if type(data) in (str, unicode):
            self.draw_text_cell(surf, i, data, cell_rect, 'l', self.font)
        else:
            self.draw_image_cell(surf, i, data, cell_rect, column)

    @staticmethod
    def draw_image_cell(surf, i, data, cell_rect, column):
        """..."""
        blit_in_rect(surf, data, cell_rect, 'l')

    def draw_text_cell(self, surf, i, data, cell_rect, align, font):
        buf = font.render(unicode(data), True, self.fg_color)
        blit_in_rect(surf, buf, cell_rect, align)

    def num_rows(self):
        return len(self.rows)

    def row_data(self, row):
        return self.rows[row]

    def column_info(self, row_data):
        m = self.column_margin
        d = 2 * m
        x = 0
        for i in range(0,2):
            if i < 1:
                width = self.width
                data = row_data[i]
                yield i, x + m, width - d, None, data
                x += width
        if self.show_fields:
            for i in range(len(row_data[2])):
                width = 50 * (i + 1)
                data = row_data[2][i]
                if type(data) != (str, unicode):
                    data = repr(data)
                yield i, x + m, width - d, None, data
                x += width

