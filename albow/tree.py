# -*- coding: utf-8 -*-
#
# tree.py
#
# (c) D.C.-G. 2014
#
# Tree widget for albow
#
from albow import Widget
from theme import ThemeProperty
from layout import Column
from palette_view import PaletteView
from scrollpanel import ScrollRow
from utils import blit_in_rect
from pygame import image, Surface, Rect, SRCALPHA, draw


#-----------------------------------------------------------------------------
class TreeRow(ScrollRow):
    def click_item(self, n, e):
        self.parent.click_item(n, e.local)


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
        self.selected_item_index = None
        self.selected_item = None
        self._parent = kwargs.pop('_parent', None)
        self.styles = kwargs.pop('styles', {})
        self.compound_types = [dict,] + kwargs.pop('compound_types', [])
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
            if type(v) in self.compound_types:
                meth = getattr(self, 'parse_%s'%v.__class__.__name__, None)
                if meth is not None:
                    v = meth(k, v)
                ks = v.keys()
                ks.sort()
                ks.reverse()
                for a in ks:
                    b = v[a]
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
            rows.append([head, fields, [w] * len(fields), k, p, c, id, type(v), lvl])
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


