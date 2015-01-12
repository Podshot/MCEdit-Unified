# ---------------------------------------------------------------------------
#
#   Albow - Root widget
#
#---------------------------------------------------------------------------

import sys
import pygame

from pygame import key
from pygame.locals import *
#from pygame.time import get_ticks
from pygame.event import Event

from glbackground import *
import widget
from widget import Widget

from datetime import datetime, timedelta
from albow.dialogs import wrapped_label

from pymclevel.box import Vector

start_time = datetime.now()

mod_cmd = KMOD_LCTRL | KMOD_RCTRL | KMOD_LMETA | KMOD_RMETA
double_click_time = timedelta(0, 0, 300000)  # days, seconds, microseconds

import logging

log = logging.getLogger(__name__)

modifiers = dict(
    shift=False,
    ctrl=False,
    alt=False,
    meta=False,
)

modkeys = {
    K_LSHIFT: 'shift', K_RSHIFT: 'shift',
    K_LCTRL: 'ctrl', K_RCTRL: 'ctrl',
    K_LALT: 'alt', K_RALT: 'alt',
    K_LMETA: 'meta', K_RMETA: 'meta',
}

MUSIC_END_EVENT = USEREVENT + 1

last_mouse_event = Event(0, pos=(0, 0), local=(0, 0))
last_mouse_event_handler = None
root_widget = None  # Root of the containment hierarchy
top_widget = None  # Initial dispatch target
clicked_widget = None  # Target of mouse_drag and mouse_up events

#---------------------------------------------------------------------------


class Cancel(Exception):
    pass


#---------------------------------------------------------------------------


def set_modifier(key, value):
    attr = modkeys.get(key)
    if attr:
        modifiers[attr] = value


def add_modifiers(event):
    d = event.dict
    d.update(modifiers)
    d['cmd'] = event.ctrl or event.meta


def get_root():
    return root_widget


def get_top_widget():
    return top_widget


def get_focus():
    return top_widget.get_focus()


#---------------------------------------------------------------------------


class RootWidget(Widget):
    #  surface   Pygame display surface
    #  is_gl     True if OpenGL surface

    redraw_every_frame = False
    bonus_draw_time = 0
    _is_gl_container = True

    def __init__(self, surface):
        global root_widget
        Widget.__init__(self, surface.get_rect())
        self.surface = surface
        root_widget = self
        widget.root_widget = self
        self.is_gl = surface.get_flags() & OPENGL != 0
        self.idle_handlers = []
        self.editor = None
        self.selectTool = None
        self.movementMath = [-1, 1, 1, -1, 1, -1]
        self.movementNum = [0, 0, 2, 2, 1, 1]
        self.cameraMath = [-1., 1., -1., 1.]
        self.cameraNum = [0, 0, 1, 1]
        self.notMove = False
        self.nudge = None
        self.nudgeCount = 0

    def get_nudge_block(self):
        return self.selectTool.panel.nudgeBlocksButton

    def set_timer(self, ms):
        pygame.time.set_timer(USEREVENT, ms)

    def run(self):
        self.run_modal(None)

    captured_widget = None

    def capture_mouse(self, widget):
        #put the mouse in "virtual mode" and pass mouse moved events to the
        #specified widget
        if widget:
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            self.captured_widget = widget
        else:
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)
            self.captured_widget = None

    frames = 0
    hover_widget = None

    def fix_sticky_ctrl(self):
        self.ctrlClicked = -1

    def run_modal(self, modal_widget):
        if self.editor is None:
            self.editor = self.mcedit.editor
            self.selectTool = self.editor.toolbar.tools[0]
        old_captured_widget = None

        if self.captured_widget:
            old_captured_widget = self.captured_widget
            self.capture_mouse(None)

        global last_mouse_event, last_mouse_event_handler
        global top_widget, clicked_widget
        is_modal = modal_widget is not None
        modal_widget = modal_widget or self
        from OpenGL import GL

        try:
            old_top_widget = top_widget
            top_widget = modal_widget
            was_modal = modal_widget.is_modal
            modal_widget.is_modal = True
            modal_widget.modal_result = None
            if not modal_widget.focus_switch:
                modal_widget.tab_to_first()
            mouse_widget = None
            if clicked_widget:
                clicked_widget = modal_widget
            num_clicks = 0
            last_click_time = start_time
            last_click_button = 0
            self.bonus_draw_time = 0

            while modal_widget.modal_result is None:
                try:
                    if not self.mcedit.version_checked:
                        if not self.mcedit.version_lock.locked():
                            self.mcedit.version_checked = True
                            self.mcedit.check_for_version()

                    self.hover_widget = self.find_widget(pygame.mouse.get_pos())
                    if self.bonus_draw_time < 1:
                        self.bonus_draw_time += 1
                        if self.is_gl:
                            self.gl_clear()
                            self.gl_draw_all(self, (0, 0))
                            GL.glFlush()
                        else:
                            self.draw_all(self.surface)
                        pygame.display.flip()
                        self.frames += 1
                    #events = [pygame.event.wait()]
                    events = [pygame.event.poll()]
                    events.extend(pygame.event.get())
                    
                    for event in events:
                        #if event.type:
                        #log.debug("%s", event)
                        type = event.type
                        if type == QUIT:
                            self.quit()
                        elif type == MOUSEBUTTONDOWN:
                            self.bonus_draw_time = 0
                            t = datetime.now()
                            if t - last_click_time <= double_click_time and event.button == last_click_button:
                                num_clicks += 1
                            else:
                                num_clicks = 1
                            last_click_button = event.button
                            last_click_time = t
                            event.dict['num_clicks'] = num_clicks
                            add_modifiers(event)
                            mouse_widget = self.find_widget(event.pos)
                            if self.captured_widget:
                                mouse_widget = self.captured_widget

                            if not mouse_widget.is_inside(modal_widget):
                                mouse_widget = modal_widget
                            #if event.button == 1:
                            clicked_widget = mouse_widget
                            last_mouse_event_handler = mouse_widget
                            last_mouse_event = event
                            mouse_widget.notify_attention_loss()
                            mouse_widget.handle_mouse('mouse_down', event)
                        elif type == MOUSEMOTION:
                            self.bonus_draw_time = 0
                            add_modifiers(event)
                            modal_widget.dispatch_key('mouse_delta', event)
                            last_mouse_event = event

                            mouse_widget = self.update_tooltip(event.pos)

                            if clicked_widget:
                                last_mouse_event_handler = clicked_widget
                                clicked_widget.handle_mouse('mouse_drag', event)
                            else:
                                if not mouse_widget.is_inside(modal_widget):
                                    mouse_widget = modal_widget
                                last_mouse_event_handler = mouse_widget
                                mouse_widget.handle_mouse('mouse_move', event)
                        elif type == MOUSEBUTTONUP:
                            add_modifiers(event)
                            self.bonus_draw_time = 0
                            mouse_widget = self.find_widget(event.pos)
                            if self.captured_widget:
                                mouse_widget = self.captured_widget
                            if clicked_widget:
                                last_mouse_event_handler = clicked_widget
                                event.dict['clicked_widget'] = clicked_widget
                            else:
                                last_mouse_event_handler = mouse_widget
                                event.dict['clicked_widget'] = None

                            last_mouse_event = event
                            clicked_widget = None
                            last_mouse_event_handler.handle_mouse('mouse_up', event)
                        elif type == KEYDOWN:
                            key = event.key
                            set_modifier(key, True)
                            add_modifiers(event)
                            self.bonus_draw_time = 0

                            levelExist = self.editor.level is not None
                            keyname = event.dict.get('keyname', None) or self.getKey(event)

                            self.send_key(modal_widget, 'key_down', event)
                            if last_mouse_event_handler:
                                event.dict['pos'] = last_mouse_event.pos
                                event.dict['local'] = last_mouse_event.local
                                last_mouse_event_handler.setup_cursor(event)
                        elif type == KEYUP:
                            self.nudgeCount = 0
                            key = event.key
                            set_modifier(key, False)
                            add_modifiers(event)
                            self.bonus_draw_time = 0

                            keyname = event.dict.get('keyname', None) or self.getKey(event)
                            levelExist = self.editor.level is not None

                            self.send_key(modal_widget, 'key_up', event)
                            if last_mouse_event_handler:
                                event.dict['pos'] = last_mouse_event.pos
                                event.dict['local'] = last_mouse_event.local
                                last_mouse_event_handler.setup_cursor(event)
                        elif type == MUSIC_END_EVENT:
                            self.music_end()
                        elif type == USEREVENT:
                            make_scheduled_calls()
                            if not is_modal:
                                if self.redraw_every_frame:
                                    self.bonus_draw_time = 0
                                else:
                                    self.bonus_draw_time += 1
                                if last_mouse_event_handler:
                                    event.dict['pos'] = last_mouse_event.pos
                                    event.dict['local'] = last_mouse_event.local
                                    add_modifiers(event)
                                    last_mouse_event_handler.setup_cursor(event)
                                self.begin_frame()
                        elif type == VIDEORESIZE:
                            #add_modifiers(event)
                            self.bonus_draw_time = 0
                            self.size = (event.w, event.h)
                            #self.dispatch_key('reshape', event)
                        elif type == ACTIVEEVENT:
                            add_modifiers(event)
                            self.dispatch_key('activeevent', event)
                        elif type == NOEVENT:
                            add_modifiers(event)
                            self.call_idle_handlers(event)

                    allKeys = pygame.key.get_pressed()
                    self.editor.cameraInputs = [0., 0., 0., 0., 0., 0.]
                    self.editor.cameraPanKeys = [0., 0., 0., 0.]
                    for i, keys in enumerate(allKeys):
                        if keys:
                            keyName = self.getKey(movement=True, keyname=pygame.key.name(i))
                            if self.editor.level:
                                for i, key in enumerate(self.editor.movements):
                                    if keyName == key:
                                        if not allKeys[pygame.K_LCTRL] and not allKeys[pygame.K_RCTRL] and not allKeys[pygame.K_RMETA] and not allKeys[pygame.K_LMETA]:
                                            self.changeMovementKeys(i, keyName)

                                for i, key in enumerate(self.editor.cameraPan):
                                    if keyName == key:
                                        if not allKeys[pygame.K_LCTRL] and not allKeys[pygame.K_RCTRL] and not allKeys[pygame.K_RMETA] and not allKeys[pygame.K_LMETA]:
                                            self.changeCameraKeys(i)

                except Cancel:
                    pass
        finally:
            modal_widget.is_modal = was_modal
            top_widget = old_top_widget
            if old_captured_widget:
                self.capture_mouse(old_captured_widget)

        clicked_widget = None

    def getKey(self, evt=None, movement=False, keyname=None):
        if keyname is None:
            keyname = key.name(evt.key)
        if 'left' in keyname and len(keyname) > 5:
            keyname = keyname[5:]
        elif 'right' in keyname and len(keyname) > 6:
            keyname = keyname[6:]
        try:
            keyname = keyname.replace(keyname[0], keyname[0].upper(), 1)
        finally:
            if keyname == 'Meta':
                keyname = 'Ctrl'
            newKeyname = ""
            if not movement:
                if evt.shift and keyname != "Shift":
                    newKeyname += "Shift-"
                if (evt.ctrl or evt.cmd) and keyname != "Ctrl":
                    newKeyname += "Ctrl-"
                if evt.alt and keyname != "Alt":
                    newKeyname += "Alt-"

            keyname = newKeyname + keyname

            if keyname == 'Enter':
                keyname = 'Return'

            return keyname

    def changeMovementKeys(self, keyNum, keyname):
        if self.editor.level is not None and not self.notMove:
            self.editor.cameraInputs[self.movementNum[keyNum]] += self.movementMath[keyNum]
        elif self.notMove and self.nudge is not None and self.nudgeCount < 1:
            if keyname == self.editor.movements[4]:
                self.nudge.nudge(Vector(0, 1, 0))
            if keyname == self.editor.movements[5]:
                self.nudge.nudge(Vector(0, -1, 0))

            Z = self.editor.mainViewport.cameraVector
            absZ = map(abs, Z)
            if absZ[0] < absZ[2]:
                forward = (0, 0, (-1 if Z[2] < 0 else 1))
            else:
                forward = ((-1 if Z[0] < 0 else 1), 0, 0)

            back = map(int.__neg__, forward)
            left = forward[2], forward[1], -forward[0]
            right = map(int.__neg__, left)

            if keyname == self.editor.movements[2]:
                self.nudge.nudge(Vector(*forward))
            if keyname == self.editor.movements[3]:
                self.nudge.nudge(Vector(*back))
            if keyname == self.editor.movements[0]:
                self.nudge.nudge(Vector(*left))
            if keyname == self.editor.movements[1]:
                self.nudge.nudge(Vector(*right))

            self.nudgeCount += 1

        elif self.notMove and self.nudge is not None:
            if self.nudgeCount == 250:
                self.nudgeCount = 0
            else:
                self.nudgeCount += 1

    def changeCameraKeys(self, keyNum):
        if self.editor.level is not None and not self.notMove:
            self.editor.cameraPanKeys[self.cameraNum[keyNum]] = self.cameraMath[keyNum]

    def call_idle_handlers(self, event):
        def call(ref):
            widget = ref()
            if widget:
                widget.idleevent(event)
            else:
                print "Idle ref died!"
            return bool(widget)

        self.idle_handlers = filter(call, self.idle_handlers)

    def add_idle_handler(self, widget):
        from weakref import ref

        self.idle_handlers.append(ref(widget))

    def remove_idle_handler(self, widget):
        from weakref import ref

        self.idle_handlers.remove(ref(widget))

    def send_key(self, widget, name, event):
        widget.dispatch_key(name, event)

    def begin_frame(self):
        pass

    def get_root(self):
        return self

    labelClass = lambda s, t: wrapped_label(t, 45)

    def show_tooltip(self, widget, pos):

        if hasattr(self, 'currentTooltip'):
            if self.currentTooltip != None:
                self.remove(self.currentTooltip)

            self.currentTooltip = None

        def TextTooltip(text):
            tooltipBacking = Panel()
            tooltipBacking.bg_color = (0.0, 0.0, 0.0, 0.6)
            tooltipBacking.add(self.labelClass(text))
            tooltipBacking.shrink_wrap()
            return tooltipBacking

        def showTip(tip):
            tip.topleft = pos
            tip.top += 20
            if (tip.bottom > self.bottom) or hasattr(widget, 'tooltipsUp'):
                tip.bottomleft = pos
                tip.top -= 4
            if tip.right > self.right:
                tip.right = pos[0]

            self.add(tip)
            self.currentTooltip = tip

        if widget.tooltip is not None:
            tip = widget.tooltip
            showTip(tip)

        else:
            ttext = widget.tooltipText
            if ttext is not None:
                tip = TextTooltip(ttext)
                showTip(tip)

    def update_tooltip(self, pos=None):
        if pos is None:
            pos = pygame.mouse.get_pos()
        if self.captured_widget:
            mouse_widget = self.captured_widget
            pos = mouse_widget.center
        else:
            mouse_widget = self.find_widget(pos)

        self.show_tooltip(mouse_widget, pos)
        return mouse_widget

    def has_focus(self):
        return True

    def quit(self):
        if self.confirm_quit():
            self.capture_mouse(None)
            sys.exit(0)

    def confirm_quit(self):
        return True

    def get_mouse_for(self, widget):
        last = last_mouse_event
        event = Event(0, last.dict)
        event.dict['local'] = widget.global_to_local(event.pos)
        add_modifiers(event)
        return event

    def gl_clear(self):
        from OpenGL import GL

        bg = self.bg_color
        if bg:
            r = bg[0] / 255.0
            g = bg[1] / 255.0
            b = bg[2] / 255.0
            GL.glClearColor(r, g, b, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

    def music_end(self):
        import music

        music.music_end()

    #-# Used for debugging the resize stuff.
#    def resized(self, *args, **kwargs):
#        Widget.resized(self, *args, **kwargs)
#        print self.size

#---------------------------------------------------------------------------

from time import time
from bisect import insort

scheduled_calls = []


def make_scheduled_calls():
    sched = scheduled_calls
    t = time()
    while sched and sched[0][0] <= t:
        sched[0][1]()
        sched.pop(0)


def schedule(delay, func):
    """Arrange for the given function to be called after the specified
    delay in seconds. Scheduled functions are called synchronously from
    the event loop, and only when the frame timer is running."""
    t = time() + delay
    insort(scheduled_calls, (t, func))
