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
cur_dir = directories.getDataDir()
splash_name = os.path.join(cur_dir, 'splash')
splash = None

try:
    found = False
    if os.path.exists(splash_name):
        splash_img = open(splash_name).read().strip()
        if os.path.exists(splash_img) and splash_img.split('.')[-1].lower() in ('jpg', 'png', 'bmp', 'pcx', 'tif', 'lbm', 'pbm', 'pgm', 'ppm', 'xpm'):
            found = True
            splash = pygame.image.load(open(splash_img, 'rb'))
    if not found:
        splash = pygame.image.load(open(os.path.join(cur_dir, "splash.png"), 'rb'))
    screen = pygame.display.set_mode(splash.get_size(), pygame.NOFRAME)
    screen.blit(splash, (0, 0))
except Exception, e:
    print e
    try:
        f = open(os.path.join(cur_dir, 'fonts', 'DejaVuSans-Bold.ttf'), 'rb')
        font = pygame.font.Font(f, 48)
        buf = font.render("MCEDit is loading...", True, (128, 128, 128))
        screen = pygame.display.set_mode((buf.get_width() + 20, buf.get_height() + 20), pygame.NOFRAME)
        screen.blit(buf, (10, 10))
        splash = pygame.display.get_surface()
    except Exception, _e:
        print _e
        splash = pygame.display.set_mode((1, 1))
    no_splash = True
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
    try:
        open(splash_name, 'w').write('scrap')
    except Exception, e:
        write_splash = False
        print "Could not create 'splash' file:", e

if write_splash:
    if len(open(splash_name).read()) > 0:
        from random import choice
        splashes_folder = os.path.join(cur_dir, 'splashes')
        if not os.path.exists(splashes_folder):
            splashes_folder = os.path.join(cur_dir, splashes_folder)
        if os.path.exists(splashes_folder) and os.listdir(splashes_folder):
            new_splash = choice(os.listdir(splashes_folder))
            if new_splash.split('.')[-1].lower() in ('jpg', 'png', 'bmp', 'pcx', 'tif', 'lbm', 'pbm', 'pgm', 'ppm', 'xpm'):
                try:
                    open(splash_name, 'w').write(os.path.join(cur_dir, splashes_folder, new_splash))
                except Exception, e:
                    print "Could not write 'splash' file:", e
