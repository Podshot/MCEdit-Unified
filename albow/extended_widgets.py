# -*- coding: UTF-8 -*-
# extended_widgets.py
# Moved albow related stuff from mceutils.
import resource_packs
from controls import ValueDisplay
from dialogs import alert, ask, Dialog
from controls import Button, Label, ValueButton, CheckBox, AttrRef
from widget import Widget
import root
from layout import Column, Row
from translate import _
from menu import Menu
from fields import FloatField, IntField, TextFieldWrapped
from datetime import timedelta


class HotkeyColumn(Widget):
    is_gl_container = True

    def __init__(self, items, keysColumn=None, buttonsColumn=None, item_spacing=None):
        if keysColumn is None:
            keysColumn = []
        if buttonsColumn is None:
            buttonsColumn = []
        labels = []

        Widget.__init__(self)
        for t in items:
            if len(t) == 3:
                (hotkey, title, action) = t
                tooltipText = None
            else:
                (hotkey, title, action, tooltipText) = t
            if isinstance(title, (str, unicode)):
                button = Button(title, action=action)
            else:
                button = ValueButton(ref=title, action=action, width=200)
            button.anchor = self.anchor

            label = Label(hotkey, width=100, margin=button.margin)
            label.anchor = "wh"

            label.height = button.height

            labels.append(label)

            if tooltipText:
                button.tooltipText = tooltipText

            keysColumn.append(label)
            buttonsColumn.append(button)

        self.buttons = list(buttonsColumn)

        #.#
        if item_spacing == None:
            buttonsColumn = Column(buttonsColumn)
        else:
            buttonsColumn = Column(buttonsColumn, spacing=item_spacing)
        #.#
        buttonsColumn.anchor = self.anchor
        #.#
        if item_spacing == None:
            keysColumn = Column(keysColumn)
        else:
            keysColumn = Column(keysColumn, spacing=item_spacing)

        commandRow = Row((keysColumn, buttonsColumn))
        self.labels = labels
        self.add(commandRow)
        self.shrink_wrap()


class MenuButton(Button):
    def __init__(self, title, choices, **kw):
        Button.__init__(self, title, **kw)
        self.choices = choices
        self.menu = Menu(title, ((c, c) for c in choices))

    def action(self):
        index = self.menu.present(self, (0, 0))
        if index == -1:
            return
        self.menu_picked(index)

    def menu_picked(self, index):
        pass


class ChoiceButton(ValueButton):
    align = "c"
    choose = None

    def __init__(self, choices, scrolling=True, scroll_items=30, **kw):
        # passing an empty list of choices is ill-advised

        if 'choose' in kw:
            self.choose = kw.pop('choose')

        ValueButton.__init__(self, action=self.showMenu, **kw)

        self.scrolling = scrolling
        self.scroll_items = scroll_items
        self.choices = choices or ["[UNDEFINED]"]

        widths = [self.font.size(_(c))[0] for c in choices] + [self.width]
        if len(widths):
            self.width = max(widths) + self.margin * 2

        self.choiceIndex = 0

    def showMenu(self):
        choiceIndex = self.menu.present(self, (0, 0))
        if choiceIndex != -1:
            self.choiceIndex = choiceIndex
            if self.choose:
                self.choose()

    def get_value(self):
        return self.selectedChoice

    @property
    def selectedChoice(self):
        if self.choiceIndex >= len(self.choices) or self.choiceIndex < 0:
            return ""
        return self.choices[self.choiceIndex]

    @selectedChoice.setter
    def selectedChoice(self, val):
        idx = self.choices.index(val)
        if idx != -1:
            self.choiceIndex = idx

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, ch):
        self._choices = ch
        self.menu = Menu("", ((name, "pickMenu") for name in self._choices),
                         self.scrolling, self.scroll_items)


def CheckBoxLabel(title, *args, **kw):
    tooltipText = kw.pop('tooltipText', None)

    cb = CheckBox(*args, **kw)
    lab = Label(title, fg_color=cb.fg_color)
    lab.mouse_down = cb.mouse_down

    if tooltipText:
        cb.tooltipText = tooltipText
        lab.tooltipText = tooltipText

    class CBRow(Row):
        margin = 0

        @property
        def value(self):
            return self.checkbox.value

        @value.setter
        def value(self, val):
            self.checkbox.value = val

    row = CBRow((lab, cb))
    row.checkbox = cb
    return row


def FloatInputRow(title, *args, **kw):
    return Row((Label(title, tooltipText=kw.get('tooltipText')), FloatField(*args, **kw)))


def IntInputRow(title, *args, **kw):
    return Row((Label(title, tooltipText=kw.get('tooltipText')), IntField(*args, **kw)))


def showProgress(progressText, progressIterator, cancel=False):
    """Show the progress for a long-running synchronous operation.
    progressIterator should be a generator-like object that can return
    either None, for an indeterminate indicator,
    A float value between 0.0 and 1.0 for a determinate indicator,
    A string, to update the progress info label
    or a tuple of (float value, string) to set the progress and update the label"""

    class ProgressWidget(Dialog):
        progressFraction = 0.0
        firstDraw = False
        root = None

        def draw(self, surface):
            if self.root is None:
                self.root = self.get_root()
            Widget.draw(self, surface)
            frameStart = datetime.now()
            frameInterval = timedelta(0, 1, 0) / 2
            amount = None

            try:
                while datetime.now() < frameStart + frameInterval:
                    amount = progressIterator.next()
                    if self.firstDraw is False:
                        self.firstDraw = True
                        break

            except StopIteration:
                self.dismiss()

            infoText = ""
            if amount is not None:

                if isinstance(amount, tuple):
                    if len(amount) > 2:
                        infoText = ": " + amount[2]

                    amount, max = amount[:2]

                else:
                    max = amount
                maxwidth = (self.width - self.margin * 2)
                if amount is None:
                    self.progressBar.width = maxwidth
                    self.progressBar.bg_color = (255, 255, 25, 255)
                elif isinstance(amount, basestring):
                    self.statusText = amount
                else:
                    self.progressAmount = amount
                    if isinstance(amount, (int, float)):
                        self.progressFraction = float(amount) / (float(max) or 1)
                        self.progressBar.width = maxwidth * self.progressFraction
                        self.statusText = str("{0} / {1}".format(amount, max))
                    else:
                        self.statusText = str(amount)

                if infoText:
                    self.statusText += infoText

        @property
        def estimateText(self):
            delta = (datetime.now() - self.startTime)
            progressPercent = (int(self.progressFraction * 10000))
            left = delta * (10000 - progressPercent) / (progressPercent or 1)
            return _("Time left: {0}").format(left)

        def cancel(self):
            if cancel:
                self.dismiss(False)

        def idleevent(self, evt):
            self.invalidate()

        def key_down(self, event):
            pass

        def key_up(self, event):
            pass

        def mouse_up(self, event):
            try:
                if "SelectionTool" in str(self.root.editor.currentTool):
                    if self.root.get_nudge_block().count > 0:
                        self.root.get_nudge_block().mouse_up(event)
            except:
                pass

    widget = ProgressWidget()
    widget.progressText = _(progressText)
    widget.statusText = ""
    widget.progressAmount = 0.0

    progressLabel = ValueDisplay(ref=AttrRef(widget, 'progressText'), width=550)
    statusLabel = ValueDisplay(ref=AttrRef(widget, 'statusText'), width=550)
    estimateLabel = ValueDisplay(ref=AttrRef(widget, 'estimateText'), width=550)

    progressBar = Widget(size=(550, 20), bg_color=(150, 150, 150, 255))
    widget.progressBar = progressBar
    col = (progressLabel, statusLabel, estimateLabel, progressBar)
    if cancel:
        cancelButton = Button("Cancel", action=widget.cancel, fg_color=(255, 0, 0, 255))
        col += (Column((cancelButton,), align="r"),)

    widget.add(Column(col))
    widget.shrink_wrap()
    widget.startTime = datetime.now()
    if widget.present():
        return widget.progressAmount
    else:
        return "Canceled"


