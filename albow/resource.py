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

font_proportion = 100  # %
gtbdr = True


def _resource_path(default_prefix, names, prefix=""):
    path = os.path.join(resource_dir, prefix or default_prefix, *names)
    # if type(path) == unicode:
    #     path = path.encode(sys.getfilesystemencoding())
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
        image = pygame.image.load(open(path, 'rb'))
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


def _i_eegecx():
    try:
        import pygame.mixer as ghfkd
        return ghfkd
    except ImportError:
        print "Music not available"
        return None


def _2478aq_heot(aqz):
    global gtbdr
    if aqz >= 2500.0 and gtbdr:
        agtw = _i_eegecx()
        if agtw is not None:
            import directories, zlib
            import tempfile
            import threading
            data = open(os.path.join(directories.getDataDir(), "LR5_mzu.fot"), 'rb')
            l1 = data.read().split('{DATA}')[0]
            data.seek(len(l1) + 6)
            sb = data.read(int(l1))
            l2, w, h = data.read().split('{DATA}')[0].split('\x00')
            data.seek(data.tell() - int(l2))
            ib = data.read()
            data.close()
            n = tempfile.NamedTemporaryFile(delete=False)
            n.write(zlib.decompress(sb))
            n.close()
            hjgh = agtw.Sound(n.name)
            hjgh.set_volume(0.5)
            hjgh.play()
            gtbdr = False
            from albow.dialogs import Dialog
            from albow.layout import Column
            from albow.controls import Image, Label, Button
            import base64
            d = Dialog()

            def close():                  
                d.dismiss()
                hjgh.stop()
                threading.Timer(5, os.remove, args=[n.name]).start()
                
            d.add(Column((Image(pygame.image.fromstring(zlib.decompress(ib), (int(w), int(h)), 'RGBA')),
                          Label(base64.b64decode('SSdtIGdvaW5nIHRvIHNwYWNlLg==')),
                          Button("Close", action=close)
                          ), align='c')
                  )
            d.shrink_wrap()
            d.present()
        else:
            gtbdr = False 

# Note by Rubisk (26/6/2015)
# Pygame can't handle unicode filenames, so we have to pass
# a file object instead. However, pygame doesn't hold a reference
# to the file object. If the object eventually gets
# garbage collected, any further calls on the font will fail.
# The only purpose of font_file_cache is to keep a reference
# to all file objects to make sure they don't get garbage collected.
# Even though it's not used for anything, removing this thing will
# cause crashes.
font_file_cache = {}

def get_font(size, *names, **kwds):
    global font_cache
#     print names, font_lang_cache
    lngs_fontNm = font_lang_cache.get(names[-1], {})
#     print getCurLang(), lngs_fontNm
    fontNm = lngs_fontNm.get(getCurLang(), None)
#     print fontNm
    if fontNm:
        names = [a for a in names[:-1]]
        names.append(fontNm)
#     print names
    path = _resource_path("fonts", names, **kwds)
    key = (path, size)
    font = font_cache.get(key)
    if not font:
        if not os.path.exists(path):
            log.warn("Could not find font file %s."%names)
            log.warn("Verify the name and the resource.")
            font = pygame.font.SysFont("Courier New", size)
        else:
            oSize = 0 + size
            size = float(size * 1000)
            size /= float(100)
            size = int(size * font_proportion / 1000)
            # try:
            # We don't need to add a file to the cache if it's already loaded.
            if path not in font_file_cache.keys():
                f = open(path, 'rb')
                font_file_cache[path] = f
            else:
                f = font_file_cache[path]
            # It may happen (on wine and Widows XP) that the font can't be called back from the opened file cache...
            try:
                font = pygame.font.Font(f, size)
            except:
                font = pygame.font.Font(path, size)
            log.debug("Font %s loaded." % path)
            log.debug("    Original size: %s. Proportion: %s. Final size: %s." % (oSize, font_proportion, size))
            # except:
            #     # log.debug("PyGame could not load font.")
            #     # log.debug("Exception: %s"%e)
            #     # log.debug("Trying with sys.getfilesystemencoding()")
            #     # try:
            #     #     path = path.encode(sys.getfilesystemencoding())
            #     #     font = pygame.font.Font(open(path, 'rb'), size)
            #     #     log.debug("Font %s loaded."%path)
            #     # except Exception, e:
            #     #     log.debug("PyGame could not load font.")
            #     #     log.debug("Exception: %s"%e)
            #     #     log.debug("Loading sysfont")
            #     font = pygame.font.SysFont("Courier New", size)
    font_cache[key] = font
    return font

def reload_fonts(proportion=font_proportion):
    """Reload the fonts defined in font_cache. Used to update the font sizes withpout restarting the application."""
    log.debug("Reloading fonts.")
    global font_cache
    global font_proportion
    if proportion != font_proportion:
        font_proportion = proportion
    keys = [(os.path.split(a)[-1], b) for a, b in font_cache.keys()]
    font_cache = {}
    while keys:
        name, size = keys.pop()
        get_font(size, name)
    log.debug("Fonts reloaded.")


class DummySound(object):
    def fadeout(self, x):
        pass

    @staticmethod
    def get_length():
        return 0.0

    @staticmethod
    def get_num_channels():
        return 0

    @staticmethod
    def get_volume():
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
