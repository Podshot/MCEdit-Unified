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
from utils import blit_in_rect
from pygame import image, Surface, Rect, SRCALPHA, draw


#-----------------------------------------------------------------------------
class TreeRow(PaletteView):
    def __init__(self, cell_size, nrows, **kwargs):
        self.draw_zebra = kwargs.pop('draw_zebra', True)
        scrolling = kwargs.pop('scrolling', True)
        self.hscrolling = kwargs.pop('hscrolling', True)
        self.hscroll = None
        PaletteView.__init__(self, cell_size, nrows, 1, scrolling=scrolling)

    def draw_item(self, surf, row, row_rect):
        row_data = self.row_data(row)
        table = self.parent
        height = row_rect.height

        for i, x, width, column, cell_data in table.column_info(row_data):
            cell_rect = Rect(x + self.margin, row_rect.top, width, height)
            self.draw_table_cell(surf, row, cell_data, cell_rect, column)

    def draw_item_and_highlight(self, surface, i, rect, highlight):
        if self.draw_zebra and i % 2:
            surface.fill(self.zebra_color, rect)
        if highlight:
            self.draw_prehighlight(surface, i, rect)
        if highlight and self.highlight_style == 'reverse':
            fg = self.inherited('bg_color') or self.sel_color
        else:
            fg = self.fg_color
        self.draw_item_with(surface, i, rect, fg)
        if highlight:
            self.draw_posthighlight(surface, i, rect)

    def draw_table_cell(self, surf, i, data, cell_rect, column):
        self.parent.draw_tree_cell(surf, i, data, cell_rect, column)

    def click_item(self, n, e):
        self.parent.click_item(n, e.local)

    def item_is_selected(self, n):
        return n == self.parent.selected_item_index

    def num_items(self):
        return self.parent.num_rows()

    def row_data(self, row):
        return self.parent.row_data(row)


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
        level = 0
        w = 50
        aId = len(items) + 1
        while items:
            lvl, k, v, p, c, id = items.pop(0)
            _c = False
            fields = []
            if type(v) in self.compound_types:
                meth = getattr(self, 'parse_%s'%v.__class__.__name__, None)
                if not meth is None:
                    v = meth(k, v)
#                else:
#                    v_items = v.items()
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
                elif type(v) not in self.compound_types:
                    fields = [v,]
            head = Surface((self.bullet_size * (lvl + 1), self.bullet_size), SRCALPHA)
            if _c:
                getattr(self, 'draw_%s_bullet'%{False: 'closed', True: 'opened'}[id in self.deployed])(head, self.bullet_color_active)
            else:
                self.draw_closed_bullet(head, self.bullet_color_inactive)
            rows.append([head, k, fields, [w] * len(fields), p, c, id, type(v), lvl])
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
        r = self.get_bullet_rect(row[0])
        x = pos[0]
        if self.margin + r.left <= x <= self.margin + self.treeRow.margin + r.right:
            id = row[6]
            self.deploy(id)
        else:
            self.select_item(n)

    def select_item(self, n):
        self.selected_item_index = n
        self.selected_item = self.rows[n]

    def get_bullet_rect(self, surf):
        r = Rect(0, 0, self.bullet_size, self.bullet_size)
        r.left = surf.get_rect().right - self.bullet_size
        r.inflate_ip(-4, -4)
        return r

    def draw_closed_bullet(self, surf, c):
        r = self.get_bullet_rect(surf)
        draw.polygon(surf, c, [r.topleft, r.midright, r.bottomleft])

    def draw_opened_bullet(self, surf, c):
        r = self.get_bullet_rect(surf)
        draw.polygon(surf, c, [r.topleft, r.midbottom, r.topright])

    def draw_tree_cell(self, surf, i, data, cell_rect, column):
        """..."""
        if type(data) in (str, unicode):
            self.draw_text_cell(surf, i, data, cell_rect, 'l', self.font)
        else:
            self.draw_image_cell(surf, i, data, cell_rect, column)

    def draw_image_cell(self, surf, i, data, cell_rect, column):
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
        for i in range(0,3):
            if i < 2:
                width = 50 * (i + 1)
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


