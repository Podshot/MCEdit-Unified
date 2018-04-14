#! /usr/bin/env python
# Taken from http://www.pygame.org/project-Splash+screen-1186-.html by Rock Achu (rockhachu2)
# and tweaked ;)
import os
import directories
if os.sys.platform == 'linux2':
    os.sys.path.insert(1, os.path.expanduser('~/.local/lib/python2.7/site-packages'))
    os.sys.path.insert(1, os.path.abspath('./lib'))

import pygame
print 'Splash load...'
os.environ['SDL_VIDEO_CENTERED'] = '1'

pygame.init()
pygame.font.init()
no_splash = False
#cur_dir = directories.getDataDir()
#splash_name = os.path.join(cur_dir, 'splash')
splash_name = directories.getDataFile('splash')
splash = None
splash_img_fp = None
fp = None

try:
    found = False
    if os.path.exists(splash_name):
        splash_img_fp = open(splash_name)
        splash_img = splash_img_fp.read().strip()
        if os.path.exists(splash_img) and splash_img.split('.')[-1].lower() in ('jpg', 'png', 'bmp', 'pcx', 'tif', 'lbm', 'pbm', 'pgm', 'ppm', 'xpm'):
            found = True
            fp = open(splash_img, 'rb')
            splash = pygame.image.load(fp)
    if not found:
        #fp = open(os.path.join(cur_dir, "splash.png"), 'rb')
        fp = open(directories.getDataFile('splash.png'), 'rb')
        splash = pygame.image.load(fp)
    screen = pygame.display.set_mode(splash.get_size(), pygame.NOFRAME)
    screen.blit(splash, (0, 0))
except Exception as e:
    print e
    try:
        #fp = open(os.path.join(cur_dir, 'fonts', 'DejaVuSans-Bold.ttf'), 'rb')
        fp = open(directories.getDataFile('fonts', 'DejaVuSans-Bold.ttf'), 'rb')
        font = pygame.font.Font(fp, 48)
        buf = font.render("MCEdit is loading...", True, (128, 128, 128))
        screen = pygame.display.set_mode((buf.get_width() + 20, buf.get_height() + 20), pygame.NOFRAME)
        screen.blit(buf, (10, 10))
        splash = pygame.display.get_surface()
    except Exception as _e:
        print _e
        splash = pygame.display.set_mode((1, 1))
    no_splash = True
finally:
    if fp:
        fp.close()
    if splash_img_fp:
        splash_img_fp.close()
if splash:
    pygame.display.update()
#os.environ['SDL_VIDEO_CENTERED'] = '0' # Done later, when initializing MCEdit 'real' display.

# Random splash
#
# Uses a 'splash' file to check the state.
# This file contains the name of the splash to be loaded next time MCEdit starts.
# No splash file means it has to be created.
# An empty file means the 'splash.png' file will always be used.
#

write_splash = True

if not os.path.exists(splash_name):
    splash_fp = None
    try:
        splash_fp = open(splash_name, 'w')
        splash_fp.write('scrap')
    except Exception as e:
        write_splash = False
        print "Could not create 'splash' file:", e
    finally:
        if splash_fp:
            splash_fp.close()

if write_splash:
    f = open(splash_name)
    if len(f.read()) > 0:
        from random import choice
        #splashes_folder = os.path.join(cur_dir, 'splashes')
        splashes_folder = directories.getDataFile('splashes')
        if not os.path.exists(splashes_folder):
            #splashes_folder = os.path.join(cur_dir, splashes_folder)
            splashes_folder = directories.getDataFile(splashes_folder)
        if os.path.exists(splashes_folder) and os.listdir(splashes_folder):
            new_splash = choice(os.listdir(splashes_folder))
            if new_splash.split('.')[-1].lower() in ('jpg', 'png', 'bmp', 'pcx', 'tif', 'lbm', 'pbm', 'pgm', 'ppm', 'xpm'):
                f2 = open(splash_name, 'w')
                try:
                    #f2.write(os.path.join(cur_dir, splashes_folder, new_splash))
                    f2.write(directories.getDataFile(splashes_folder, new_splash))
                except Exception as e:
                    print "Could not write 'splash' file:", e
                finally:
                    if f2:
                        f2.close()
    f.close()
