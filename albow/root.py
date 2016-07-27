# ---------------------------------------------------------------------------
#
#   Albow - Root widget
#
#---------------------------------------------------------------------------

import sys
import pygame

from pygame import key
from pygame.locals import *
# from pygame.time import get_ticks
from pygame.event import Event

from glbackground import *
import widget
from widget import Widget

from datetime import datetime, timedelta
from albow.dialogs import wrapped_label
from albow.translate import _

from pymclevel.box import Vector

# -# This need to be changed. We need albow.translate in the config module.
# -# he solution can be a set of functions wich let us define the needed MCEdit 'config' data
# -# without importing it.
# -# It can be a 'config' module built only for albow.
from config import config
# -#
import os
import directories
import time
from dialogs import Dialog, Label, Button, Row, Column

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
    bonus_draw_time = False
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
        self.testTime = None
        self.testTimeBack = 0.4
        self.nudgeDirection = None
        self.sessionStolen = False
        self.sprint = False
        self.filesToChange = []

    def get_nudge_block(self):
        return self.selectTool.panel.nudgeBlocksButton

    def take_screenshot(self):
        try:
            os.mkdir(os.path.join(directories.getCacheDir(), "screenshots"))
        except OSError:
            pass
        screenshot_name = os.path.join(directories.getCacheDir(), "screenshots", time.strftime("%Y-%m-%d (%I-%M-%S-%p)") + ".png")
        pygame.image.save(pygame.display.get_surface(), screenshot_name)
        self.diag = Dialog()
        lbl = Label(_("Screenshot taken and saved as '%s'") % screenshot_name, doNotTranslate=True)
        folderBtn = Button("Open Folder", action=self.open_screenshots_folder)
        btn = Button("Ok", action=self.screenshot_notify)
        buttonsRow = Row((btn, folderBtn))
        col = Column((lbl, buttonsRow))
        self.diag.add(col)
        self.diag.shrink_wrap()
        self.diag.present()

    def open_screenshots_folder(self):
        from mcplatform import platform_open
        platform_open(os.path.join(directories.getCacheDir(), "screenshots"))
        self.screenshot_notify()

    def screenshot_notify(self):
        self.diag.dismiss()

    @staticmethod
    def set_timer(ms):
        pygame.time.set_timer(USEREVENT, ms)

    def run(self):
        self.run_modal(None)

    captured_widget = None

    def capture_mouse(self, widget):
        # put the mouse in "virtual mode" and pass mouse moved events to the
        # specified widget
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
            if clicked_widget:
                clicked_widget = modal_widget
            num_clicks = 0
            last_click_time = start_time
            last_click_button = False
            self.bonus_draw_time = False

            while modal_widget.modal_result is None:
                try:
                    if not self.mcedit.version_checked:
                        if not self.mcedit.version_lock.locked():
                            self.mcedit.version_checked = True
                            self.mcedit.check_for_version()

                    self.hover_widget = self.find_widget(pygame.mouse.get_pos())
                    if not self.bonus_draw_time:
                        self.bonus_draw_time = True
                        if self.is_gl:
                            self.gl_clear()
                            self.gl_draw_all(self, (0, 0))
                            GL.glFlush()
                        else:
                            self.draw_all(self.surface)
                        pygame.display.flip()
                        self.frames += 1
                    # events = [pygame.event.wait()]
                    events = [pygame.event.poll()]
                    events.extend(pygame.event.get())

                    for event in events:
                        # if event.type:
                        # log.debug("%s", event)
                        type = event.type
                        if type == QUIT:
                            self.quit()
                        elif type == MOUSEBUTTONDOWN:
                            self.bonus_draw_time = False
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
                            # if event.button == 1:
                            clicked_widget = mouse_widget
                            last_mouse_event_handler = mouse_widget
                            last_mouse_event = event
                            mouse_widget.notify_attention_loss()
                            mouse_widget.handle_mouse('mouse_down', event)
                        elif type == MOUSEMOTION:
                            self.bonus_draw_time = False
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
                            self.bonus_draw_time = False
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
                            self.bonus_draw_time = False
                            keyname = self.getKey(event)
                            if keyname == config.keys.takeAScreenshot.get():
                                self.take_screenshot()

                            self.send_key(modal_widget, 'key_down', event)
                            if last_mouse_event_handler:
                                event.dict['pos'] = last_mouse_event.pos
                                event.dict['local'] = last_mouse_event.local
                                last_mouse_event_handler.setup_cursor(event)
                        elif type == KEYUP:
                            key = event.key
                            set_modifier(key, False)
                            add_modifiers(event)
                            self.bonus_draw_time = False
                            keyname = self.getKey(event)
                            if keyname == config.keys.showBlockInfo.get() and self.editor.toolbar.tools[0].infoKey == 1:
                                self.editor.toolbar.tools[0].infoKey = 0
                                self.editor.mainViewport.showCommands()
                            if self.nudgeDirection is not None:
                                keyname = self.getKey(movement=True, keyname=pygame.key.name(key))
                                for i, key in enumerate(self.editor.movements):
                                    if keyname == key and i == self.nudgeDirection:
                                        self.nudgeDirection = None
                                        self.testTime = None
                                        self.testTimeBack = 0.4

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
                                    self.bonus_draw_time = False
                                else:
                                    self.bonus_draw_time = True
                                if last_mouse_event_handler:
                                    event.dict['pos'] = last_mouse_event.pos
                                    event.dict['local'] = last_mouse_event.local
                                    add_modifiers(event)
                                    last_mouse_event_handler.setup_cursor(event)
                                self.begin_frame()
                        # '# Actual Windows working but Linux non working code.
#                         elif type == VIDEORESIZE:
#                             #pygame.display.set_mode(event.dict['size'], self.surface.get_flags())
#                             pygame.display.flip()
#                             #add_modifiers(event)
#                             #self.bonus_draw_time = False
#                             old_w, old_h = self.size
#                             print "Old: " + str(self.size)
#                             #self.size = (event.w, event.h)
#                             print "New: " + str(event.__dict__['size'])
#                             #self.dispatch_key('reshape', event)
#                             #self.mcedit.displayContext.flip()
#                             #pygame.display.flip()
#                             self.root._resized((old_w, old_h))
#                             print "Resized via pygame"
                        # '# Old code before the changes for window management (and working on Linux).
                        elif type == VIDEORESIZE:
                            # add_modifiers(event)
                            self.bonus_draw_time = False
                            self.size = (event.w, event.h)
                            # self.dispatch_key('reshape', event)
                        # '#
                        elif type == VIDEOEXPOSE:
                            if self.mcedit.displayContext.win and self.mcedit.displayContext.win.get_state() == 1:
                                x, y = config.settings.windowX.get(), config.settings.windowY.get()
                                pos = self.mcedit.displayContext.win.get_position()
                                if pos[0] != x:
                                    config.settings.windowX.set(pos[0])
                                if pos[1] != y:
                                    config.settings.windowY.set(pos[1])
                        elif type == ACTIVEEVENT:
                            add_modifiers(event)
                            self.dispatch_key('activeevent', event)
                        elif type == NOEVENT:
                            add_modifiers(event)
                            self.call_idle_handlers(event)
                        # elif type == VIDEORESIZE:
                        #    pygame.display.set_mode(event.dict['size'],self.surface.get_flags())
                        #    pygame.display.flip()

                    if not self.sessionStolen:
                        try:
                            if self.editor.level is not None and hasattr(self.editor.level, "checkSessionLock"):
                                self.editor.level.checkSessionLock()
                        except Exception, e:
                            log.warn(u"Error reading chunk: %s", e)
                            if not config.session.override.get():
                                self.sessionStolen = True
                            else:
                                self.editor.level.acquireSessionLock()

                    if self.editor.level is not None:
                        self.editor.cameraInputs = [0., 0., 0., 0., 0., 0.]
                        self.editor.cameraPanKeys = [0., 0., 0., 0.]
                        allKeys = pygame.key.get_pressed()
                        allKeysWithData = enumerate(allKeys)

                        def useKeys((i, keys)):
                            if not keys:
                                return
                            keyName = self.getKey(movement=True, keyname=pygame.key.name(i))
                            if keyName == self.editor.sprintKey:
                                self.sprint = True
                            if self.editor.level:
                                for j, key in enumerate(self.editor.movements):
                                    if keyName == key and not allKeys[pygame.K_LCTRL] and not allKeys[pygame.K_RCTRL] and not allKeys[pygame.K_RMETA] and not allKeys[pygame.K_LMETA]:
                                        self.changeMovementKeys(j, keyName)

                                for k, key in enumerate(self.editor.cameraPan):
                                    if keyName == key and not allKeys[pygame.K_LCTRL] and not allKeys[pygame.K_RCTRL] and not allKeys[pygame.K_RMETA] and not allKeys[pygame.K_LMETA]:
                                        self.changeCameraKeys(k)
                        map(useKeys, allKeysWithData)

                        for edit in self.filesToChange:
                            newTime = os.path.getmtime(edit.filename)
                            if newTime > edit.timeChanged:
                                edit.timeChanged = newTime
                                edit.makeChanges()


                except Cancel:
                    pass
        finally:
            modal_widget.is_modal = was_modal
            top_widget = old_top_widget
            if old_captured_widget:
                self.capture_mouse(old_captured_widget)

        clicked_widget = None

    @staticmethod
    def getKey(evt=None, movement=False, keyname=None):
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
            if not movement:
                newKeyname = ""
                if evt.shift and keyname != "Shift":
                    newKeyname += "Shift-"
                if (evt.ctrl or evt.cmd) and keyname != "Ctrl":
                    newKeyname += "Ctrl-"
                if evt.alt and keyname != "Alt":
                    newKeyname += "Alt-"

                keyname = newKeyname + keyname

                if not newKeyname:
                    if sys.platform == 'linux2':
                        test_key = getattr(evt, 'scancode', None)
                        tool_keys = [10, 11, 12, 13, 14, 15, 16, 17, 18]
                    else:
                        test_key = keyname
                        tool_keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
                    if test_key in tool_keys:
                        keyname = str(tool_keys.index(test_key) + 1)
                    elif test_key == 19:
                        keyname = '0'

            if keyname == 'Enter':
                keyname = 'Return'
            elif keyname == 'Delete':
                keyname = 'Del'

            return keyname

    def changeMovementKeys(self, keyNum, keyname):
        if self.editor.level is not None and not self.notMove:
            self.editor.cameraInputs[self.movementNum[keyNum]] += self.movementMath[keyNum]
        elif self.notMove and self.nudge is not None and (self.testTime is None or datetime.now() - self.testTime >= timedelta(seconds=self.testTimeBack)):
            if self.testTimeBack > 0.1:
                self.testTimeBack -= 0.1
            self.bonus_draw_time = False
            self.testTime = datetime.now()
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

            for i, key in enumerate(self.editor.movements):
                if key == keyname:
                    self.nudgeDirection = i

    def changeCameraKeys(self, keyNum):
        if self.editor.level is not None and not self.notMove:
            self.editor.cameraPanKeys[self.cameraNum[keyNum]] = self.cameraMath[keyNum]

    def RemoveEditFiles(self):
        self.filesToChange = []

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

    @staticmethod
    def send_key(widget, name, event):
        widget.dispatch_key(name, event)

    def begin_frame(self):
        pass

    def get_root(self):
        return self

    labelClass = lambda s, t: wrapped_label(t, 45)

    def show_tooltip(self, widget, pos):

        if hasattr(self, 'currentTooltip'):
            if self.currentTooltip is not None:
                self.remove(self.currentTooltip)

            self.currentTooltip = None

        def TextTooltip(text, name):
            tooltipBacking = Panel(name=name)
            tooltipBacking.bg_color = (0.0, 0.0, 0.0, 0.8)
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
                tip = TextTooltip(ttext, 'Panel.%s' % (repr(widget)))
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

    @staticmethod
    def confirm_quit():
        return True

    @staticmethod
    def get_mouse_for(widget):
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

    @staticmethod
    def music_end():
        import music

        music.music_end()

    # -# Used for debugging the resize stuff.
#    def resized(self, *args, **kwargs):
#        Widget.resized(self, *args, **kwargs)
#        print self.size

#---------------------------------------------------------------------------

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
