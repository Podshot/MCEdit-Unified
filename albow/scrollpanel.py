# -*- coding: utf_8 -*-
#
# scrollpanel.py
#
# Scrollable widget which contains other widgets, for albow
#
from tree import TreeRow
from layout import Column
from utils import blit_in_rect
from pygame import event, Surface, SRCALPHA

#-----------------------------------------------------------------------------
class ScrollRow(TreeRow):
    def click_item(self, n, e):
        self.parent.click_item(n, e)


#-----------------------------------------------------------------------------
class ScrollPanel(Column):
    column_margin = 2
    def __init__(self, *args, **kwargs):
        kwargs['margin'] = 0
        self.selected_item_index = None
        self.rows = kwargs.pop('rows', [])
        self.align = kwargs.pop('align', 'l')
        self.spacing = kwargs.pop('spacing', 4)
        self.draw_zebra = kwargs.pop('draw_zebra', True)
        self.row_height = kwargs.pop('row_height', max([a.height for a in self.rows] + [self.font.size(' ')[1],]))
        self.inner_width = kwargs.pop('inner_width', 500)
        self.scrollRow = scrollRow = ScrollRow((self.inner_width, self.row_height), 10, draw_zebra=self.draw_zebra, spacing=0)
        self.selected = None
        Column.__init__(self, [scrollRow,], **kwargs)
        self.shrink_wrap()

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
        width = 0
        subs = row_data.subwidgets
        for i in range(len(subs)):
            sub = subs[i]
            width += sub.width
            surf = Surface((sub.width, sub.height), SRCALPHA)
            sub.draw_all(surf)
            yield i, x + m, sub.width - d, None, surf
            x += width

    def click_item(self, n, e):
        if n < len(self.rows):
            for sub in self.rows[n].subwidgets:
                if sub:
                    x = e.local[0] - self.margin - self.rows[n].rect.left - self.rows[n].margin - self.scrollRow.cell_rect(n, 0).left - sub.rect.left
                    y = e.local[1] - self.margin - self.rows[n].rect.top - self.rows[n].margin - self.scrollRow.cell_rect(n, 0).top - sub.rect.top
                    if sub.left <= x <= sub.right:
                        _e = event.Event(e.type, {'alt': e.alt, 'meta': e.meta, 'ctrl': e.ctrl, 'shift': e.shift, 'button': e.button, 'cmd': e.cmd, 'num_clicks': e.num_clicks,
                                                  'local': (x, y), 'pos': e.local})
                        self.focus_on(sub)
                        if self.selected:
                            self.selected.is_modal = False
                        sub.is_modal = True
                        sub.mouse_down(_e)
                        self.selected = sub
                        break

