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

from math import isnan
from datetime import datetime, timedelta

from OpenGL import GL
from OpenGL import GLU

from albow import alert, AttrRef, Button, Column, input_text, Row, TableColumn, TableView, TextField, Widget, CheckBox
from albow.controls import Label, ValueDisplay
from albow.dialogs import Dialog, wrapped_label
from albow.openglwidgets import GLViewport
from albow.translate import _
from pygame import mouse

from depths import DepthOffset
from editortools.operation import Operation
from glutils import gl


class CameraViewport(GLViewport):
    anchor = "tlbr"

    oldMousePosition = None

    def __init__(self, editor):
        self.editor = editor
        rect = editor.mcedit.rect
        GLViewport.__init__(self, rect)

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
        #   1 = app just started or regained focus since last bad event
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

        config.settings.fov.addObserver(self, "fovSetting", callback=self.updateFov)

        self.mouseVector = (0, 0, 0)

        self.root = self.get_root()
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

        if inSpace:
            accel_factor *= 3.0
            max_speed *= 3.0

        pi = self.editor.cameraPanKeys
        mouseSpeed = config.controls.mouseSpeed.get()
        self.yaw += pi[0] * mouseSpeed
        self.pitch += pi[1] * mouseSpeed

        if self.flyMode:
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
                speed = 0.15 * speed
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
        look += self.cameraVector
        up = (0, 1, 0)
        GLU.gluLookAt(pos[0], pos[1], pos[2],
                      look[0], look[1], look[2],
                      up[0], up[1], up[2])

    def _cameraVector(self):
        return self._anglesToVector(self.yaw, self.pitch)

    def _anglesToVector(self, yaw, pitch):
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
                        focusPair = raycaster.firstBlock(self.cameraPosition, self._mouseVector(), self.editor.level, 100, config.settings.viewMode.get())
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

    mobs = pymclevel.Entity.monsters + ["[Custom]"]

    @mceutils.alertException
    def editMonsterSpawner(self, point):
        mobs = self.mobs

        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String("MobSpawner")
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["Delay"] = pymclevel.TAG_Short(120)
            tileEntity["EntityId"] = pymclevel.TAG_String(mobs[0])

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
            return mobs[mobTable.selectedIndex]

        id = tileEntity["EntityId"].value
        addMob(id)

        mobTable.selectedIndex = mobs.index(id)

        choiceCol = Column((ValueDisplay(width=200, get_value=lambda: selectedMob() + " spawner"), mobTable))

        okButton = Button("OK", action=panel.dismiss)
        panel.add(Column((choiceCol, okButton)))
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
            tileEntity["EntityId"] = pymclevel.TAG_String(selectedMob())
            op = MonsterSpawnerEditOperation(self.editor, self.editor.level)
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @mceutils.alertException
    def editSign(self, point):

        block = self.editor.level.blockAt(*point)
        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        linekeys = ["Text" + str(i) for i in range(1, 5)]

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String("Sign")
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            for l in linekeys:
                tileEntity[l] = pymclevel.TAG_String("")

        self.editor.level.addTileEntity(tileEntity)

        panel = Dialog()

        lineFields = [TextField(width=400) for l in linekeys]
        for l, f in zip(linekeys, lineFields):
            f.value = tileEntity[l].value

        colors = [
            "\xa70  Black",
            "\xa71  Dark Blue",
            "\xa72  Dark Green",
            "\xa73  Dark Aqua",
            "\xa74  Dark Red",
            "\xa75  Dark Purple",
            "\xa76  Gold",
            "\xa77  Gray",
            "\xa78  Dark Gray",
            "\xa79  Blue",
            "\xa7a  Green",
            "\xa7b  Aqua",
            "\xa7c  Red",
            "\xa7d  Light Purple",
            "\xa7e  Yellow",
            "\xa7f  White",
        ]

        def menu_picked(index):
            c = u'\xa7' + hex(index)[-1]
            currentField = panel.focus_switch.focus_switch
            currentField.text += c  # xxx view hierarchy
            currentField.insertion_point = len(currentField.text)

        class SignEditOperation(Operation):
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

        def changeSign():
            unsavedChanges = False
            for l, f in zip(linekeys, lineFields):
                oldText = "{}".format(tileEntity[l])
                tileEntity[l] = pymclevel.TAG_String(f.value[:255])
                if "{}".format(tileEntity[l]) != oldText and not unsavedChanges:
                    unsavedChanges = True
            if unsavedChanges:
                op = SignEditOperation(self.editor, self.editor.level)
                self.editor.addOperation(op)
                if op.canUndo:
                    self.editor.addUnsavedEdit()
            panel.dismiss()

        colorMenu = mceutils.MenuButton("Add Color Code...", colors, menu_picked=menu_picked)

        column = [Label("Edit Sign")] + lineFields + [colorMenu, Button("OK", action=changeSign)]

        panel.add(Column(column))
        panel.shrink_wrap()
        panel.present()

    @mceutils.alertException
    def editSkull(self, point):
        block = self.editor.level.blockAt(*point)
        blockData = self.editor.level.blockDataAt(*point)
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
            tileEntity["id"] = pymclevel.TAG_String("Skull")
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["SkullType"] = pymclevel.TAG_Byte(3)
            self.editor.level.addTileEntity(tileEntity)

        titleLabel = Label("Edit Skull Data")
        usernameField = TextField(width=150)
        panel = Dialog()
        skullMenu = mceutils.ChoiceButton(map(str, skullTypes))

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
        block = self.editor.level.blockAt(*point)
        blockData = self.editor.level.blockDataAt(*point)
        tileEntity = self.editor.level.tileEntityAt(*point)
        undoBackupEntityTag = copy.deepcopy(tileEntity)

        if not tileEntity:
            tileEntity = pymclevel.TAG_Compound()
            tileEntity["id"] = pymclevel.TAG_String("Control")
            tileEntity["x"] = pymclevel.TAG_Int(point[0])
            tileEntity["y"] = pymclevel.TAG_Int(point[1])
            tileEntity["z"] = pymclevel.TAG_Int(point[2])
            tileEntity["Command"] = pymclevel.TAG_String()
            tileEntity["CustomName"] = pymclevel.TAG_String("@")
            tileEntity["TrackOutput"] = pymclevel.TAG_Byte(0)
            self.editor.level.addTileEntity(tileEntity)

        titleLabel = Label("Edit Command Block")
        commandField = TextField(width=500)
        nameField = TextField(width=100)
        trackOutput = CheckBox()

        commandField.value = tileEntity["Command"].value
        oldCommand = commandField.value
        trackOutput.value = tileEntity["TrackOutput"].value
        oldTrackOutput = trackOutput.value
        nameField.value = tileEntity["CustomName"].value
        oldNameField = nameField.value

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
            if oldCommand != commandField.value or oldTrackOutput != trackOutput.value or oldNameField != nameField.value:
                tileEntity["Command"] = pymclevel.TAG_String(commandField.value)
                tileEntity["TrackOutput"] = pymclevel.TAG_Byte(trackOutput.value)
                tileEntity["CustomName"] = pymclevel.TAG_String(nameField.value)

                op = CommandBlockEditOperation(self.editor, self.editor.level)
                self.editor.addOperation(op)
                if op.canUndo:
                    self.editor.addUnsavedEdit()

            chunk = self.editor.level.getChunk(int(int(point[0]) / 16), int(int(point[2]) / 16))
            chunk.dirty = True
            panel.dismiss()

        okBTN = Button("OK", action=updateCommandBlock)
        cancel = Button("Cancel", action=panel.dismiss)
        column = [titleLabel, Label("Command:"), commandField, Row((Label("Custom Name:"), nameField)), Row((Label("Track Output"), trackOutput)), okBTN, cancel]
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

        chestItemTable.num_rows = lambda: len(tileEntityTag["Items"])
        chestItemTable.row_data = getRowData
        chestItemTable.row_is_selected = lambda x: x == chestWidget.selectedItemIndex
        chestItemTable.click_row = selectTableRow

        fieldRow = (
            mceutils.IntInputRow("Slot: ", ref=AttrRef(chestWidget, 'Slot'), min=0, max=26),
            mceutils.TextInputRow("ID / ID Name: ", ref=AttrRef(chestWidget, 'id'), width=300),
            # Text to allow the input of internal item names
            mceutils.IntInputRow("DMG: ", ref=AttrRef(chestWidget, 'Damage'), min=-32768, max=32767),
            mceutils.IntInputRow("Count: ", ref=AttrRef(chestWidget, 'Count'), min=-64, max=64),
        )

        def deleteFromWorld():
            i = chestWidget.selectedItemIndex
            item = tileEntityTag["Items"][i]
            id = item["id"].value
            Damage = item["Damage"].value

            deleteSameDamage = mceutils.CheckBoxLabel("Only delete items with the same damage value")
            deleteBlocksToo = mceutils.CheckBoxLabel("Also delete blocks placed in the world")
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
                        l = len(tag["Inventory"])
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

                mceutils.showProgress(progressInfo, deleteItemsIter(), cancel=True)

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

    rightMouseDragStart = None

    def rightClickDown(self, evt):
        self.rightMouseDragStart = datetime.now()
        self.toggleMouseLook()

    def rightClickUp(self, evt):
        x, y = evt.pos
        if self.rightMouseDragStart is None:
            return

        td = datetime.now() - self.rightMouseDragStart
        # except AttributeError:
        # return
        # print "RightClickUp: ", td
        if td.seconds > 0 or td.microseconds > 280000:
            self.mouseLookOff()

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
                                pymclevel.alphaMaterials.CommandBlock.ID: self.editCommandBlock
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
                #    mouse.set_pos(*self.startingMousePosition)
                #    event.get(MOUSEMOTION)
                #    self.oldMousePosition = (self.startingMousePosition)

    def activeevent(self, evt):
        if evt.state & 0x2 and evt.gain != 0:
            self.avoidMouseJumpBug = 1

    @property
    def tooltipText(self):
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

    def _drawCeiling(self):
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

        GL.glFogf(GL.GL_FOG_DENSITY, 0.002)

    def disableFog(self):
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

        if self._compass is None:
            self._compass = CompassOverlay()

        self._compass.yawPitch = self.yaw, 0

        with gl.glPushMatrix(GL.GL_PROJECTION):
            GL.glLoadIdentity()
            GL.glOrtho(0., 1., float(self.height) / self.width, 0, -200, 200)

            self._compass.draw()

    _compass = None


def unproject(x, y, z):
    try:
        return GLU.gluUnProject(x, y, z)
    except ValueError:  # projection failed
        return 0, 0, 0
