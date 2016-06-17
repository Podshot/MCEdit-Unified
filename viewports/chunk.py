from camera import CameraViewport
from OpenGL import GL
import mceutils


class ChunkViewport(CameraViewport):
    defaultScale = 1.0  # pixels per block

    def __init__(self, *a, **kw):
        CameraViewport.__init__(self, *a, **kw)

    def setup_projection(self):
        w, h = (0.5 * s / self.defaultScale
                for s in self.size)

        minx, maxx = - w, w
        miny, maxy = - h, h
        minz, maxz = -4000, 4000
        GL.glOrtho(minx, maxx, miny, maxy, minz, maxz)

    def setup_modelview(self):
        x, y, z = self.cameraPosition

        GL.glRotate(90.0, 1.0, 0.0, 0.0)
        GL.glTranslate(-x, 0, -z)

    def zoom(self, f):
        x, y, z = self.cameraPosition
        if self.blockFaceUnderCursor[0] is None:
            return
        mx, my, mz = self.blockFaceUnderCursor[0]
        dx, dz = mx - x, mz - z
        s = min(4.0, max(1 / 16., self.defaultScale / f))
        if s != self.defaultScale:
            self.defaultScale = s
            f = 1.0 - f

            self.cameraPosition = x + dx * f, self.editor.level.Height, z + dz * f
            self.editor.renderer.loadNearbyChunks()

    incrementFactor = 1.4

    def zoomIn(self):
        self.zoom(1.0 / self.incrementFactor)

    def zoomOut(self):
        self.zoom(self.incrementFactor)

    def mouse_down(self, evt):
        if evt.button == 4:  # wheel up - zoom in
            # if self.defaultScale == 4.0:
            #                self.editor.swapViewports()
            #            else:
            self.zoomIn()
        elif evt.button == 5:  # wheel down - zoom out
            self.zoomOut()
        else:
            super(ChunkViewport, self).mouse_down(evt)

    def rightClickDown(self, evt):
        pass

    def rightClickUp(self, evt):
        pass

    def mouse_move(self, evt):
        pass

    @mceutils.alertException
    def mouse_drag(self, evt):

        if evt.buttons[2]:
            x, y, z = self.cameraPosition
            dx, dz = evt.rel
            self.cameraPosition = (
                x - dx / self.defaultScale,
                y,
                z - dz / self.defaultScale)
        else:
            super(ChunkViewport, self).mouse_drag(evt)

    def render(self):
        super(ChunkViewport, self).render()

    @property
    def tooltipText(self):
        text = super(ChunkViewport, self).tooltipText
        if text == "1 W x 1 L x 1 H":
            return None
        return text

    def drawCeiling(self):
        pass
