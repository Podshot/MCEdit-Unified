from OpenGL import GL, GLU
from config import config
import pygame
from pygame import display, image
import logging
import release
import sys
import directories
import os
import mcplatform
import numpy
import pymclevel
import resource_packs
import glutils
import mceutils
import functools


class GLDisplayContext(object):
    def __init__(self, splash=None):
        self.reset(splash)

    def getWindowSize(self):
        w, h = (config.settings.windowWidth.get(), config.settings.windowHeight.get())
        return max(20, w), max(20, h)

    def displayMode(self):
        return pygame.OPENGL | pygame.RESIZABLE | pygame.DOUBLEBUF

    def reset(self, splash=None):
        pygame.key.set_repeat(500, 100)

        try:
            display.gl_set_attribute(pygame.GL_SWAP_CONTROL, config.settings.vsync.get())
        except Exception, e:
            logging.warning('Unable to set vertical sync: {0!r}'.format(e))

        display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)

        wwh = self.getWindowSize()
        d = display.set_mode(wwh, self.displayMode())

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glAlphaFunc(GL.GL_NOTEQUAL, 0)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # textures are 256x256, so with this we can specify pixel coordinates
        GL.glMatrixMode(GL.GL_TEXTURE)
        GL.glScale(1 / 256., 1 / 256., 1 / 256.)

        if splash:
            swh = splash.get_size()
            x, y = (wwh[0] / 2 - swh[0] / 2, wwh[1] / 2 - swh[1] / 2)
            w, h = swh
            data = image.tostring(splash, 'RGBA', 1)
            GL.glWindowPos2d(x, y)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glDrawPixels(w, h,
                            GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, numpy.fromstring(data, dtype='uint8'))
            display.flip()

        display.set_caption('MCEdit ~ ' + release.get_version(), 'MCEdit')
        if sys.platform == 'win32' and config.settings.setWindowPlacement.get():
            config.settings.setWindowPlacement.set(False)
            config.save()
            X, Y = config.settings.windowX.get(), config.settings.windowY.get()

            if X:
                w, h = self.getWindowSize()
                hwndOwner = display.get_wm_info()['window']

                flags, showCmd, ptMin, ptMax, rect = mcplatform.win32gui.GetWindowPlacement(hwndOwner)
                realW = rect[2] - rect[0]
                realH = rect[3] - rect[1]

                showCmd = config.settings.windowShowCmd.get()
                rect = (X, Y, X + realW, Y + realH)

                mcplatform.win32gui.SetWindowPlacement(hwndOwner, (0, showCmd, ptMin, ptMax, rect))

            config.settings.setWindowPlacement.set(True)
            config.save()
        elif sys.platform == 'linux2' and mcplatform.hasXlibDisplay:
            dis = mcplatform.Xlib.display.Display()
            root = dis.screen().root
            windowIDs = root.get_full_property(dis.intern_atom('_NET_CLIENT_LIST'), mcplatform.Xlib.X.AnyPropertyType).value
            for windowID in windowIDs:
                window = dis.create_resource_object('window', windowID)
                name = window.get_wm_name()
                if "MCEdit ~ Unified" in name:
                    win = window
            win.configure(x=config.settings.windowX.get(), y=config.settings.windowY.get())
            self.win = win
            dis.sync()

        try:
            iconpath = os.path.join(directories.getDataDir(), 'favicon.png')
            iconfile = file(iconpath, 'rb')
            icon = pygame.image.load(iconfile, 'favicon.png')
            display.set_icon(icon)
        except Exception, e:
            logging.warning('Unable to set icon: {0!r}'.format(e))

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
            (pymclevel.alphaMaterials, resource_packs.packs.get_selected_resource_pack().terrain_path()),
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
