#
# Albow - Controls
#
#-# Modified by D.C.-G. for translation purpose

from pygame import Rect, draw, transform

from widget import Widget, overridable_property
from theme import ThemeProperty
import resource
from translate import _, getLang


class Control(object):
    highlighted = overridable_property('highlighted')
    enabled = overridable_property('enabled')
    value = overridable_property('value')

    enable = None
    ref = None
    _highlighted = False
    _enabled = True
    _value = None

    def get_value(self):
        ref = self.ref
        if ref:
            return ref.get()
        else:
            return self._value

    def set_value(self, x):
        ref = self.ref
        if ref:
            ref.set(x)
        else:
            self._value = x

    def get_highlighted(self):
        return self._highlighted

    def get_enabled(self):
        enable = self.enable
        if enable:
            return enable()
        else:
            return self._enabled

    def set_enabled(self, x):
        self._enabled = x


class AttrRef(object):
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr

    def get(self):
        return getattr(self.obj, self.attr)

    def set(self, x):
        setattr(self.obj, self.attr, x)


class ItemRef(object):
    def __init__(self, obj, item):
        self.obj = obj
        self.item = item

    def get(self):
        return self.obj[self.item]

    def set(self, x):
        self.obj[self.item] = x


class Label(Widget):
    text = overridable_property('text')
    align = overridable_property('align')

    hover_color = ThemeProperty('hover_color')
    highlight_color = ThemeProperty('highlight_color')
    disabled_color = ThemeProperty('disabled_color')
    highlight_bg_color = ThemeProperty('highlight_bg_color')
    hover_bg_color = ThemeProperty('hover_bg_color')
    enabled_bg_color = ThemeProperty('enabled_bg_color')
    disabled_bg_color = ThemeProperty('disabled_bg_color')

    enabled = True
    highlighted = False
    _align = 'l'

    def __init__(self, text, width=None, base_text=None, **kwds):
        #-# Translation live update preparation
        # base_text: to be used each time a widget takes a formated string
        #            defaults to 'text'.
        Widget.__init__(self, **kwds)
        #-# Translation live update preparation
        self.fixed_width = width
        self.base_text = base_text or text
        self.previous_translation = _(text, doNotTranslate=kwds.get('doNotTranslate', False))
        #-#
        self._text = _(text, doNotTranslate=kwds.get('doNotTranslate', False))
        #-#
        self.calc_size()
        #-#

    #-# Translation live update preparation
    def calc_size(self):
        lines = self._text.split("\n")
        tw, th = 0, 0
        for i in range(len(lines)):
            line = lines[i]
            if i == len(lines) - 1:
                w, h = self.font.size(line)
            else:
                w, h = self.font.size(line)[0], self.font.get_linesize()
            tw = max(tw, w)
            th += h
        if self.fixed_width is not None:
            tw = self.fixed_width
        else:
            tw = max(1, tw)
        d = 2 * self.margin
        self.size = (tw + d, th + d)

    def get_update_translation(self):
        return Widget.update_translation(self)

    def set_update_ui(self, v):
        self.text = self.base_text
        self.set_text(self.base_text)
        self.calc_size()
        Widget.set_update_ui(self, v)
    #-#

    def __repr__(self):
        return "Label {0}, child of {1}".format(self.text.encode('ascii', errors='backslashreplace'), self.parent)

    def get_text(self):
        return self._text

    def set_text(self, x, doNotTranslate=False):
        self._text = _(x, doNotTranslate=doNotTranslate or self.doNotTranslate)
        self.calc_size()

    def get_align(self):
        return self._align

    def set_align(self, x):
        self._align = x

    def draw(self, surface):
        if not self.enabled:
            fg = self.disabled_color
            bg = self.disabled_bg_color
        else:
            fg = self.fg_color
            bg = self.enabled_bg_color
            if self.is_default:
                fg = self.default_choice_color or fg
                bg = self.default_choice_bg_color or bg
            if self.is_hover:
                fg = self.hover_color or fg
                bg = self.hover_bg_color or bg
            if self.highlighted:
                fg = self.highlight_color or fg
                bg = self.highlight_bg_color or bg

        self.draw_with(surface, fg, bg)

    is_default = False

    def draw_with(self, surface, fg, bg=None):
        if bg:
            r = surface.get_rect()
            b = self.border_width
            if b:
                e = -2 * b
                r.inflate_ip(e, e)
            surface.fill(bg, r)
        m = self.margin
        align = self.align
        width = surface.get_width()
        y = m
        lines = self.text.split("\n")
        font = self.font
        dy = font.get_linesize()
        for line in lines:
            if len(line):
                size = font.size(line)
                if size[0] == 0:
                    continue

                image = font.render(line, True, fg)
                r = image.get_rect()
                r.top = y
                if align == 'l':
                    r.left = m
                elif align == 'r':
                    r.right = width - m
                else:
                    r.centerx = width // 2
                surface.blit(image, r)
            y += dy


class GLLabel(Label):
    pass


class SmallLabel(Label):
    """Small text size. See theme.py"""


class ButtonBase(Control):
    align = 'c'
    action = None
    rightClickAction = None
    default_choice_color = ThemeProperty('default_choice_color')
    default_choice_bg_color = ThemeProperty('default_choice_bg_color')

    def mouse_down(self, event):
        button = event.button
        if self.enabled and button == 1:
            self._highlighted = True

    def mouse_drag(self, event):
        state = event in self
        if event.buttons[0] == 1 and state != self._highlighted:
            self._highlighted = state
            self.invalidate()

    def mouse_up(self, event):
        button = event.button
        if event in self and button == 1:
            if self is event.clicked_widget or (event.clicked_widget and self in event.clicked_widget.all_parents()):
                self._highlighted = False
                if self.enabled:
                    self.call_handler('action')
        if event in self and button == 3 and self.enabled:
            if self is event.clicked_widget or (event.clicked_widget and self in event.clicked_widget.all_parents()):
                self.call_handler('rightClickAction')
        self.get_root().fix_sticky_ctrl()



class Button(ButtonBase, Label):
    def __init__(self, text, action=None, enable=None, rightClickAction=None, **kwds):
        if action:
            kwds['action'] = action
        if enable:
            kwds['enable'] = enable
        if rightClickAction:
            kwds['rightClickAction'] = rightClickAction
        Label.__init__(self, text, **kwds)


class Image(Widget):
    #  image   Image to display

    highlight_color = ThemeProperty('highlight_color')

    image = overridable_property('image')

    highlighted = False

    def __init__(self, image=None, rect=None, prefix="", **kwds):
        Widget.__init__(self, rect, **kwds)
        if image:
            if isinstance(image, basestring):
                image = resource.get_image(image, prefix=prefix)
            w, h = image.get_size()
            d = 2 * self.margin
            self.size = w + d, h + d
            self._image = image

    def get_image(self):
        return self._image

    def set_image(self, x):
        self._image = x

    def draw(self, surf):
        frame = surf.get_rect()
        if self.highlighted:
            surf.fill(self.highlight_color)
        image = self.image
        r = image.get_rect()
        r.center = frame.center
        surf.blit(image, r)
        
class RotatableImage(Image):
    
    def __init__(self, angle=0.0, min_angle=0, max_angle=360, **kwds):
        super(RotatableImage, self).__init__(**kwds)
        self._angle = -angle
        self._min_angle = min_angle
        self._max_angle = max_angle
    
    def draw(self, surf):
        frame = surf.get_rect()
        if self.highlighted:
            surf.fill(self.highlight_color)
        image = self.image
        image = transform.rotate(image, self._angle)
        r = image.get_rect()
        r.center = frame.center
        surf.blit(image, r)
        
    def get_angle(self):
        return self._angle

    def set_angle(self, angle):
        angle = max(min(angle, self._max_angle), self._min_angle)
        self._angle = angle
        
    def add_angle(self, angle):
        self.set_angle(self.get_angle() + (angle * -1))

class ImageButton(ButtonBase, Image):
    pass


class ValueDisplay(Control, Label):
    format = "%s"
    align = 'l'

    def __init__(self, width=100, **kwds):
        Label.__init__(self, "", **kwds)
        self.set_size_for_text(width)

    def get_text(self):
        return self.format_value(_(self.value, self.doNotTranslate))

    def format_value(self, value):
        if value is not None:
            return self.format % value
        else:
            return ""


class SmallValueDisplay(ValueDisplay):
    pass


class ValueButton(ButtonBase, ValueDisplay):
    align = 'c'

    def get_text(self):
        return self.format_value(_(self.value, self.doNotTranslate))


class CheckControl(Control):
    def mouse_down(self, e):
        if self.get_enabled():
            self.value = not self.value

    def get_highlighted(self):
        return self.value


class CheckWidget(Widget):
    default_size = (16, 16)
    margin = 4
    border_width = 1
    check_mark_tweak = 2

    smooth = ThemeProperty('smooth')

    def __init__(self, **kwds):
        Widget.__init__(self, Rect((0, 0), self.default_size), **kwds)

    def draw(self, surf):
        if self.highlighted:
            r = self.get_margin_rect()
            fg = self.fg_color
            d = self.check_mark_tweak
            p1 = (r.left, r.centery - d)
            p2 = (r.centerx - d, r.bottom)
            p3 = (r.right, r.top - d)
            if self.smooth:
                draw.aalines(surf, fg, False, [p1, p2, p3])
            else:
                draw.lines(surf, fg, False, [p1, p2, p3])


class CheckBox(CheckControl, CheckWidget):
    pass


class RadioControl(Control):
    setting = None

    def get_highlighted(self):
        return self.value == self.setting

    def mouse_down(self, e):
        self.value = self.setting


class RadioButton(RadioControl, CheckWidget):
    pass
