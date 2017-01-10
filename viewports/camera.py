# -*- coding: utf_8 -*-
# The above line is necessary, unless we want problems with encodings...
import sys
from compass import CompassOverlay
from raycaster import TooFarException
import raycaster
import keys
import pygame

import math
import copy
import numpy
from config import config
import frustum
import logging
import glutils
import mceutils
import itertools
import pymclevel
from pymclevel import MCEDIT_DEFS, MCEDIT_IDS

from math import isnan
from datetime import datetime, timedelta

from OpenGL import GL
from OpenGL import GLU

from albow import alert, AttrRef, Button, Column, input_text, Row, TableColumn, TableView, Widget, CheckBox, \
    TextFieldWrapped, MenuButton, ChoiceButton, IntInputRow, TextInputRow, showProgress, IntField, ask
from albow.controls import Label, ValueDisplay
from albow.dialogs import Dialog, wrapped_label
from albow.openglwidgets import GLViewport
from albow.extended_widgets import BasicTextInputRow, CheckBoxLabel
from albow.translate import _
from albow.root import get_top_widget
from pygame import mouse
from depths import DepthOffset
from editortools.operation import Operation
from glutils import gl
from pymclevel.nbt import TAG_String
from editortools.nbtexplorer import SlotEditor

class SignEditOperation(Operation):
        def __init__(self, tool, level, tileEntity, backupTileEntity):
            self.tool = tool
            self.level = level
            self.tileEntity = tileEntity
            self.undoBackupEntityTag = backupTileEntity
            self.canUndo = False

        def perform(self, recordUndo=True):
            if self.level.saving:
                alert("Cannot perform action while saving is taking place")
                return
            self.level.addTileEntity(self.tileEntity)
            self.canUndo = True

        def undo(self):
            self.redoBackupEntityTag = copy.deepcopy(self.tileEntity)
            self.level.addTileEntity(self.undoBackupEntityTag)
            return pymclevel.BoundingBox(pymclevel.TileEntity.pos(self.tileEntity), (1, 1, 1))

        def redo(self):
            self.level.addTileEntity(self.redoBackupEntityTag)
            return pymclevel.BoundingBox(pymclevel.TileEntity.pos(self.tileEntity), (1, 1, 1))

class CameraViewport(GLViewport):
    anchor = "tlbr"

    oldMousePosition = None
    dontShowMessageAgain = False

    def __init__(self, editor, def_enc=None):
        self.editor = editor
        global DEF_ENC
        DEF_ENC = def_enc or editor.mcedit.def_enc
        rect = editor.mcedit.rect
        GLViewport.__init__(self, rect)

        # Declare a pseudo showCommands function, since it is called by other objects before its creation in mouse_move.
        self.showCommands = lambda:None

        near = 0.5
        far = 4000.0

        self.near = near
        self.far = far

        self.brake = False
        self.lastTick = datetime.now()
        # self.nearheight = near * tang

        self.cameraPosition = (16., 45., 16.)
        self.velocity = [0., 0., 0.]

        self.yaw = -45.  # degrees
        self._pitch = 0.1

        self.cameraVector = self._cameraVector()

        # A state machine to dodge an apparent bug in pygame that generates erroneous mouse move events
        # 0 = bad event already happened
        # 1 = app just started or regained focus since last bad event
        #   2 = mouse cursor was hidden after state 1, next event will be bad
        self.avoidMouseJumpBug = 1

        config.settings.drawSky.addObserver(self)
        config.settings.drawFog.addObserver(self)
        config.settings.superSecretSettings.addObserver(self)
        config.settings.showCeiling.addObserver(self)
        config.controls.cameraAccel.addObserver(self, "accelFactor")
        config.controls.cameraMaxSpeed.addObserver(self, "maxSpeed")
        config.controls.cameraBrakingSpeed.addObserver(self, "brakeMaxSpeed")
        config.controls.invertMousePitch.addObserver(self)
        config.controls.autobrake.addObserver(self)
        config.controls.swapAxes.addObserver(self)
        config.settings.compassToggle.addObserver(self)

        config.settings.fov.addObserver(self, "fovSetting", callback=self.updateFov)

        self.mouseVector = (0, 0, 0)

        self.root = self.get_root()
        self.hoveringCommandBlock = [False, ""]
        self.block_info_parsers = None
        # self.add(DebugDisplay(self, "cameraPosition", "blockFaceUnderCursor", "mouseVector", "mouse3dPoint"))

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, val):
        self._pitch = min(89.999, max(-89.999, val))

    def updateFov(self, val=None):
        hfov = self.fovSetting
        fov = numpy.degrees(2.0 * numpy.arctan(self.size[0] / self.size[1] * numpy.tan(numpy.radians(hfov) * 0.5)))

        self.fov = fov
        self.tang = numpy.tan(numpy.radians(fov))

    def stopMoving(self):
        self.velocity = [0, 0, 0]

    def brakeOn(self):
        self.brake = True

    def brakeOff(self):
        self.brake = False

    tickInterval = 1000 / config.settings.targetFPS.get()

    oldPosition = (0, 0, 0)

    flyMode = config.settings.flyMode.property()

    def tickCamera(self, frameStartTime, inputs, inSpace):
        timePassed = (frameStartTime - self.lastTick).microseconds
        if timePassed <= self.tickInterval * 1000 or not pygame.key.get_focused():
            return

        self.lastTick = frameStartTime
        timeDelta = float(timePassed) / 1000000.
        timeDelta = min(timeDelta, 0.125)  # 8fps lower limit!
        drag = config.controls.cameraDrag.get()
        accel_factor = drag + config.controls.cameraAccel.get()

        # if we're in space, move faster

        drag_epsilon = 10.0 * timeDelta

        if self.brake:
            max_speed = self.brakeMaxSpeed
        else:
            max_speed = self.maxSpeed

        if inSpace or self.root.sprint:
            accel_factor *= 3.0
            max_speed *= 3.0
            self.root.sprint = False
        elif config.settings.viewMode.get() == "Chunk":
            accel_factor *= 2.0
            max_speed *= 2.0

        pi = self.editor.cameraPanKeys
        mouseSpeed = config.controls.mouseSpeed.get()
        self.yaw += pi[0] * mouseSpeed
        self.pitch += pi[1] * mouseSpeed

        if config.settings.viewMode.get() == "Chunk":
            (dx, dy, dz) = (0, -0.25, -1)
            self.yaw = -180
            self.pitch = 10
        elif self.flyMode:
            (dx, dy, dz) = self._anglesToVector(self.yaw, 0)
        elif self.swapAxes:
            p = self.pitch
            if p > 80:
                p = 0

            (dx, dy, dz) = self._anglesToVector(self.yaw, p)

        else:
            (dx, dy, dz) = self._cameraVector()

        velocity = self.velocity  # xxx learn to use matrix/vector libs
        i = inputs
        yaw = numpy.radians(self.yaw)
        cosyaw = -numpy.cos(yaw)
        sinyaw = numpy.sin(yaw)

        directedInputs = mceutils.normalize((
            i[0] * cosyaw + i[2] * dx,
            i[1] + i[2] * dy,
            i[2] * dz - i[0] * sinyaw,
        ))

        # give the camera an impulse according to the state of the inputs and in the direction of the camera
        cameraAccel = map(lambda x: x * accel_factor * timeDelta, directedInputs)
        # cameraImpulse = map(lambda x: x*impulse_factor, directedInputs)

        newVelocity = map(lambda a, b: a + b, velocity, cameraAccel)
        velocityDir, speed = mceutils.normalize_size(newVelocity)

        # apply drag
        if speed:
            if self.autobrake and not any(inputs):
                speed *= 0.15
            else:

                sign = speed / abs(speed)
                speed = abs(speed)
                speed = speed - (drag * timeDelta)
                if speed < 0.0:
                    speed = 0.0
                speed *= sign

        speed = max(-max_speed, min(max_speed, speed))

        if abs(speed) < drag_epsilon:
            speed = 0

        velocity = map(lambda a: a * speed, velocityDir)

        # velocity = map(lambda p,d: p + d, velocity, cameraImpulse)
        d = map(lambda a, b: abs(a - b), self.cameraPosition, self.oldPosition)
        if d[0] + d[2] > 32.0:
            self.oldPosition = self.cameraPosition
            self.updateFloorQuad()

        self.cameraPosition = map(lambda p, d: p + d * timeDelta, self.cameraPosition, velocity)
        if self.cameraPosition[1] > 3800.:
            self.cameraPosition[1] = 3800.
        elif self.cameraPosition[1] < -1000.:
            self.cameraPosition[1] = -1000.

        self.velocity = velocity
        self.cameraVector = self._cameraVector()

        self.editor.renderer.position = self.cameraPosition
        if self.editor.currentTool.previewRenderer:
            self.editor.currentTool.previewRenderer.position = self.cameraPosition

    def setModelview(self):
        pos = self.cameraPosition
        look = numpy.array(self.cameraPosition)
        look = look.astype(float) + self.cameraVector
        up = (0, 1, 0)
        GLU.gluLookAt(pos[0], pos[1], pos[2],
                      look[0], look[1], look[2],
                      up[0], up[1], up[2])

    def _cameraVector(self):
        return self._anglesToVector(self.yaw, self.pitch)

    @staticmethod
    def _anglesToVector(yaw, pitch):
        def nanzero(x):
            if isnan(x):
                return 0
            else:
                return x

        dx = -math.sin(math.radians(yaw)) * math.cos(math.radians(pitch))
        dy = -math.sin(math.radians(pitch))
        dz = math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
        return map(nanzero, [dx, dy, dz])

    def updateMouseVector(self):
        self.mouseVector = self._mouseVector()

    def _mouseVector(self):
        """
            returns a vector reflecting a ray cast from the camera
        position to the mouse position on the near plane
        """
        x, y = mouse.get_pos()
        # if (x, y) not in self.rect:
        # return (0, 0, 0);  # xxx

        y = self.root.height - y
        point1 = unproject(x, y, 0.0)
        point2 = unproject(x, y, 1.0)
        v = numpy.array(point2) - point1
        v = mceutils.normalize(v)
        return v

    def _blockUnderCursor(self, center=False):
        """
            returns a point in 3d space that was determined by
         reading the depth buffer value
        """
        try:
            GL.glReadBuffer(GL.GL_BACK)
        except Exception:
            logging.exception('Exception during glReadBuffer')
        ws = self.root.size
        if center:
            x, y = ws
            x //= 2
            y //= 2
        else:
            x, y = mouse.get_pos()
        if (x < 0 or y < 0 or x >= ws[0] or
                    y >= ws[1]):
            return 0, 0, 0

        y = ws[1] - y

        try:
            pixel = GL.glReadPixels(x, y, 1, 1, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT)
            newpoint = unproject(x, y, pixel[0])
        except Exception:
            return 0, 0, 0

        return newpoint

    def updateBlockFaceUnderCursor(self):
        focusPair = None
        if not self.enableMouseLag or self.editor.frames & 1:
            self.updateMouseVector()
            if self.editor.mouseEntered:
                if not self.mouseMovesCamera:
                    try:
                        focusPair = raycaster.firstBlock(self.cameraPosition, self._mouseVector(), self.editor.level,
                                                         100, config.settings.viewMode.get())
                    except TooFarException:
                        mouse3dPoint = self._blockUnderCursor()
                        focusPair = self._findBlockFaceUnderCursor(mouse3dPoint)
                elif self.editor.longDistanceMode:
                    mouse3dPoint = self._blockUnderCursor(True)
                    focusPair = self._findBlockFaceUnderCursor(mouse3dPoint)

            # otherwise, find the block at a controllable distance in front of the camera
            if focusPair is None:
                if self.blockFaceUnderCursor is None or self.mouseMovesCamera:
                    focusPair = (self.getCameraPoint(), (0, 0, 0))
                else:
                    focusPair = self.blockFaceUnderCursor

            try:
                if focusPair[0] is not None and self.editor.level.tileEntityAt(*focusPair[0]):
                    changed = False
                    te = self.editor.level.tileEntityAt(*focusPair[0])
                    backupTE = copy.deepcopy(te)
                    if te["id"].value == "Sign" or MCEDIT_IDS.GET(e["id"].value) in ("DEF_BLOCKS_STANDING_SIGN", "DEFS_BLOCKS_WALL_SIGN"):
                        if "Text1" in te and "Text2" in te and "Text3" in te and "Text4" in te:
                            for i in xrange(1,5):
                                if len(te["Text"+str(i)].value) > 32767:
                                    te["Text"+str(i)] = pymclevel.TAG_String(str(te["Text"+str(i)].value)[:32767])
                                    changed = True
                    if changed:
                        response = None
                        if not self.dontShowMessageAgain:
                            response = ask("Found a sign that exceeded the maximum character limit. Automatically trimmed the sign to prevent crashes.", responses=["Ok", "Don't show this again"])
                        if response is not None and response == "Don't show this again":
                            self.dontShowMessageAgain = True
                        op = SignEditOperation(self.editor, self.editor.level, te, backupTE)
                        self.editor.addOperation(op)
                        if op.canUndo:
                            self.editor.addUnsavedEdit()
            except:
                pass

            self.blockFaceUnderCursor = focusPair

    def _findBlockFaceUnderCursor(self, projectedPoint):
        """Returns a (pos, Face) pair or None if one couldn't be found"""
        d = [0, 0, 0]

        try:
            intProjectedPoint = map(int, map(numpy.floor, projectedPoint))
        except ValueError:
            return None  # catch NaNs
        intProjectedPoint[1] = max(-1, intProjectedPoint[1])

        # find out which face is under the cursor.  xxx do it more precisely
        faceVector = ((projectedPoint[0] - (intProjectedPoint[0] + 0.5)),
                      (projectedPoint[1] - (intProjectedPoint[1] + 0.5)),
                      (projectedPoint[2] - (intProjectedPoint[2] + 0.5))
        )

        av = map(abs, faceVector)

        i = av.index(max(av))
        delta = faceVector[i]
        if delta < 0:
            d[i] = -1
        else:
            d[i] = 1

        potentialOffsets = []

        try:
            block = self.editor.level.blockAt(*intProjectedPoint)
        except (EnvironmentError, pymclevel.ChunkNotPresent):
            return intProjectedPoint, d

        if block == pymclevel.alphaMaterials.SnowLayer.ID:
            potentialOffsets.append((0, 1, 0))
        else:
            # discard any faces that aren't likely to be exposed
            for face, offsets in pymclevel.faceDirections:
                point = map(lambda a, b: a + b, intProjectedPoint, offsets)
                try:
                    neighborBlock = self.editor.level.blockAt(*point)
                    if block != neighborBlock:
                        potentialOffsets.append(offsets)
                except (EnvironmentError, pymclevel.ChunkNotPresent):
                    pass

        # check each component of the face vector to see if that face is exposed
        if tuple(d) not in potentialOffsets:
            av[i] = 0
            i = av.index(max(av))
            d = [0, 0, 0]
            delta = faceVector[i]
            if delta < 0:
                d[i] = -1
            else:
                d[i] = 1
            if tuple(d) not in potentialOffsets:
                av[i] = 0
                i = av.index(max(av))
                d = [0, 0, 0]
                delta = faceVector[i]
                if delta < 0:
                    d[i] = -1
                else:
                    d[i] = 1

                if tuple(d) not in potentialOffsets:
                    if len(potentialOffsets):
                        d = potentialOffsets[0]
                    else:
                        # use the top face as a fallback
                        d = [0, 1, 0]

        return intProjectedPoint, d

    @property
    def ratio(self):
        return self.width / float(self.height)

    startingMousePosition = None

    def mouseLookOn(self):
        self.root.capture_mouse(self)
        self.focus_switch = None
        self.startingMousePosition = mouse.get_pos()

        if self.avoidMouseJumpBug == 1:
            self.avoidMouseJumpBug = 2

    def mouseLookOff(self):
        self.root.capture_mouse(None)
        if self.startingMousePosition:
            mouse.set_pos(*self.startingMousePosition)
        self.startingMousePosition = None

    @property
    def mouseMovesCamera(self):
        return self.root.captured_widget is not None

    def toggleMouseLook(self):
        if not self.mouseMovesCamera:
            self.mouseLookOn()
        else:
            self.mouseLookOff()

    # mobs is overrided in __init__
    mobs = pymclevel.Entity.monsters + ["[Custom]"]

    @mceutils.alertException
    def editMonsterSpawner(self, point):
        mobs = self.mobs
        _mobs = {}
        # Get the mobs from the versionned data
        from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
        if MCEDIT_DEFS.get('spawner_monsters'):
            mobs = []
            for a in MCEDIT_DEFS['spawner_monsters']:
                _id = MCEDIT_IDS[a]
                name = _(MCEDIT_DEFS[_id]['name'])
                _mobs[name] = a
                _mobs[a] = name
                mobs.append(name)

        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String(MCEDIT_DEFS.get("MobSpawner", "MobSpawner"))
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["Delay"] = pymclevel.TAG_Short(120)
            tileEntity["EntityId"] = pymclevel.TAG_String(MCEDIT_DEFS.get(mobs[0], mobs[0]))
            self.editor.level.addTileEntity(tileEntity)

        panel = Dialog()

        def addMob(id):
            if id not in mobs:
                mobs.insert(0, id)
                mobTable.selectedIndex = 0

        def selectTableRow(i, evt):
            if mobs[i] == "[Custom]":
                id = input_text("Type in an EntityID for this spawner. Invalid IDs may crash Minecraft.", 150)
                if id:
                    addMob(id)
                else:
                    return
                mobTable.selectedIndex = mobs.index(id)
            else:
                mobTable.selectedIndex = i

            if evt.num_clicks == 2:
                panel.dismiss()

        mobTable = TableView(columns=(
            TableColumn("", 200),
        )
        )
        mobTable.num_rows = lambda: len(mobs)
        mobTable.row_data = lambda i: (mobs[i],)
        mobTable.row_is_selected = lambda x: x == mobTable.selectedIndex
        mobTable.click_row = selectTableRow
        mobTable.selectedIndex = 0

        def selectedMob():
            val = mobs[mobTable.selectedIndex]
            return _mobs.get(val, val)

        def cancel():
            mobs[mobTable.selectedIndex] = id
            panel.dismiss()

        if "EntityId" in tileEntity:
            _id = tileEntity["EntityId"].value
#             id = MCEDIT_DEFS.get(MCEDIT_IDS.get(_id, _id), {}).get("name", _id)
        elif "SpawnData" in tileEntity:
            _id = tileEntity["SpawnData"]["id"].value
        else:
            _id = "[Custom]"

        id = MCEDIT_DEFS.get(MCEDIT_IDS.get(_id, _id), {}).get("name", _id)

        addMob(id)

        mobTable.selectedIndex = mobs.index(id)
        oldChoiceCol = Column((Label(_("Current: ") + _mobs.get(id, id), align='l', width=200), ))
        newChoiceCol = Column((ValueDisplay(width=200, get_value=lambda: _("Change to: ") + selectedMob()), mobTable))

        lastRow = Row((Button("OK", action=panel.dismiss), Button("Cancel", action=cancel)))
        panel.add(Column((oldChoiceCol, newChoiceCol, lastRow)))
        panel.shrink_wrap()
        panel.present()

        class MonsterSpawnerEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                self.level.addTileEntity(tileEntity)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntity)
                self.level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

            def redo(self):
                self.level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

        if id != selectedMob():
            if "EntityId" in tileEntity:
                tileEntity["EntityId"] = pymclevel.TAG_String(selectedMob())
            if "SpawnData" in tileEntity:
                # Try to not clear the spawn data, but only update the mob id
#                 tileEntity["SpawnData"] = pymclevel.TAG_Compound()
                tag_id = pymclevel.TAG_String(selectedMob())
                if "id" in tileEntity["SpawnData"]:
                    tag_id.name = "id"
                    tileEntity["SpawnData"]["id"] = tag_id
                if "EntityId" in tileEntity["SpawnData"]:
                    tileEntity["SpawnData"]["EntityId"] = tag_id
            if "SpawnPotentials" in tileEntity:
                for potential in tileEntity["SpawnPotentials"]:
                    if "Entity" in potential:
                        # MC 1.9+
                        if potential["Entity"]["id"].value == id or ("EntityId" in potential["Entity"] and potential["Entity"]["EntityId"].value == id):
                            potential["Entity"] = pymclevel.TAG_Compound()
                            potential["Entity"]["id"] = pymclevel.TAG_String(selectedMob())
                    elif "Properties" in potential:
                        # MC before 1.9
                        if "Type" in potential and potential["Type"].value == id:
                            potential["Type"] = pymclevel.TAG_String(selectedMob())
                        # We also can change some other values in the Properties tag, but it is useless in MC 1.8+.
                        # The fact is this data will not be updated by the game after the mob type is changed, but the old mob will not spawn.
#                         put_entityid = False
#                         put_id = False
#                         if "EntityId" in potential["Properties"] and potential["Properties"]["EntityId"].value == id:
#                             put_entityid = True
#                         if "id" in potential["Properties"] and potential["Properties"]["id"].value == id:
#                             put_id = True
#                         new_props = pymclevel.TAG_Compound()
#                         if put_entityid:
#                             new_props["EntityId"] = pymclevel.TAG_String(selectedMob())
#                         if put_id:
#                             new_props["id"] = pymclevel.TAG_String(selectedMob())
#                         potential["Properties"] = new_props
            op = MonsterSpawnerEditOperation(self.editor, self.editor.level)
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @mceutils.alertException
    def editJukebox(self, point):
        discs = {
            "[No Record]": None,
            "13": 2256,
            "cat": 2257,
            "blocks": 2258,
            "chirp": 2259,
            "far": 2260,
            "mall": 2261,
            "mellohi": 2262,
            "stal": 2263,
            "strad": 2264,
            "ward": 2265,
            "11": 2266,
            "wait": 2267
        }

        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String("RecordPlayer")
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            self.editor.level.addTileEntity(tileEntity)

        panel = Dialog()

        def selectTableRow(i, evt):
            discTable.selectedIndex = i

            if evt.num_clicks == 2:
                panel.dismiss()

        discTable = TableView(columns=(
            TableColumn("", 200),
        )
        )
        discTable.num_rows = lambda: len(discs)
        discTable.row_data = lambda i: (selectedDisc(i),)
        discTable.row_is_selected = lambda x: x == discTable.selectedIndex
        discTable.click_row = selectTableRow
        discTable.selectedIndex = 0

        def selectedDisc(id):
            if id == 0:
                return "[No Record]"
            return discs.keys()[discs.values().index(id + 2255)]

        def cancel():
            if id == "[No Record]":
                discTable.selectedIndex = 0
            else:
                discTable.selectedIndex = discs[id] - 2255
            panel.dismiss()

        if "RecordItem" in tileEntity:
            if tileEntity["RecordItem"]["id"].value == "minecraft:air":
                id = "[No Record]"
            else:
                id = tileEntity["RecordItem"]["id"].value[17:]
        elif "Record" in tileEntity:
            if tileEntity["Record"].value == 0:
                id = "[No Record]"
            else:
                id = selectedDisc(tileEntity["Record"].value - 2255)
        else:
            id = "[No Record]"

        if id == "[No Record]":
            discTable.selectedIndex = 0
        else:
            discTable.selectedIndex = discs[id] - 2255

        oldChoiceCol = Column((Label(_("Current: ") + id, align='l', width=200), ))
        newChoiceCol = Column((ValueDisplay(width=200, get_value=lambda: _("Change to: ") + selectedDisc(discTable.selectedIndex)), discTable))

        lastRow = Row((Button("OK", action=panel.dismiss), Button("Cancel", action=cancel)))
        panel.add(Column((oldChoiceCol, newChoiceCol, lastRow)))
        panel.shrink_wrap()
        panel.present()

        class JukeboxEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                self.level.addTileEntity(tileEntity)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntity)
                self.level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

            def redo(self):
                self.level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

        if id != selectedDisc(discTable.selectedIndex):
            if "RecordItem" in tileEntity:
                del tileEntity["RecordItem"]
            if discTable.selectedIndex == 0:
                tileEntity["Record"] = pymclevel.TAG_Int(0)
                self.editor.level.setBlockDataAt(tileEntity["x"].value, tileEntity["y"].value, tileEntity["z"].value, 0)
            else:
                tileEntity["Record"] = pymclevel.TAG_Int(discTable.selectedIndex + 2255)
                self.editor.level.setBlockDataAt(tileEntity["x"].value, tileEntity["y"].value, tileEntity["z"].value, 1)
            op = JukeboxEditOperation(self.editor, self.editor.level)
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @mceutils.alertException
    def editNoteBlock(self, point):
        notes = [
            "F# (0.5)", "G (0.53)", "G# (0.56)",
            "A (0.6)", "A# (0.63)", "B (0.67)",
            "C (0.7)", "C# (0.75)", "D (0.8)",
            "D# (0.85)", "E (0.9)", "F (0.95)",
            "F# (1.0)", "G (1.05)", "G# (1.1)",
            "A (1.2)", "A# (1.25)", "B (1.32)",
            "C (1.4)", "C# (1.5)", "D (1.6)",
            "D# (1.7)", "E (1.8)", "F (1.9)",
            "F# (2.0)"
        ]

        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String(MCEDIT_DEFS.get("MobSpawner", "MobSpawner"))
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["note"] = pymclevel.TAG_Byte(0)
            self.editor.level.addTileEntity(tileEntity)

        panel = Dialog()

        def selectTableRow(i, evt):
            noteTable.selectedIndex = i

            if evt.num_clicks == 2:
                panel.dismiss()

        noteTable = TableView(columns=(
            TableColumn("", 200),
        )
        )
        noteTable.num_rows = lambda: len(notes)
        noteTable.row_data = lambda i: (notes[i],)
        noteTable.row_is_selected = lambda x: x == noteTable.selectedIndex
        noteTable.click_row = selectTableRow
        noteTable.selectedIndex = 0

        def selectedNote():
            return notes[noteTable.selectedIndex]

        def cancel():
            noteTable.selectedIndex = id
            panel.dismiss()

        id = tileEntity["note"].value

        noteTable.selectedIndex = id

        oldChoiceCol = Column((Label(_("Current: ") + notes[id], align='l', width=200), ))
        newChoiceCol = Column((ValueDisplay(width=200, get_value=lambda: _("Change to: ") + selectedNote()), noteTable))

        lastRow = Row((Button("OK", action=panel.dismiss), Button("Cancel", action=cancel)))
        panel.add(Column((oldChoiceCol, newChoiceCol, lastRow)))
        panel.shrink_wrap()
        panel.present()

        class NoteBlockEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                self.level.addTileEntity(tileEntity)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntity)
                self.level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

            def redo(self):
                self.level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

        if id != noteTable.selectedIndex:
            tileEntity["note"] = pymclevel.TAG_Byte(noteTable.selectedIndex)
            op = NoteBlockEditOperation(self.editor, self.editor.level)
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @mceutils.alertException
    def editSign(self, point):

        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        linekeys = ["Text" + str(i) for i in range(1, 5)]

        # From version 1.8, signs accept Json format.
        # 1.9 does no more support the old raw string fomat.
        splitVersion = self.editor.level.gameVersion.split('.')
        newFmtVersion = ['1','9']
        fmt = ""
        json_fmt = False

        f = lambda a,b: (a + (['0'] * max(len(b) - len(a), 0)), b + (['0'] * max(len(a) - len(b), 0)))
        if False not in map(lambda x,y: (int(x) if x.isdigit() else x) >= (int(y) if y.isdigit() else y),*f(splitVersion, newFmtVersion))[:2]:
            json_fmt = True
            fmt = '{"text":""}'

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
             # Don't know how to handle the difference between wall and standing signs for now...
             # Just let this like it is until we can find the way!
            tileEntity["id"] = pymclevel.TAG_String("Sign")
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            for l in linekeys:
                tileEntity[l] = pymclevel.TAG_String(fmt)
            self.editor.level.addTileEntity(tileEntity)

        panel = Dialog()

        lineFields = [TextFieldWrapped(width=400) for l in linekeys]
        for l, f in zip(linekeys, lineFields):

            f.value = tileEntity[l].value

            # Double quotes handling for olf sign text format.
            if f.value == 'null':
                f.value = fmt
            elif json_fmt and f.value == '':
                f.value = fmt
            else:
                if f.value.startswith('"') and f.value.endswith('"'):
                    f.value = f.value[1:-1]
                if '\\"' in f.value:
                    f.value = f.value.replace('\\"', '"')

        colors = [
            u"§0  Black",
            u"§1  Dark Blue",
            u"§2  Dark Green",
            u"§3  Dark Aqua",
            u"§4  Dark Red",
            u"§5  Dark Purple",
            u"§6  Gold",
            u"§7  Gray",
            u"§8  Dark Gray",
            u"§9  Blue",
            u"§a  Green",
            u"§b  Aqua",
            u"§c  Red",
            u"§d  Light Purple",
            u"§e  Yellow",
            u"§f  White",
        ]

        def menu_picked(index):
            c = u"§%d"%index
            currentField = panel.focus_switch.focus_switch
            currentField.text += c  # xxx view hierarchy
            currentField.insertion_point = len(currentField.text)

        def changeSign():
            unsavedChanges = False
            fmt = '"{}"'
            u_fmt = u'"%s"'
            if json_fmt:
                fmt = '{}'
                u_fmt = u'%s'
            for l, f in zip(linekeys, lineFields):
                oldText = fmt.format(tileEntity[l])
                tileEntity[l] = pymclevel.TAG_String(u_fmt%f.value[:255])
                if fmt.format(tileEntity[l]) != oldText and not unsavedChanges:
                    unsavedChanges = True
            if unsavedChanges:
                op = SignEditOperation(self.editor, self.editor.level, tileEntity, undoBackupEntityTag)
                self.editor.addOperation(op)
                if op.canUndo:
                    self.editor.addUnsavedEdit()
            panel.dismiss()

        colorMenu = MenuButton("Add Color Code...", colors, menu_picked=menu_picked)

        row = Row((Button("OK", action=changeSign), Button("Cancel", action=panel.dismiss)))

        column = [Label("Edit Sign")] + lineFields + [colorMenu, row]

        panel.add(Column(column))
        panel.shrink_wrap()
        panel.present()

    @mceutils.alertException
    def editSkull(self, point):
        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)
        skullTypes = {
            "Skeleton": 0,
            "Wither Skeleton": 1,
            "Zombie": 2,
            "Player": 3,
            "Creeper": 4,
        }

        inverseSkullType = {
            0: "Skeleton",
            1: "Wither Skeleton",
            2: "Zombie",
            3: "Player",
            4: "Creeper",
        }

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            # Don't know how to handle the difference between skulls in this context signs for now...
            # Tests nedded!
            tileEntity["id"] = pymclevel.TAG_String("Skull")
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["SkullType"] = pymclevel.TAG_Byte(3)
            self.editor.level.addTileEntity(tileEntity)

        titleLabel = Label("Edit Skull Data")
        usernameField = TextFieldWrapped(width=150)
        panel = Dialog()
        skullMenu = ChoiceButton(map(str, skullTypes))

        if "Owner" in tileEntity:
            usernameField.value = str(tileEntity["Owner"]["Name"].value)
        elif "ExtraType" in tileEntity:
            usernameField.value = str(tileEntity["ExtraType"].value)
        else:
            usernameField.value = ""

        oldUserName = usernameField.value
        skullMenu.selectedChoice = inverseSkullType[tileEntity["SkullType"].value]
        oldSelectedSkull = skullMenu.selectedChoice

        class SkullEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                self.level.addTileEntity(tileEntity)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntity)
                self.level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

            def redo(self):
                self.level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

        def updateSkull():
            if usernameField.value != oldUserName or oldSelectedSkull != skullMenu.selectedChoice:
                tileEntity["ExtraType"] = pymclevel.TAG_String(usernameField.value)
                tileEntity["SkullType"] = pymclevel.TAG_Byte(skullTypes[skullMenu.selectedChoice])
                if "Owner" in tileEntity:
                    del tileEntity["Owner"]
                op = SkullEditOperation(self.editor, self.editor.level)
                self.editor.addOperation(op)
                if op.canUndo:
                    self.editor.addUnsavedEdit()

            chunk = self.editor.level.getChunk(int(int(point[0]) / 16), int(int(point[2]) / 16))
            chunk.dirty = True
            panel.dismiss()

        okBTN = Button("OK", action=updateSkull)
        cancel = Button("Cancel", action=panel.dismiss)

        column = [titleLabel, usernameField, skullMenu, okBTN, cancel]
        panel.add(Column(column))
        panel.shrink_wrap()
        panel.present()

    @mceutils.alertException
    def editCommandBlock(self, point):
        panel = Dialog()
        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String(MCEDIT_DEFS.get("Control", "Control"))
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["Command"] = pymclevel.TAG_String()
            tileEntity["CustomName"] = pymclevel.TAG_String("@")
            tileEntity["TrackOutput"] = pymclevel.TAG_Byte(0)
            tileEntity["SuccessCount"] = pymclevel.TAG_Int(0)
            self.editor.level.addTileEntity(tileEntity)

        titleLabel = Label("Edit Command Block")
        commandField = TextFieldWrapped(width=650)
        nameField = TextFieldWrapped(width=200)
        successField = IntInputRow("SuccessCount", min=0, max=15)
        trackOutput = CheckBox()

        # Fix for the '§ is Ä§' issue
#         try:
#             commandField.value = tileEntity["Command"].value.decode("unicode-escape")
#         except:
#             commandField.value = tileEntity["Command"].value
        commandField.value = tileEntity["Command"].value

        oldCommand = commandField.value
        trackOutput.value = tileEntity["TrackOutput"].value
        oldTrackOutput = trackOutput.value
        nameField.value = tileEntity.get("CustomName", TAG_String("@")).value
        oldNameField = nameField.value
        successField.subwidgets[1].value = tileEntity.get("SuccessCount", pymclevel.TAG_Int(0)).value
        oldSuccess = successField.subwidgets[1].value

        class CommandBlockEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                self.level.addTileEntity(tileEntity)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntity)
                self.level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

            def redo(self):
                self.level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

        def updateCommandBlock():
            if oldCommand != commandField.value or oldTrackOutput != trackOutput.value or oldNameField != nameField.value or oldSuccess != successField.subwidgets[1].value:
                tileEntity["Command"] = pymclevel.TAG_String(commandField.value)
                tileEntity["TrackOutput"] = pymclevel.TAG_Byte(trackOutput.value)
                tileEntity["CustomName"] = pymclevel.TAG_String(nameField.value)
                tileEntity["SuccessCount"] = pymclevel.TAG_Int(successField.subwidgets[1].value)

                op = CommandBlockEditOperation(self.editor, self.editor.level)
                self.editor.addOperation(op)
                if op.canUndo:
                    self.editor.addUnsavedEdit()

            chunk = self.editor.level.getChunk(int(int(point[0]) / 16), int(int(point[2]) / 16))
            chunk.dirty = True
            panel.dismiss()

        okBTN = Button("OK", action=updateCommandBlock)
        cancel = Button("Cancel", action=panel.dismiss)
        column = [titleLabel, Label("Command:"), commandField, Row((Label("Custom Name:"), nameField)), successField,
                  Row((Label("Track Output"), trackOutput)), okBTN, cancel]
        panel.add(Column(column))
        panel.shrink_wrap()
        panel.present()

        return

    @mceutils.alertException
    def editContainer(self, point, containerID):
        tileEntityTag = self.editor.level.tileEntityAt(*point)
        if tileEntityTag is None:
            tileEntityTag = pymclevel.TileEntity.Create(containerID)
            pymclevel.TileEntity.setpos(tileEntityTag, point)
            self.editor.level.addTileEntity(tileEntityTag)

        if tileEntityTag["id"].value != containerID:
            return

        undoBackupEntityTag = copy.deepcopy(tileEntityTag)

        def itemProp(key):
            # xxx do validation here
            def getter(self):
                if 0 == len(tileEntityTag["Items"]):
                    return 0
                return tileEntityTag["Items"][self.selectedItemIndex][key].value

            def setter(self, val):
                if 0 == len(tileEntityTag["Items"]):
                    return
                self.dirty = True
                tileEntityTag["Items"][self.selectedItemIndex][key].value = val

            return property(getter, setter)

        class ChestWidget(Widget):
            dirty = False
            Slot = itemProp("Slot")
            id = itemProp("id")
            Damage = itemProp("Damage")
            Count = itemProp("Count")
            itemLimit = pymclevel.TileEntity.maxItems.get(containerID, 26)

        def slotFormat(slot):
            slotNames = pymclevel.TileEntity.slotNames.get(containerID)
            if slotNames:
                return slotNames.get(slot, slot)
            return slot

        chestWidget = ChestWidget()
        chestItemTable = TableView(columns=[
            TableColumn("Slot", 60, "l", fmt=slotFormat),
            TableColumn("ID / ID Name", 345, "l"),
            TableColumn("DMG", 50, "l"),
            TableColumn("Count", 65, "l"),

            TableColumn("Name", 260, "l"),
        ])

        def itemName(id, damage):
            try:
                return pymclevel.items.items.findItem(id, damage).name
            except pymclevel.items.ItemNotFound:
                return "Unknown Item"

        def getRowData(i):
            item = tileEntityTag["Items"][i]
            slot, id, damage, count = item["Slot"].value, item["id"].value, item["Damage"].value, item["Count"].value
            return slot, id, damage, count, itemName(id, damage)

        chestWidget.selectedItemIndex = 0

        def selectTableRow(i, evt):
            chestWidget.selectedItemIndex = i
            # Disabling the item selector for now, since we need PE items resources.
#             if evt.num_clicks > 1:
#                 selectButtonAction()

        def changeValue(data):
            s, i, c, d = data
            s = int(s)
            s_idx = 0
            chestWidget.Slot = s
            chestWidget.id = i
            chestWidget.Count = int(c)
            chestWidget.Damage = int(d)


        chestItemTable.num_rows = lambda: len(tileEntityTag["Items"])
        chestItemTable.row_data = getRowData
        chestItemTable.row_is_selected = lambda x: x == chestWidget.selectedItemIndex
        chestItemTable.click_row = selectTableRow
        chestItemTable.change_value = changeValue

        def selectButtonAction():
            SlotEditor(chestItemTable,
                       (chestWidget.Slot, chestWidget.id or u"", chestWidget.Count, chestWidget.Damage)
                       ).present()

        maxSlot = pymclevel.TileEntity.maxItems.get(tileEntityTag["id"].value, 27) - 1
        fieldRow = (
            IntInputRow("Slot: ", ref=AttrRef(chestWidget, 'Slot'), min=0, max=maxSlot),
            BasicTextInputRow("ID / ID Name: ", ref=AttrRef(chestWidget, 'id'), width=300),
            # Text to allow the input of internal item names
            IntInputRow("DMG: ", ref=AttrRef(chestWidget, 'Damage'), min=0, max=32767),
            IntInputRow("Count: ", ref=AttrRef(chestWidget, 'Count'), min=-1, max=64),
            # This button is inactive for now, because we need to work with different IDs types:
            # * The 'human' IDs: Stone, Glass, Swords...
            # * The MC ones: minecraft:stone, minecraft:air...
            # * The PE ones: 0:0, 1:0...
#             Button("Select", action=selectButtonAction)
        )

        def deleteFromWorld():
            i = chestWidget.selectedItemIndex
            item = tileEntityTag["Items"][i]
            id = item["id"].value
            Damage = item["Damage"].value

            deleteSameDamage = CheckBoxLabel("Only delete items with the same damage value")
            deleteBlocksToo = CheckBoxLabel("Also delete blocks placed in the world")
            if id not in (8, 9, 10, 11):  # fluid blocks
                deleteBlocksToo.value = True

            w = wrapped_label(
                "WARNING: You are about to modify the entire world. This cannot be undone. Really delete all copies of this item from all land, chests, furnaces, dispensers, dropped items, item-containing tiles, and player inventories in this world?",
                60)
            col = (w, deleteSameDamage)
            if id < 256:
                col += (deleteBlocksToo,)

            d = Dialog(Column(col), ["OK", "Cancel"])

            if d.present() == "OK":
                def deleteItemsIter():
                    i = 0
                    if deleteSameDamage.value:
                        def matches(t):
                            return t["id"].value == id and t["Damage"].value == Damage
                    else:
                        def matches(t):
                            return t["id"].value == id

                    def matches_itementity(e):
                        if e["id"].value != "Item":
                            return False
                        if "Item" not in e:
                            return False
                        t = e["Item"]
                        return matches(t)

                    for player in self.editor.level.players:
                        tag = self.editor.level.getPlayerTag(player)
                        tag["Inventory"].value = [t for t in tag["Inventory"].value if not matches(t)]

                    for chunk in self.editor.level.getChunks():
                        if id < 256 and deleteBlocksToo.value:
                            matchingBlocks = chunk.Blocks == id
                            if deleteSameDamage.value:
                                matchingBlocks &= chunk.Data == Damage
                            if any(matchingBlocks):
                                chunk.Blocks[matchingBlocks] = 0
                                chunk.Data[matchingBlocks] = 0
                                chunk.chunkChanged()
                                self.editor.invalidateChunks([chunk.chunkPosition])

                        for te in chunk.TileEntities:
                            if "Items" in te:
                                l = len(te["Items"])

                                te["Items"].value = [t for t in te["Items"].value if not matches(t)]
                                if l != len(te["Items"]):
                                    chunk.dirty = True
                        entities = [e for e in chunk.Entities if matches_itementity(e)]
                        if len(entities) != len(chunk.Entities):
                            chunk.Entities.value = entities
                            chunk.dirty = True

                        yield (i, self.editor.level.chunkCount)
                        i += 1

                progressInfo = _("Deleting the item {0} from the entire world ({1} chunks)").format(
                    itemName(chestWidget.id, 0), self.editor.level.chunkCount)

                showProgress(progressInfo, deleteItemsIter(), cancel=True)

                self.editor.addUnsavedEdit()
                chestWidget.selectedItemIndex = min(chestWidget.selectedItemIndex, len(tileEntityTag["Items"]) - 1)

        def deleteItem():
            i = chestWidget.selectedItemIndex
            item = tileEntityTag["Items"][i]
            tileEntityTag["Items"].value = [t for t in tileEntityTag["Items"].value if t is not item]
            chestWidget.selectedItemIndex = min(chestWidget.selectedItemIndex, len(tileEntityTag["Items"]) - 1)

        def deleteEnable():
            return len(tileEntityTag["Items"]) and chestWidget.selectedItemIndex != -1

        def addEnable():
            return len(tileEntityTag["Items"]) < chestWidget.itemLimit

        def addItem():
            slot = 0
            for item in tileEntityTag["Items"]:
                if slot == item["Slot"].value:
                    slot += 1
            if slot >= chestWidget.itemLimit:
                return
            item = pymclevel.TAG_Compound()
            item["id"] = pymclevel.TAG_String("minecraft:")
            item["Damage"] = pymclevel.TAG_Short(0)
            item["Slot"] = pymclevel.TAG_Byte(slot)
            item["Count"] = pymclevel.TAG_Byte(1)
            tileEntityTag["Items"].append(item)

        addItemButton = Button("New Item (1.7+)", action=addItem, enable=addEnable)
        deleteItemButton = Button("Delete This Item", action=deleteItem, enable=deleteEnable)
        deleteFromWorldButton = Button("Delete All Instances Of This Item From World", action=deleteFromWorld,
                                       enable=deleteEnable)
        deleteCol = Column((addItemButton, deleteItemButton, deleteFromWorldButton))

        fieldRow = Row(fieldRow)
        col = Column((chestItemTable, fieldRow, deleteCol))

        chestWidget.add(col)
        chestWidget.shrink_wrap()

        Dialog(client=chestWidget, responses=["Done"]).present()
        level = self.editor.level

        class ChestEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                level.addTileEntity(tileEntityTag)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntityTag)
                level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntityTag), (1, 1, 1))

            def redo(self):
                level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntityTag), (1, 1, 1))

        if chestWidget.dirty:
            op = ChestEditOperation(self.editor, self.editor.level)
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @mceutils.alertException
    def editFlowerPot(self, point):
        panel = Dialog()
        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)
        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String(MCEDIT_DEFS.get("FlowerPot", "FlowerPot"))
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["Item"] = pymclevel.TAG_String("")
            tileEntity["Data"] = pymclevel.TAG_Int(0)
            self.editor.level.addTileEntity(tileEntity)

        titleLabel = Label("Edit Flower Pot")
        Item = TextFieldWrapped(width=300, text=tileEntity["Item"].value)
        oldItem = Item.value
        Data = IntField(width=300,text=str(tileEntity["Data"].value))
        oldData = Data.value

        class FlowerPotEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                self.level.addTileEntity(tileEntity)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntity)
                self.level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

            def redo(self):
                self.level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

        def updateFlowerPot():
            if oldData != Data.value or oldItem != Item.value:
                tileEntity["Item"] = pymclevel.TAG_String(Item.value)
                tileEntity["Data"] = pymclevel.TAG_Int(Data.value)

                op = FlowerPotEditOperation(self.editor, self.editor.level)
                self.editor.addOperation(op)
                if op.canUndo:
                    self.editor.addUnsavedEdit()

                chunk = self.editor.level.getChunk(int(int(point[0]) / 16), int(int(point[2]) / 16))
                chunk.dirty = True
                panel.dismiss()

        okBtn = Button("OK", action=updateFlowerPot)
        cancel = Button("Cancel", action=panel.dismiss)
        panel.add(Column((titleLabel, Row((Label("Item"), Item)), Row((Label("Data"), Data)), okBtn, cancel)))
        panel.shrink_wrap()
        panel.present()

    @mceutils.alertException
    def editEnchantmentTable(self, point):
        panel = Dialog()
        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)
        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String(MCEDIT_DEFS.get("EnchantTable", "EnchantTable"))
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["CustomName"] = pymclevel.TAG_String("")
            self.editor.level.addTileEntity(tileEntity)

        titleLabel = Label("Edit Enchantment Table")
        try:
            name = tileEntity["CustomName"].value
        except:
            name = ""
        name = TextFieldWrapped(width=300, text=name)
        oldName = name.value

        class EnchantmentTableEditOperation(Operation):
            def __init__(self, tool, level):
                self.tool = tool
                self.level = level
                self.undoBackupEntityTag = undoBackupEntityTag
                self.canUndo = False

            def perform(self, recordUndo=True):
                if self.level.saving:
                    alert("Cannot perform action while saving is taking place")
                    return
                self.level.addTileEntity(tileEntity)
                self.canUndo = True

            def undo(self):
                self.redoBackupEntityTag = copy.deepcopy(tileEntity)
                self.level.addTileEntity(self.undoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

            def redo(self):
                self.level.addTileEntity(self.redoBackupEntityTag)
                return pymclevel.BoundingBox(pymclevel.TileEntity.pos(tileEntity), (1, 1, 1))

        def updateEnchantmentTable():
            if oldName != name.value:
                tileEntity["CustomName"] = pymclevel.TAG_String(name.value)

                op = EnchantmentTableEditOperation(self.editor, self.editor.level)
                self.editor.addOperation(op)
                if op.canUndo:
                    self.editor.addUnsavedEdit()

                chunk = self.editor.level.getChunk(int(int(point[0]) / 16), int(int(point[2]) / 16))
                chunk.dirty = True
                panel.dismiss()

        okBtn = Button("OK", action=updateEnchantmentTable)
        cancel = Button("Cancel", action=panel.dismiss)
        panel.add(Column((titleLabel, Row((Label("Custom Name"), name)), okBtn, cancel)))
        panel.shrink_wrap()
        panel.present()

    should_lock = False

    def rightClickDown(self, evt):
        # self.rightMouseDragStart = datetime.now()
        self.should_lock = True
        self.toggleMouseLook()

    def rightClickUp(self, evt):
        if not get_top_widget().is_modal:
            return
        if not self.should_lock and self.editor.level:
            self.should_lock = False
            self.toggleMouseLook()
        # if self.rightMouseDragStart is None:
        #     return

        # td = datetime.now() - self.rightMouseDragStart
        # # except AttributeError:
        # # return
        # # print "RightClickUp: ", td
        # if td.microseconds > 180000:
        #     self.mouseLookOff()

    def leftClickDown(self, evt):
        self.editor.toolMouseDown(evt, self.blockFaceUnderCursor)

        if evt.num_clicks == 2:
            def distance2(p1, p2):
                return numpy.sum(map(lambda a, b: (a - b) ** 2, p1, p2))

            point, face = self.blockFaceUnderCursor
            if point is not None:
                point = map(lambda x: int(numpy.floor(x)), point)
                if self.editor.currentTool is self.editor.selectionTool:
                    try:
                        block = self.editor.level.blockAt(*point)
                        if distance2(point, self.cameraPosition) > 4:
                            blockEditors = {
                                pymclevel.alphaMaterials.MonsterSpawner.ID: self.editMonsterSpawner,
                                pymclevel.alphaMaterials.Sign.ID: self.editSign,
                                pymclevel.alphaMaterials.WallSign.ID: self.editSign,
                                pymclevel.alphaMaterials.MobHead.ID: self.editSkull,
                                pymclevel.alphaMaterials.CommandBlock.ID: self.editCommandBlock,
                                210: self.editCommandBlock,
                                211: self.editCommandBlock,
                                pymclevel.alphaMaterials.Jukebox.ID: self.editJukebox,
                                pymclevel.alphaMaterials.NoteBlock.ID: self.editNoteBlock,
                                pymclevel.alphaMaterials.FlowerPot.ID: self.editFlowerPot,
                                pymclevel.alphaMaterials.EnchantmentTable.ID: self.editEnchantmentTable
                            }
                            edit = blockEditors.get(block)
                            if edit:
                                self.editor.endSelection()
                                edit(point)
                            else:
                                # detect "container" tiles
                                te = self.editor.level.tileEntityAt(*point)
                                if te and "Items" in te and "id" in te:
                                    self.editor.endSelection()
                                    self.editContainer(point, te["id"].value)
                    except (EnvironmentError, pymclevel.ChunkNotPresent):
                        pass

    def leftClickUp(self, evt):
        self.editor.toolMouseUp(evt, self.blockFaceUnderCursor)

    # --- Event handlers ---

    def mouse_down(self, evt):
        button = keys.remapMouseButton(evt.button)
        logging.debug("Mouse down %d @ %s", button, evt.pos)

        if button == 1:
            if sys.platform == "darwin" and evt.ctrl:
                self.rightClickDown(evt)
            else:
                self.leftClickDown(evt)
        elif button == 2:
            self.rightClickDown(evt)
        elif button == 3 and sys.platform == "darwin" and evt.alt:
            self.leftClickDown(evt)
        else:
            evt.dict['keyname'] = "mouse{}".format(button)
            self.editor.key_down(evt)

        self.editor.focus_on(None)
        # self.focus_switch = None

    def mouse_up(self, evt):
        button = keys.remapMouseButton(evt.button)
        logging.debug("Mouse up   %d @ %s", button, evt.pos)
        if button == 1:
            if sys.platform == "darwin" and evt.ctrl:
                self.rightClickUp(evt)
            else:
                self.leftClickUp(evt)
        elif button == 2:
            self.rightClickUp(evt)
        elif button == 3 and sys.platform == "darwin" and evt.alt:
            self.leftClickUp(evt)
        else:
            evt.dict['keyname'] = "mouse{}".format(button)
            self.editor.key_up(evt)

    def mouse_drag(self, evt):
        self.mouse_move(evt)
        self.editor.mouse_drag(evt)

    lastRendererUpdate = datetime.now()

    def mouse_move(self, evt):
        if self.avoidMouseJumpBug == 2:
            self.avoidMouseJumpBug = 0
            return

        def sensitivityAdjust(d):
            return d * config.controls.mouseSpeed.get() / 10.0

        self.editor.mouseEntered = True
        if self.mouseMovesCamera:
            self.should_lock = False
            pitchAdjust = sensitivityAdjust(evt.rel[1])
            if self.invertMousePitch:
                pitchAdjust = -pitchAdjust
            self.yaw += sensitivityAdjust(evt.rel[0])
            self.pitch += pitchAdjust
            if datetime.now() - self.lastRendererUpdate > timedelta(0, 0, 500000):
                self.editor.renderer.loadNearbyChunks()
                self.lastRendererUpdate = datetime.now()

                # adjustLimit = 2

                # self.oldMousePosition = (x, y)
                # if (self.startingMousePosition[0] - x > adjustLimit or self.startingMousePosition[1] - y > adjustLimit or
                # self.startingMousePosition[0] - x < -adjustLimit or self.startingMousePosition[1] - y < -adjustLimit):
                # mouse.set_pos(*self.startingMousePosition)
                #    event.get(MOUSEMOTION)
                #    self.oldMousePosition = (self.startingMousePosition)

        #if config.settings.showCommands.get():

    def activeevent(self, evt):
        if evt.state & 0x2 and evt.gain != 0:
            self.avoidMouseJumpBug = 1

    @property
    def tooltipText(self):
        #if self.hoveringCommandBlock[0] and (self.editor.currentTool is self.editor.selectionTool and self.editor.selectionTool.infoKey == 0):
        #    return self.hoveringCommandBlock[1] or "[Empty]"
        if self.editor.currentTool is self.editor.selectionTool and self.editor.selectionTool.infoKey == 0 and config.settings.showQuickBlockInfo.get():
            point, face = self.blockFaceUnderCursor
            if point:
                if not self.block_info_parsers or (BlockInfoParser.last_level != self.editor.level):
                    self.block_info_parsers = BlockInfoParser.get_parsers(self.editor)
                block = self.editor.level.blockAt(*point)
                if block:
                    if block in self.block_info_parsers:
                        return self.block_info_parsers[block](point)
        return self.editor.currentTool.worldTooltipText

    floorQuad = numpy.array(((-4000.0, 0.0, -4000.0),
                             (-4000.0, 0.0, 4000.0),
                             (4000.0, 0.0, 4000.0),
                             (4000.0, 0.0, -4000.0),
                            ), dtype='float32')

    def updateFloorQuad(self):
        floorQuad = ((-4000.0, 0.0, -4000.0),
                     (-4000.0, 0.0, 4000.0),
                     (4000.0, 0.0, 4000.0),
                     (4000.0, 0.0, -4000.0),
        )

        floorQuad = numpy.array(floorQuad, dtype='float32')
        if self.editor.renderer.inSpace():
            floorQuad *= 8.0
        floorQuad += (self.cameraPosition[0], 0.0, self.cameraPosition[2])
        self.floorQuad = floorQuad
        self.floorQuadList.invalidate()

    def drawFloorQuad(self):
        self.floorQuadList.call(self._drawFloorQuad)

    @staticmethod
    def _drawCeiling():
        lines = []
        minz = minx = -256
        maxz = maxx = 256
        for x in range(minx, maxx + 1, 16):
            lines.append((x, 0, minz))
            lines.append((x, 0, maxz))
        for z in range(minz, maxz + 1, 16):
            lines.append((minx, 0, z))
            lines.append((maxx, 0, z))

        GL.glColor(0.3, 0.7, 0.9)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, numpy.array(lines, dtype='float32'))

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(False)
        GL.glDrawArrays(GL.GL_LINES, 0, len(lines))
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDepthMask(True)

    def drawCeiling(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        # GL.glPushMatrix()
        x, y, z = self.cameraPosition
        x -= x % 16
        z -= z % 16
        y = self.editor.level.Height
        GL.glTranslate(x, y, z)
        self.ceilingList.call(self._drawCeiling)
        GL.glTranslate(-x, -y, -z)

    _floorQuadList = None

    @property
    def floorQuadList(self):
        if not self._floorQuadList:
            self._floorQuadList = glutils.DisplayList()
        return self._floorQuadList

    _ceilingList = None

    @property
    def ceilingList(self):
        if not self._ceilingList:
            self._ceilingList = glutils.DisplayList()
        return self._ceilingList

    @property
    def floorColor(self):
        if self.drawSky:
            return 0.0, 0.0, 1.0, 0.3
        else:
            return 0.0, 1.0, 0.0, 0.15

            # floorColor = (0.0, 0.0, 1.0, 0.1)

    def _drawFloorQuad(self):
        GL.glDepthMask(True)
        GL.glPolygonOffset(DepthOffset.ChunkMarkers + 2, DepthOffset.ChunkMarkers + 2)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, self.floorQuad)
        GL.glColor(*self.floorColor)
        with gl.glEnable(GL.GL_BLEND, GL.GL_DEPTH_TEST, GL.GL_POLYGON_OFFSET_FILL):
            GL.glDrawArrays(GL.GL_QUADS, 0, 4)

    @property
    def drawSky(self):
        return self._drawSky

    @drawSky.setter
    def drawSky(self, val):
        self._drawSky = val
        if self.skyList:
            self.skyList.invalidate()
        if self._floorQuadList:
            self._floorQuadList.invalidate()

    skyList = None

    def drawSkyBackground(self):
        if self.skyList is None:
            self.skyList = glutils.DisplayList()
        self.skyList.call(self._drawSkyBackground)

    def _drawSkyBackground(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)

        quad = numpy.array([-1, -1, -1, 1, 1, 1, 1, -1], dtype='float32')
        if self.editor.level.dimNo == -1:
            colors = numpy.array([0x90, 0x00, 0x00, 0xff,
                                  0x90, 0x00, 0x00, 0xff,
                                  0x90, 0x00, 0x00, 0xff,
                                  0x90, 0x00, 0x00, 0xff, ], dtype='uint8')
        elif self.editor.level.dimNo == 1:
            colors = numpy.array([0x22, 0x27, 0x28, 0xff,
                                  0x22, 0x27, 0x28, 0xff,
                                  0x22, 0x27, 0x28, 0xff,
                                  0x22, 0x27, 0x28, 0xff, ], dtype='uint8')
        else:
            colors = numpy.array([0x48, 0x49, 0xBA, 0xff,
                                  0x8a, 0xaf, 0xff, 0xff,
                                  0x8a, 0xaf, 0xff, 0xff,
                                  0x48, 0x49, 0xBA, 0xff, ], dtype='uint8')

        alpha = 1.0

        if alpha > 0.0:
            if alpha < 1.0:
                GL.glEnable(GL.GL_BLEND)

            GL.glVertexPointer(2, GL.GL_FLOAT, 0, quad)
            GL.glColorPointer(4, GL.GL_UNSIGNED_BYTE, 0, colors)
            GL.glDrawArrays(GL.GL_QUADS, 0, 4)

            if alpha < 1.0:
                GL.glDisable(GL.GL_BLEND)

        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPopMatrix()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPopMatrix()

    enableMouseLag = config.settings.enableMouseLag.property()

    @property
    def drawFog(self):
        return self._drawFog and not self.editor.renderer.inSpace()

    @drawFog.setter
    def drawFog(self, val):
        self._drawFog = val

    fogColor = numpy.array([0.6, 0.8, 1.0, 1.0], dtype='float32')
    fogColorBlack = numpy.array([0.0, 0.0, 0.0, 1.0], dtype='float32')

    def enableFog(self):
        GL.glEnable(GL.GL_FOG)
        if self.drawSky:
            GL.glFogfv(GL.GL_FOG_COLOR, self.fogColor)
        else:
            GL.glFogfv(GL.GL_FOG_COLOR, self.fogColorBlack)

        GL.glFogf(GL.GL_FOG_DENSITY, 0.0001 * config.settings.fogIntensity.get())

    @staticmethod
    def disableFog():
        GL.glDisable(GL.GL_FOG)

    def getCameraPoint(self):
        distance = self.editor.currentTool.cameraDistance
        return [i for i in itertools.imap(lambda p, d: int(numpy.floor(p + d * distance)),
                                          self.cameraPosition,
                                          self.cameraVector)]

    blockFaceUnderCursor = (0, 0, 0), (0, 0, 0)

    viewingFrustum = None

    def setup_projection(self):
        distance = 1.0
        if self.editor.renderer.inSpace():
            distance = 8.0
        GLU.gluPerspective(max(self.fov, 25.0), self.ratio, self.near * distance, self.far * distance)

    def setup_modelview(self):
        self.setModelview()

    def gl_draw(self):
        self.tickCamera(self.editor.frameStartTime, self.editor.cameraInputs, self.editor.renderer.inSpace())
        self.render()

    def render(self):
        self.viewingFrustum = frustum.Frustum.fromViewingMatrix()

        if self.superSecretSettings:
            self.editor.drawStars()
        if self.drawSky:
            self.drawSkyBackground()
        if self.drawFog:
            self.enableFog()

        self.drawFloorQuad()

        self.editor.renderer.viewingFrustum = self.viewingFrustum
        self.editor.renderer.draw()

        if self.showCeiling and not self.editor.renderer.inSpace():
            self.drawCeiling()

        if self.editor.level:
            try:
                self.updateBlockFaceUnderCursor()
            except (EnvironmentError, pymclevel.ChunkNotPresent) as e:
                logging.debug("Updating cursor block: %s", e)
                self.blockFaceUnderCursor = (None, None)

            self.root.update_tooltip()

            (blockPosition, faceDirection) = self.blockFaceUnderCursor
            if None != blockPosition:
                self.editor.updateInspectionString(blockPosition)

                if self.find_widget(mouse.get_pos()) == self:
                    ct = self.editor.currentTool
                    if ct:
                        ct.drawTerrainReticle()
                        ct.drawToolReticle()
                    else:
                        self.editor.drawWireCubeReticle()

            for t in self.editor.toolbar.tools:
                t.drawTerrainMarkers()
                t.drawToolMarkers()

        if self.drawFog:
            self.disableFog()

        if self.compassToggle:
            if self._compass is None:
                self._compass = CompassOverlay()

            x = getattr(getattr(self.editor, 'copyPanel', None), 'width', 0)
            if x:
                x = x /float( self.editor.mainViewport.width)
            self._compass.x = x
            self._compass.yawPitch = self.yaw, 0

            with gl.glPushMatrix(GL.GL_PROJECTION):
                GL.glLoadIdentity()
                GL.glOrtho(0., 1., float(self.height) / self.width, 0, -200, 200)

                self._compass.draw()
        else:
            self._compass = None

    _compass = None
    
class BlockInfoParser(object):
    last_level = None
    nbt_ending = "\n\nPress ALT for NBT"
    edit_ending = ", Double-Click to Edit"
    
    @classmethod
    def get_parsers(cls, editor):
        cls.last_level = editor.level
        parser_map = {}
        for subcls in cls.__subclasses__():
            instance = subcls(editor.level)
            try:
                blocks = instance.getBlocks()
            except KeyError:
                continue
            if isinstance(blocks, (str, int)):
                parser_map[blocks] = instance.parse_info
            elif isinstance(blocks, (list, tuple)):
                for block in blocks:
                    parser_map[block] = instance.parse_info
        return parser_map
    
    def getBlocks(self):
        raise NotImplementedError()
    
    def parse_info(self, pos):
        raise NotImplementedError()

class SpawnerInfoParser(BlockInfoParser):
    
    def __init__(self, level):
        self.level = level
        
    def getBlocks(self):
        return self.level.materials["minecraft:mob_spawner"].ID
    
    def parse_info(self, pos):
        tile_entity = self.level.tileEntityAt(*pos)
        if tile_entity:
            spawn_data = tile_entity.get("SpawnData", {})
            if spawn_data:
                id = spawn_data.get('EntityId', None)
                if not id:
                    id = spawn_data.get('id', None)
                if not id:
                    value = repr(NameError("Malformed spawn data: could not find 'EntityId' or 'id' tag."))
                else:
                    value = id.value
                return str(value) + " Spawner" + self.nbt_ending + self.edit_ending
        return "[Empty]"  + self.nbt_ending + self.edit_ending
    
class JukeboxInfoParser(BlockInfoParser):
    id_records = {
               2256: "13",
               2257: "Cat",
               2258: "Blocks",
               2259: "Chirp",
               2260: "Far",
               2261: "Mall",
               2262: "Mellohi",
               2263: "Stal",
               2264: "Strad",
               2265: "Ward",
               2266: "11",
               2267: "Wait"
    }
    
    name_records = {
                "minecraft:record_13": "13",
                "minecraft:record_cat": "Cat",
                "minecraft:record_blocks": "Blocks",
                "minecraft:record_chirp": "Chirp",
                "minecraft:record_far": "Far",
                "minecraft:record_mall": "Mall",
                "minecraft:record_mellohi": "Mellohi",
                "minecraft:record_stal": "Stal",
                "minecraft:record_strad": "Strad",
                "minecraft:record_ward": "Ward",
                "minecraft:record_11": "11",
                "minecraft:record_wait": "Wait"
    }
    
    def __init__(self, level):
        self.level = level
        
    def getBlocks(self):
        return self.level.materials["minecraft:jukebox"].ID
    
    def parse_info(self, pos):
        tile_entity = self.level.tileEntityAt(*pos)
        if tile_entity:
            if "Record" in tile_entity:
                value = tile_entity["Record"].value
                if value in self.id_records:
                    return self.id_records[value] + " Record" + self.nbt_ending + self.edit_ending
            elif "RecordItem" in tile_entity:
                value = tile_entity["RecordItem"]["id"].value
                if value in self.name_records:
                    return self.name_records[value] + " Record" + self.nbt_ending + self.edit_ending
        return "[No Record]"  + self.nbt_ending + self.edit_ending
    
class CommandBlockInfoParser(BlockInfoParser):
    
    def __init__(self, level):
        self.level = level
        
    def getBlocks(self):
        return [
                self.level.materials["minecraft:command_block"].ID,
                self.level.materials["minecraft:repeating_command_block"].ID,
                self.level.materials["minecraft:chain_command_block"].ID
                ]
    
    def parse_info(self, pos):
        tile_entity = self.level.tileEntityAt(*pos)
        if tile_entity:
            value = tile_entity.get("Command", TAG_String("")).value
            if value:
                if len(value) > 1500:
                    return value[:1500] + "\n**COMMAND IS TOO LONG TO SHOW MORE**" + self.nbt_ending + self.edit_ending
                return value + self.nbt_ending + self.edit_ending
        return "[Empty Command Block]"  + self.nbt_ending + self.edit_ending
    
class ContainerInfoParser(BlockInfoParser):
    
    def __init__(self, level):
        self.level = level
        
    def getBlocks(self):
        return [
                self.level.materials["minecraft:dispenser"].ID,
                self.level.materials["minecraft:chest"].ID,
                self.level.materials["minecraft:furnace"].ID,
                self.level.materials["minecraft:lit_furnace"].ID,
                self.level.materials["minecraft:trapped_chest"].ID,
                self.level.materials["minecraft:hopper"].ID,
                self.level.materials["minecraft:dropper"].ID,
                self.level.materials["minecraft:brewing_stand"].ID
                ]
        
    def parse_info(self, pos):
        tile_entity = self.level.tileEntityAt(*pos)
        if tile_entity:
            return "Contains {} Items".format(len(tile_entity.get("Items", []))) + self.nbt_ending + self.edit_ending
        return "[Empty Container]" + self.nbt_ending + self.edit_ending

def unproject(x, y, z):
    try:
        return GLU.gluUnProject(x, y, z)
    except ValueError:  # projection failed
        return 0, 0, 0
