"""Copyright (c) 2010-2012 David Rio Vierra

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""
# import resource_packs # not the right place, moving it a bit furtehr

"""
mceutils.py

Exception catching, some basic box drawing, texture pack loading, oddball UI elements
"""
# Modified by D.C.-G. for translation purpose
#.# Marks the layout modifications. -- D.C.-G.
#!#
#!# The stuff in there related to albow should be in albow module.
#!# This stuff will then be available for components base classes in this GUI module.
#!# And make albow/widgets more coherent to use.
#!#
from resource_packs import ResourcePackHandler
from albow.controls import ValueDisplay
from albow import alert, ask, Button, Column, Label, root, Row, ValueButton, Widget
from albow.translate import _
from datetime import datetime
import directories
import numpy
from OpenGL import GL
import os
import png
from pygame import display
import pymclevel
import json
import hashlib
import shutil

import logging

#!# Used to track the ALBOW stuff imported from here
def warn(obj):
    name = getattr(obj, '__name__', getattr(getattr(obj, '__class__', obj), '__name__', obj))
    logging.getLogger().warn('%s.%s is deprecated and will be removed. Use albow.%s instead.'%(obj.__module__, name, name))
#!#


def alertException(func):
    def _alertException(*args, **kw):
        try:
            return func(*args, **kw)
        except root.Cancel:
            alert("Canceled.")
        except pymclevel.infiniteworld.SessionLockLost as e:
            alert(_(e.message) + _("\n\nYour changes cannot be saved."))
        except Exception, e:
            logging.exception("Exception:")
            ask(_("Error during {0}: {1!r}").format(func, e)[:1000], ["OK"], cancel=0)
    return _alertException


def drawFace(box, face, type=GL.GL_QUADS):
    x, y, z, = box.origin
    x2, y2, z2 = box.maximum

    if face == pymclevel.faces.FaceXDecreasing:

        faceVertices = numpy.array(
            (x, y2, z2,
             x, y2, z,
             x, y, z,
             x, y, z2,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceXIncreasing:

        faceVertices = numpy.array(
            (x2, y, z2,
             x2, y, z,
             x2, y2, z,
             x2, y2, z2,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceYDecreasing:
        faceVertices = numpy.array(
            (x2, y, z2,
             x, y, z2,
             x, y, z,
             x2, y, z,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceYIncreasing:
        faceVertices = numpy.array(
            (x2, y2, z,
             x, y2, z,
             x, y2, z2,
             x2, y2, z2,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceZDecreasing:
        faceVertices = numpy.array(
            (x, y, z,
             x, y2, z,
             x2, y2, z,
             x2, y, z,
            ), dtype='f4')

    elif face == pymclevel.faces.FaceZIncreasing:
        faceVertices = numpy.array(
            (x2, y, z2,
             x2, y2, z2,
             x, y2, z2,
             x, y, z2,
            ), dtype='f4')

    faceVertices.shape = (4, 3)
    dim = face >> 1
    dims = [0, 1, 2]
    dims.remove(dim)

    texVertices = numpy.array(
        faceVertices[:, dims],
        dtype='f4'
    ).flatten()
    faceVertices.shape = (12,)

    texVertices *= 16
    GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

    GL.glVertexPointer(3, GL.GL_FLOAT, 0, faceVertices)
    GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, texVertices)

    GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glEnable(GL.GL_POLYGON_OFFSET_LINE)

    if type is GL.GL_LINE_STRIP:
        indexes = numpy.array((0, 1, 2, 3, 0), dtype='uint32')
        GL.glDrawElements(type, 5, GL.GL_UNSIGNED_INT, indexes)
    else:
        GL.glDrawArrays(type, 0, 4)
    GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glDisable(GL.GL_POLYGON_OFFSET_LINE)
    GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)


def drawCube(box, cubeType=GL.GL_QUADS, blockType=0, texture=None, textureVertices=None, selectionBox=False):
    """ pass a different cubeType e.g. GL_LINE_STRIP for wireframes """
    x, y, z, = box.origin
    x2, y2, z2 = box.maximum
    dx, dy, dz = x2 - x, y2 - y, z2 - z
    cubeVertices = numpy.array(
        (
            x, y, z,
            x, y2, z,
            x2, y2, z,
            x2, y, z,

            x2, y, z2,
            x2, y2, z2,
            x, y2, z2,
            x, y, z2,

            x2, y, z2,
            x, y, z2,
            x, y, z,
            x2, y, z,

            x2, y2, z,
            x, y2, z,
            x, y2, z2,
            x2, y2, z2,

            x, y2, z2,
            x, y2, z,
            x, y, z,
            x, y, z2,

            x2, y, z2,
            x2, y, z,
            x2, y2, z,
            x2, y2, z2,
        ), dtype='f4')
    if textureVertices is None:
        textureVertices = numpy.array(
            (
                0, -dy * 16,
                0, 0,
                dx * 16, 0,
                dx * 16, -dy * 16,

                dx * 16, -dy * 16,
                dx * 16, 0,
                0, 0,
                0, -dy * 16,

                dx * 16, -dz * 16,
                0, -dz * 16,
                0, 0,
                dx * 16, 0,

                dx * 16, 0,
                0, 0,
                0, -dz * 16,
                dx * 16, -dz * 16,

                dz * 16, 0,
                0, 0,
                0, -dy * 16,
                dz * 16, -dy * 16,

                dz * 16, -dy * 16,
                0, -dy * 16,
                0, 0,
                dz * 16, 0,

            ), dtype='f4')

        textureVertices.shape = (6, 4, 2)

        if selectionBox:
            textureVertices[0:2] += (16 * (x & 15), 16 * (y2 & 15))
            textureVertices[2:4] += (16 * (x & 15), -16 * (z & 15))
            textureVertices[4:6] += (16 * (z & 15), 16 * (y2 & 15))
            textureVertices[:] += 0.5

    GL.glVertexPointer(3, GL.GL_FLOAT, 0, cubeVertices)
    if texture is not None:
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)

        texture.bind()
        GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, textureVertices),

    GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glEnable(GL.GL_POLYGON_OFFSET_LINE)

    GL.glDrawArrays(cubeType, 0, 24)
    GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
    GL.glDisable(GL.GL_POLYGON_OFFSET_LINE)

    if texture is not None:
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisable(GL.GL_TEXTURE_2D)


def drawTerrainCuttingWire(box,
                           c0=(0.75, 0.75, 0.75, 0.4),
                           c1=(1.0, 1.0, 1.0, 1.0)):
    # glDepthMask(False)
    GL.glEnable(GL.GL_DEPTH_TEST)

    GL.glDepthFunc(GL.GL_LEQUAL)
    GL.glColor(*c1)
    GL.glLineWidth(2.0)
    drawCube(box, cubeType=GL.GL_LINE_STRIP)

    GL.glDepthFunc(GL.GL_GREATER)
    GL.glColor(*c0)
    GL.glLineWidth(1.0)
    drawCube(box, cubeType=GL.GL_LINE_STRIP)

    GL.glDepthFunc(GL.GL_LEQUAL)
    GL.glDisable(GL.GL_DEPTH_TEST)
    # glDepthMask(True)


def loadAlphaTerrainTexture():
    texW, texH, terraindata = loadPNGFile(os.path.join(directories.getDataDir(),  ResourcePackHandler.Instance().get_selected_resource_pack().terrain_path()))

    def _loadFunc():
        loadTextureFunc(texW, texH, terraindata)

    tex = glutils.Texture(_loadFunc)
    tex.data = terraindata
    return tex


def loadPNGData(filename_or_data):
    reader = png.Reader(filename_or_data)
    (w, h, data, metadata) = reader.read_flat()
    data = numpy.array(data, dtype='uint8')
    data.shape = (h, w, metadata['planes'])
    if data.shape[2] == 1:
        # indexed color. remarkably straightforward.
        data.shape = data.shape[:2]
        data = numpy.array(reader.palette(), dtype='uint8')[data]

    if data.shape[2] < 4:
        data = numpy.insert(data, 3, 255, 2)

    return w, h, data


def loadPNGFile(filename):
    (w, h, data) = loadPNGData(filename)

    powers = (16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
    assert (w in powers) and (h in powers)  # how crude

    return w, h, data


def loadTextureFunc(w, h, ndata):
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w, h, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, ndata)
    return w, h


def loadPNGTexture(filename, *a, **kw):
    filename = os.path.join(directories.getDataDir(), filename)
    try:
        w, h, ndata = loadPNGFile(filename)

        tex = glutils.Texture(functools.partial(loadTextureFunc, w, h, ndata), *a, **kw)
        tex.data = ndata
        return tex
    except Exception, e:
        print "Exception loading ", filename, ": ", repr(e)
        return glutils.Texture()


import glutils


def normalize(x):
    l = x[0] * x[0] + x[1] * x[1] + x[2] * x[2]
    if l <= 0.0:
        return [0, 0, 0]
    size = numpy.sqrt(l)
    if size <= 0.0:
        return [0, 0, 0]
    return map(lambda a: a / size, x)


def normalize_size(x):
    l = x[0] * x[0] + x[1] * x[1] + x[2] * x[2]
    if l <= 0.0:
        return [0., 0., 0.], 0.
    size = numpy.sqrt(l)
    if size <= 0.0:
        return [0, 0, 0], 0
    return (x / size), size


# Label = GLLabel

class HotkeyColumn(Widget):
    is_gl_container = True

    def __init__(self, items, keysColumn=None, buttonsColumn=None, item_spacing=None):
        warn(self)
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


from albow import CheckBox, AttrRef, Menu


class MenuButton(Button):
    def __init__(self, title, choices, **kw):
        warn(self)
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
        warn(self)

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
    warn(CheckBoxLabel)
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


from albow import FloatField, IntField, TextFieldWrapped


def FloatInputRow(title, *args, **kw):
    warn(FloatInputRow)
    return Row((Label(title, tooltipText=kw.get('tooltipText')), FloatField(*args, **kw)))


def IntInputRow(title, *args, **kw):
    warn(IntInputRow)
    return Row((Label(title, tooltipText=kw.get('tooltipText')), IntField(*args, **kw)))


from albow.dialogs import Dialog
from datetime import timedelta


def TextInputRow(title, *args, **kw):
    warn(TextInputRow)
    return Row((Label(title, tooltipText=kw.get('tooltipText')), TextFieldWrapped(*args, **kw)))


def setWindowCaption(prefix):
    caption = display.get_caption()[0]
    prefix = _(prefix)
    if type(prefix) == unicode:
        prefix = prefix.encode("utf8")

    class ctx:
        def __enter__(self):
            display.set_caption(prefix + caption)

        def __exit__(self, *args):
            display.set_caption(caption)

    return ctx()


def showProgress(progressText, progressIterator, cancel=False):
    """Show the progress for a long-running synchronous operation.
    progressIterator should be a generator-like object that can return
    either None, for an indeterminate indicator,
    A float value between 0.0 and 1.0 for a determinate indicator,
    A string, to update the progress info label
    or a tuple of (float value, string) to set the progress and update the label"""

    warn(ShowProgress)

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
            if progressPercent > 10000:
                progressPercent = 10000
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


from glutils import DisplayList

import functools
