# -*- coding: utf-8 -*-
#
# tree.py
#
# (c) D.C.-G. 2014
#
# Tree widget for albow
#
from albow import Widget, Menu, IntField, FloatField, TextFieldWrapped, \
    CheckBox, AttrRef, Label, Row, Button, ask, alert
from albow.translate import _
from mceutils import ChoiceButton
from theme import ThemeProperty
from layout import Column
from dialogs import Dialog
from palette_view import PaletteView
from scrollpanel import ScrollRow
from utils import blit_in_rect
from pygame import image, Surface, Rect, SRCALPHA, draw, event


#-----------------------------------------------------------------------------
item_types_map = {dict: ("Compound", None, {}),
                  int: ("Integer", IntField, 0),
                  float: ("Floating point number", FloatField, 0.0),
                  unicode: ("Text", TextFieldWrapped, ""),
                  bool: ("Boolean", CheckBox, True),
                 }

def setup_map_types_items(mp=None):
    if not mp:
        mp = item_types_map
    map_types_items = {}
    for k, v in mp.items():
        if v[0] in map_types_items.keys():
            _v = map_types_items.pop(v[0])
            map_types_items[u"%s (%s)"%(v[0], _v[0].__name__)] = _v
            map_types_items[u"%s (%s)"%(v[0], k.__name__)] = v
        else:
            map_types_items[v[0]] = (k, v[1], v[2])
    return map_types_items

map_types_items = setup_map_types_items()


#-----------------------------------------------------------------------------
# Tree item builder methods
def create_base_item(self, i_type, i_name, i_value):
    return i_name, type(i_type)(i_value)

create_dict = create_int = create_float = create_unicode = create_bool = create_base_item


#-----------------------------------------------------------------------------
class SetupNewItemPanel(Dialog):
    def __init__(self, type_string, types=map_types_items, ok_action=None):
        self.type_string = type_string
        self.ok_action = ok_action
        title = Label("Choose default data")
        self.t, widget, self.v = types[type_string]
        self.n = u""
        w_name = TextFieldWrapped(ref=AttrRef(self, 'n'))
        self.w_value = self.get_widget(widget)
        col = Column([Column([title,]), Row([Label("Name"), w_name], margin=0), Row([Label("Value"), self.w_value], margin=0), Row([Button("OK", action=ok_action or self.dismiss_ok), Button("Cancel", action=self.dismiss)], margin=0)], margin=0, spacing=2)
        Dialog.__init__(self, client=col)

    def dismiss_ok(self):
        self.dismiss((self.t, self.n, getattr(self.w_value, 'value', map_types_items.get(self.type_string, [None,] * 3)[2])))

    def get_widget(self, widget):
        if hasattr(widget, 'value'):
            value = widget(value=self.v)
        elif hasattr(widget, 'text'):
            value = widget(text=self.v)
        elif widget is None:
            value = Label("This item type is a container. Add chlidren later.")
        else:
            msg = "*** Error in SelectItemTypePanel.__init__():\n    Widget <%s> has nor 'text' or 'value' member."%widget
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
def select_item_type(ok_action, types=map_types_items):
    choices = types.keys()
    choices.sort()
    result = SelectItemTypePanel("Choose item type", responses=choices, default=None).present()
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
                     ]
        self.selected_item_index = None
        self.selected_item = None
        self._parent = kwargs.pop('_parent', None)
        self.styles = kwargs.pop('styles', {})
        self.compound_types = [dict,] + kwargs.pop('compound_types', [])
        self.item_types = self.compound_types + kwargs.pop('item_types', [int, float, unicode, bool])
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
        row_height = self.font.size(' ')[1]
        self.treeRow = treeRow = TreeRow((self.inner_width, row_height), 10, draw_zebra=draw_zebra)
        Column.__init__(self, [treeRow,], **kwargs)

    @staticmethod
    def add_item_to_dict(parent, name, item):
        parent[name] = item

    def add_item_to(self, parent, (name, item)):
        print 'add_item_to'
        print '    parent', parent
        print '    name', name
        print '    item', item
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

    def add_item(self):
        print "add_item",
        print self.selected_item_index
        print self.selected_item
        r = select_item_type(None, map_types_items)
        if r:
            t, n, v = r
            meth = getattr(self, 'create_%s'%t.__name__, None)
            if meth:
                new_item = meth(self, t, n, v)
                self.add_item_to(self.get_item_parent(self.selected_item), new_item)
    #            self.rows.insert(self.selected_item_index, new_item)

    def add_child(self):
        print "add_child",
        print self.selected_item_index
        print self.selected_item
        r = select_item_type(None, map_types_items)
        if r:
            t, n, v = r
            meth = getattr(self, 'create_%s'%t.__name__, None)
            if meth:
                new_item = meth(self, t, n, v)
                self.add_item_to(self.selected_item, new_item)
    #            new_item

    def delete_item(self):
        print "delete_item",
        print self.selected_item_index
        print self.selected_item

    def rename_item(self):
        print "rename_item",
        print self.selected_item_index
        print self.selected_item

    def get_item_parent(self, item):
        pid = item[4]
#        def comp_ids(itm):
#            return pid == itm[6]
#        return filter(comp_ids, self.rows)
        for itm in self.rows:
            if pid == itm[6]:
                return itm

    def show_menu(self, pos):
        if self.menu and self.selected_item_index:
            m = Menu("Menu", self.menu, handler=self)
            i = m.present(self, pos)
            if i > -1:
                meth = getattr(self, self.menu[i][1], None)
                if meth:
                    meth()

    def add_item_enabled(self):
        return self.selected_item[6] > 0

    def add_child_enabled(self):
        return self.selected_item[7] in self.compound_types

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
            
            _c = False
            fields = []
            c = [] + c
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
            meth(head, bg, fg, shape, text, k, lvl)
            rows.append([head, fields, [w] * len(fields), k, p, c, id, type(v), lvl, v])
        self.rows = rows

    def deploy(self, id):
            if id in self.deployed:
                self.deployed.remove(id)
            else:
                self.deployed.append(id)
            self.build_layout()

    def click_item(self, n, pos):
        """..."""
        row = self.rows[n]
        r = self.get_bullet_rect(row[0], row[8])
        x = pos[0]
        if self.margin + r.left - self.treeRow.hscroll <= x <= self.margin + self.treeRow.margin + r.right - self.treeRow.hscroll:
            id = row[6]
            self.deploy(id)
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


