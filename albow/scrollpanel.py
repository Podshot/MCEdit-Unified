# -*- coding: utf_8 -*-
#
# scrollpanel.py
#
# Scrollable widget which contains other widgets, for albow
#
from palette_view import PaletteView
from layout import Column
from utils import blit_in_rect
from pygame import event, Surface, SRCALPHA, Rect, draw, mouse

#-----------------------------------------------------------------------------
class ScrollRow(PaletteView):
    __tooltipText = None
    @property
    def tooltipText(self):
        pos = mouse.get_pos()

        x, y = self.global_to_local(pos)
#         print "pos", pos
#         print "x", x, "y", y
        w, h = self.cell_size
        W, H = self.size
        d = self.margin
        if d <= x < W - d and d <= y < H - d:
            row = (y - d) // h
            col = (x - d) // w
            if row < self.num_items():
                row_data = self.row_data(row)
                if type(row_data) == list:
                    return self.row_data(row)[-1]
                else:
                    return self.__tooltipText

    @tooltipText.setter
    def tooltipText(self, text):
        self.__tooltipText = text

    def __init__(self, cell_size, nrows, **kwargs):
        self.draw_zebra = kwargs.pop('draw_zebra', True)
        scrolling = kwargs.pop('scrolling', True)
        self.hscrolling = kwargs.pop('hscrolling', True)
        self.hscroll = 0
        self.virtual_width = 1000
        self.dragging_hhover = False
        self.hscroll_rel = 0
        PaletteView.__init__(self, cell_size, nrows, 1, scrolling=scrolling)
        if self.hscrolling:
            self.height += self.scroll_button_size

    def draw_item(self, surf, row, row_rect):
        if self.hscrolling:
            if row_rect.bottom > self.scroll_left_rect().top:
                return
        row_data = self.row_data(row)
        table = self.parent
        height = row_rect.height

        for i, x, width, column, cell_data in table.column_info(row_data):
            cell_rect = Rect(x + self.margin - self.hscroll, row_rect.top, width, height)
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

    def item_is_selected(self, n):
        return n == self.parent.selected_item_index

    def num_items(self):
        return self.parent.num_rows()

    def num_rows(self):
        return max(0, PaletteView.num_rows(self) - 1)

    def row_data(self, row):
        return self.parent.row_data(row)

    def click_item(self, n, e):
        self.parent.click_item(n, e)

    def scroll_up_rect(self):
        d = self.scroll_button_size
        r = Rect(0, 0, d, d)
        m = self.margin
        r.top = m
        r.right = self.width - m
        r.inflate_ip(-4, -4)
        return r

    def scroll_down_rect(self):
        d = self.scroll_button_size
        r = Rect(0, 0, d, d)
        m = self.margin
        r.right = self.width - m
        if self.hscrolling:
            m += d
        r.bottom = self.height - m
        r.inflate_ip(-4, -4)
        return r

    def scroll_left_rect(self):
        d = self.scroll_button_size
        r = Rect(0, 0, d, d)
        m = self.margin
        r.bottom = self.height - m
        r.left = m
        r.inflate_ip(-4, -4)
        return r

    def scroll_right_rect(self):
        d = self.scroll_button_size
        r = Rect(0, 0, d, d)
        m = self.margin
        r.bottom = self.height - m
        if self.scrolling:
            m += d
        r.right = self.width - m
        r.inflate_ip(-4, -4)
        return r

    def hscrollbar_rect(self):
        # Get the distance between the scroll buttons (d)
        slr, slt = self.scroll_left_rect().topright
        d = self.scroll_right_rect().left - slr
        # The predefined step value
        _s = self.cell_size[1]
        # Get the total step number
        n = float(self.virtual_width) / _s
        # Get the visible step number
        v = float(self.width) / _s
        s = float(d) / n
        w = s * v
        if type(w) == float:
            if w - int(w) > 0:
                w += 1

        left = max(slr, slr + (d * (float(self.hscroll) / self.virtual_width)) + self.hscroll_rel)
        r = Rect(left, slt, w, self.scroll_button_size)
        r.right = min(r.right, d + slr)
        r.inflate_ip(-4, -4)
        if r.w < 1:
            r.w = int(w)
        return r

    def can_scroll_left(self):
        return self.hscrolling and self.hscroll > 0

    def can_scroll_right(self):
        return self.hscrolling and self.hscroll + self.width < self.virtual_width

    def draw_scroll_left_button(self, surface):
        r = self.scroll_left_rect()
        c = self.scroll_button_color
        draw.polygon(surface, c, [r.midleft, r.topright, r.bottomright])

    def draw_scroll_right_button(self, surface):
        r = self.scroll_right_rect()
        c = self.scroll_button_color
        draw.polygon(surface, c, [r.topleft, r.midright, r.bottomleft])

    def draw_hscrollbar(self, surface):
        r = self.hscrollbar_rect()
        c = map(lambda x: min(255, max(0, x + 10)), self.scroll_button_color)
        draw.rect(surface, c, r)

    def draw(self, surface):
        for row in xrange(self.num_rows()):
            for col in xrange(self.num_cols()):
                r = self.cell_rect(row, col)
                self.draw_cell(surface, row, col, r)

        u = False
        d = False
        l = False
        r = False
        if self.can_scroll_up():
            u = True
            self.draw_scroll_up_button(surface)
        if self.can_scroll_down():
            d = True
            self.draw_scroll_down_button(surface)
        if self.can_scroll_left():
            l = True
            self.draw_scroll_left_button(surface)
        if self.can_scroll_right():
            r = True
            self.draw_scroll_right_button(surface)

        if u or d:
            self.draw_scrollbar(surface)
        if l or r:
            self.draw_hscrollbar(surface)

    def scroll_left(self, delta=1):
        if self.can_scroll_left():
            self.hscroll -= self.cell_size[1] * delta

    def scroll_right(self, delta=1):
        if self.can_scroll_right():
            self.hscroll += self.cell_size[1] * delta

    def mouse_down(self, event):
        if event.button == 1:
            if self.hscrolling:
                p = event.local
                if self.hscrollbar_rect().collidepoint(p):
                    self.dragging_hhover = True
                    return
                elif self.scroll_left_rect().collidepoint(p):
                    self.scroll_left()
                    return
                elif self.scroll_right_rect().collidepoint(p):
                    self.scroll_right()
                    return
        elif event.button == 6:
            if self.hscrolling:
                self.scroll_left()
        elif event.button == 7:
            if self.hscrolling:
                self.scroll_right()
        PaletteView.mouse_down(self, event)

    def mouse_drag(self, event):
        if self.dragging_hhover:
            self.hscroll_rel += event.rel[0]
            slr, slt = self.scroll_left_rect().topright
            d = self.scroll_right_rect().left - slr
            _s = self.cell_size[1]
            n = float(self.virtual_width) / _s
            s = float(d) / n
            if abs(self.hscroll_rel) > s:
                if self.hscroll_rel > 0:
                    self.scroll_right(delta=int(abs(self.hscroll_rel) / s))
                else:
                    self.scroll_left(delta=int(abs(self.hscroll_rel) / s))
                self.hscroll_rel = 0
        PaletteView.mouse_drag(self, event)

    def mouse_up(self, event):
        if self.dragging_hhover:
            self.dragging_hhover = False
            self.hscroll_rel = 0
        PaletteView.mouse_up(self, event)

    def cell_rect(self, row, col):
        w, h = self.cell_size
        d = self.margin
        x = col * w + d - self.hscroll
        y = row * h + d
        return Rect(x, y, w, h)


#-----------------------------------------------------------------------------
class ScrollPanel(Column):
    column_margin = 2
    def __init__(self, *args, **kwargs):
        kwargs['margin'] = kwargs.get('margin', 0)
        self.selected_item_index = None
        self.rows = kwargs.pop('rows', [])
        self.align = kwargs.get('align', 'l')
        self.spacing = kwargs.get('spacing', 4)
        self.draw_zebra = kwargs.pop('draw_zebra', True)
#        self.row_height = kwargs.pop('row_height', max([a.height for a in self.rows] + [self.font.size(' ')[1],]))
        self.row_height = kwargs.pop('row_height', max([a.height for a in self.rows] + [self.font.get_linesize(),]))
        self.inner_width = kwargs.pop('inner_width', 500)
        self.scrolling = kwargs.get('scrolling', True)
        self.hscrolling = kwargs.get('hscrolling', True)
        self.scrollRow = scrollRow = ScrollRow((self.inner_width, self.row_height), 10, draw_zebra=self.draw_zebra, spacing=0,
                                               scrolling=self.scrolling, hscrolling=self.hscrolling)
        self.selected = None
        Column.__init__(self, [scrollRow,], **kwargs)
        self.shrink_wrap()

    def draw_tree_cell(self, surf, i, data, cell_rect, column):
        """..."""
        if self.align.lower() == 'r':
            cell_rect.right = self.right - self.margin
            if self.scrollRow.can_scroll_up() or self.scrollRow.can_scroll_down():
                cell_rect.right -= self.scrollRow.scroll_button_size
        elif self.align.lower() == 'c':
            cell_rect.left = self.centerx - (cell_rect.width / 2)
        if type(data) in (str, unicode):
            self.draw_text_cell(surf, i, data, cell_rect, self.align, self.font)
        else:
            self.draw_image_cell(surf, i, data, cell_rect, column)

    def draw_image_cell(self, surf, i, data, cell_rect, column):
        """..."""
        blit_in_rect(surf, data, cell_rect, self.align, self.margin)

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
            yield i, x + m, sub.width - d, i, surf
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

