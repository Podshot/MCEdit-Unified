#-# Modified by D.C.-G. for translation purpose
from albow import Label
from albow.translate import _
from config import config
from glbackground import GLBackground
import pygame


class NudgeButton(GLBackground):
    """ A button that captures movement keys while pressed and sends them to a listener as nudge events.
    Poorly planned. """

    is_gl_container = True

    def __init__(self, editor):
        GLBackground.__init__(self)
        nudgeLabel = Label("Nudge", margin=8)

        self.editor = editor
        self.add(nudgeLabel)
        self.shrink_wrap()
        self.root = self.get_root()

        # tooltipBacking = Panel()
        # tooltipBacking.bg_color = (0, 0, 0, 0.6)
        keys = [_(config.keys[config.convert(k)].get()) for k in ("forward", "back", "left", "right", "up", "down", "fast nudge")]
        if config.keys[config.convert("fast nudge")].get() == "None":
            keys[6] = _("Right mouse")

        nudgeLabel.tooltipText = _("Click and hold.  While holding, use the movement keys ({0}/{1}/{2}/{3}/{4}/{5}) to nudge. Left mouse to nudge a block.\n{6} to nudge a greater distance.").format(
            *keys)
        # tooltipBacking.shrink_wrap()

    def mouse_down(self, event):
        self.root.notMove = True
        self.root.nudge = self
        self.focus()
        if event.button == 3 and config.keys.fastNudge.get() == "None":
            self.editor.rightClickNudge = True

    def mouse_up(self, event):
        self.root.notMove = False
        self.root.nudge = None
        if event.button == 3 and config.keys.fastNudge.get() == "None":
            self.editor.rightClickNudge = False
            self.editor.turn_off_focus()
        if event.button == 1:
            self.editor.turn_off_focus()

    def key_down(self, evt):
        if not pygame.key.get_focused():
            return

        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)

        if keyname == config.keys.fastNudge.get():
            self.editor.rightClickNudge = True

    def key_up(self, evt):
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)

        if keyname == config.keys.fastNudge.get():
            self.editor.rightClickNudge = False
