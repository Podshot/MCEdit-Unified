# -*- coding: utf-8 -*-
#-# Modified by D.C.-G. for translation purpose
import os
import sys

import logging
log = logging.getLogger(__name__)

import pygame
from pygame.locals import RLEACCEL
from translate import langPath
optimize_images = True
run_length_encode = False


__curLang = "default"

def getCurLang():
    return __curLang

def setCurLang(lang):
    global __curLang
    __curLang = lang

font_lang_cache = {}
resource_dir = "Resources"

image_cache = {}
font_cache = {}
sound_cache = {}
text_cache = {}
cursor_cache = {}

#font_proportion = 100 # %


def _resource_path(default_prefix, names, prefix=""):
    path = os.path.join(resource_dir, prefix or default_prefix, *names)
    if type(path) == unicode:
        path = path.encode(sys.getfilesystemencoding())
    return path


def resource_path(*names, **kwds):
    return _resource_path("", names, **kwds)


def resource_exists(*names, **kwds):
    return os.path.exists(_resource_path("", names, **kwds))


def _get_image(names, border=0, optimize=optimize_images, noalpha=False,
               rle=run_length_encode, prefix="images"):
    path = _resource_path(prefix, names)
    image = image_cache.get(path)
    if not image:
        image = pygame.image.load(path)
        if noalpha:
            image = image.convert(24)
        elif optimize:
            image = image.convert_alpha()
        if rle:
            image.set_alpha(255, RLEACCEL)
        if border:
            w, h = image.get_size()
            b = border
            d = 2 * border
            image = image.subsurface(b, b, w - d, h - d)
        image_cache[path] = image
    return image


def get_image(*names, **kwds):
    return _get_image(names, **kwds)


def get_font(size, *names, **kwds):
    global font_cache
    lngs_fontNm = font_lang_cache.get(names[-1], {})
    fontNm = lngs_fontNm.get(getCurLang(), None)
    if fontNm:
        names = [a for a in names[:-1]]
        names.append(fontNm)
    path = _resource_path("fonts", names, **kwds)
    key = (path, size)
    font = font_cache.get(key)
    if not font:
#        size = float(size * 1000)
#        size = size / float(100)
#        size = int(size * font_proportion / 1000)
        try:
            font = pygame.font.Font(path, size)
            log.debug("Font %s loaded."%path)
        except Exception, e:
            log.debug("PyGame could not load font.")
            log.debug("Exception: %s"%e)
            log.debug("Trying with sys.getfilesystemencoding()")
            try:
                path = path.encode(sys.getfilesystemencoding())
                font = pygame.font.Font(path, size)
                log.debug("Font %s loaded."%path)
            except Exception, e:
                log.debug("PyGame could not load font.")
                log.debug("Exception: %s"%e)
                log.debug("Loading sysfont")
                font = pygame.font.SysFont("Courier New", size)
        font_cache[key] = font
    return font


class DummySound(object):
    def fadeout(self, x):
        pass

    def get_length(self):
        return 0.0

    def get_num_channels(self):
        return 0

    def get_volume(self):
        return 0.0

    def play(self, *args):
        pass

    def set_volume(self, x):
        pass

    def stop(self):
        pass


dummy_sound = DummySound()


def get_sound(*names, **kwds):
    if sound_cache is None:
        return dummy_sound
    path = _resource_path("sounds", names, **kwds)
    sound = sound_cache.get(path)
    if not sound:
        try:
            from pygame.mixer import Sound
        except ImportError, e:
            no_sound(e)
            return dummy_sound
        try:
            sound = Sound(path)
        except pygame.error, e:
            missing_sound(e, path)
            return dummy_sound
        sound_cache[path] = sound
    return sound


def no_sound(e):
    global sound_cache
    print "albow.resource.get_sound: %s" % e
    print "albow.resource.get_sound: Sound not available, continuing without it"
    sound_cache = None


def missing_sound(e, name):
    print "albow.resource.get_sound: %s: %s" % (name, e)


def get_text(*names, **kwds):
    #-# Try at first the 'lang/text' folder
    path = _resource_path(os.path.join(langPath, "text"), names, **kwds)
    if not os.path.exists(path):
        path = _resource_path("text", names, **kwds)
    text = text_cache.get(path)
    if text is None:
        text = open(path, "rU").read()
        text_cache[path] = text
    return text


def load_cursor(path):
    image = get_image(path)
    width, height = image.get_size()
    hot = (0, 0)
    data = []
    mask = []
    rowbytes = (width + 7) // 8
    xr = xrange(width)
    yr = xrange(height)
    for y in yr:
        bit = 0x80
        db = mb = 0
        for x in xr:
            r, g, b, a = image.get_at((x, y))
            if a >= 128:
                mb |= bit
                if r + g + b < 383:
                    db |= bit
            if r == 0 and b == 255:
                hot = (x, y)
            bit >>= 1
            if not bit:
                data.append(db)
                mask.append(mb)
                db = mb = 0
                bit = 0x80
        if bit != 0x80:
            data.append(db)
            mask.append(mb)
    return (8 * rowbytes, height), hot, data, mask


def get_cursor(*names, **kwds):
    path = _resource_path("cursors", names, **kwds)
    cursor = cursor_cache.get(path)
    if cursor is None:
        cursor = load_cursor(path)
        cursor_cache[path] = cursor
    return cursor
