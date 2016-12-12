from OpenGL import GL, GLU
from config import config
import pygame
from pygame import display, image, Surface
import logging
import release
import sys
import directories
import os
import mcplatform
import numpy
import pymclevel
from resource_packs import ResourcePackHandler
import glutils
import mceutils
import functools

DEBUG_WM = mcplatform.DEBUG_WM
USE_WM = mcplatform.USE_WM


class GLDisplayContext(object):
    def __init__(self, splash=None, caption=("", "")):
        self.win = None
        self.reset(splash, caption=caption)

    @staticmethod
    def getWindowSize():
        w, h = (config.settings.windowWidth.get(), config.settings.windowHeight.get())
        return max(20, w), max(20, h)

    @staticmethod
    def displayMode():
        return pygame.OPENGL | pygame.RESIZABLE | pygame.DOUBLEBUF

    def reset(self, splash=None, caption=("", "")):
        pygame.key.set_repeat(500, 100)

        try:
            display.gl_set_attribute(pygame.GL_SWAP_CONTROL, config.settings.vsync.get())
        except Exception, e:
            logging.warning('Unable to set vertical sync: {0!r}'.format(e))

        display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)

        if DEBUG_WM:
            print "config.settings.windowMaximized.get()", config.settings.windowMaximized.get()
        wwh = self.getWindowSize()
        if DEBUG_WM:
            print "wwh 1", wwh
        d = display.set_mode(wwh, self.displayMode())

        # Let initialize OpenGL stuff after the splash.
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glAlphaFunc(GL.GL_NOTEQUAL, 0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
 
        # textures are 256x256, so with this we can specify pixel coordinates
#        GL.glMatrixMode(GL.GL_TEXTURE)
#        GL.glScale(1 / 256., 1 / 256., 1 / 256.)

        display.set_caption(*caption)

        if mcplatform.WindowHandler:
            self.win = mcplatform.WindowHandler(mode=self.displayMode())

        # The following Windows specific code won't be executed if we're using '--debug-wm' switch.
        if not USE_WM and sys.platform == 'win32' and config.settings.setWindowPlacement.get():
            config.settings.setWindowPlacement.set(False)
            config.save()
            X, Y = config.settings.windowX.get(), config.settings.windowY.get()

            if X:
                hwndOwner = display.get_wm_info()['window']

                flags, showCmd, ptMin, ptMax, rect = mcplatform.win32gui.GetWindowPlacement(hwndOwner)
                realW = rect[2] - rect[0]
                realH = rect[3] - rect[1]

                showCmd = config.settings.windowShowCmd.get()
                rect = (X, Y, X + realW, Y + realH)

                mcplatform.win32gui.SetWindowPlacement(hwndOwner, (0, showCmd, ptMin, ptMax, rect))

            config.settings.setWindowPlacement.set(True)
            config.save()
        elif self.win:
            maximized = config.settings.windowMaximized.get()
            if DEBUG_WM:
                print "maximized", maximized
            if maximized:
                geom = self.win.get_root_rect()
                in_w, in_h = self.win.get_size()
                x, y = int((geom[2] - in_w) / 2), int((geom[3] - in_h) / 2)
                os.environ['SDL_VIDEO_CENTERED'] = '1'
            else:
                os.environ['SDL_VIDEO_CENTERED'] = '0'
                x, y = config.settings.windowX.get(), config.settings.windowY.get()
                wwh = self.win.get_size()
            if DEBUG_WM:
                print "x", x, "y", y
                print "wwh 2", wwh

        if splash:
            # Setup the OGL display
            GL.glLoadIdentity()
            GLU.gluOrtho2D(0, wwh[0], 0, wwh[1])
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT | GL.GL_ACCUM_BUFFER_BIT | GL.GL_STENCIL_BUFFER_BIT)

            swh = splash.get_size()
            _x, _y = (wwh[0] / 2 - swh[0] / 2, wwh[1] / 2 - swh[1] / 2)
            w, h = swh

            try:
                data = image.tostring(splash, 'RGBA_PREMULT', 1)
            except ValueError:
                data = image.tostring(splash, 'RGBA', 1)
            except ValueError:
                data = image.tostring(splash, 'RGB', 1)

            # Set the raster position
            GL.glRasterPos(_x, _y)

            GL.glDrawPixels(w, h,
                            GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, numpy.fromstring(data, dtype='uint8'))

        if splash:
            display.flip()

        if self.win:
            if not maximized:
                wwh = self.getWindowSize()
            if DEBUG_WM:
                print "wwh 3", wwh
            self.win.set_position((x, y), update=True)
            if DEBUG_WM:
                print "* self.win.get_position()", self.win.get_position()

        try:
            iconpath = os.path.join(directories.getDataDir(), 'favicon.png')
            iconfile = file(iconpath, 'rb')
            icon = pygame.image.load(iconfile, 'favicon.png')
            display.set_icon(icon)
        except Exception, e:
            logging.warning('Unable to set icon: {0!r}'.format(e))

        # Let initialize OpenGL stuff after the splash.
#         GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
#         GL.glAlphaFunc(GL.GL_NOTEQUAL, 0)
#         GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
 
        # textures are 256x256, so with this we can specify pixel coordinates
        GL.glMatrixMode(GL.GL_TEXTURE)
        GL.glScale(1 / 256., 1 / 256., 1 / 256.)

        self.display = d

        self.loadTextures()

    def getTerrainTexture(self, level):
        return self.terrainTextures.get(level.materials.name, self.terrainTextures["Alpha"])

    def loadTextures(self):
        self.terrainTextures = {}

        def makeTerrainTexture(mats):
            w, h = 1, 1
            teximage = numpy.zeros((w, h, 4), dtype='uint8')
            teximage[:] = 127, 127, 127, 255

            GL.glTexImage2D(
                GL.GL_TEXTURE_2D,
                0,
                GL.GL_RGBA8,
                w,
                h,
                0,
                GL.GL_RGBA,
                GL.GL_UNSIGNED_BYTE,
                teximage
            )

        textures = (
            (pymclevel.classicMaterials, 'terrain-classic.png'),
            (pymclevel.indevMaterials, 'terrain-classic.png'),
            (pymclevel.alphaMaterials, ResourcePackHandler.Instance().get_selected_resource_pack().terrain_path()),
            (pymclevel.pocketMaterials, 'terrain-pocket.png')
        )

        for mats, matFile in textures:
            try:
                if mats.name == 'Alpha':
                    tex = mceutils.loadAlphaTerrainTexture()
                else:
                    tex = mceutils.loadPNGTexture(matFile)
                self.terrainTextures[mats.name] = tex
            except Exception, e:
                logging.warning(
                    'Unable to load terrain from {0}, using flat colors.'
                    'Error was: {1!r}'.format(matFile, e)
                )
                self.terrainTextures[mats.name] = glutils.Texture(
                    functools.partial(makeTerrainTexture, mats)
                )
            mats.terrainTexture = self.terrainTextures[mats.name]

