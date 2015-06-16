#! /usr/bin/env python
# Taken from http://www.pygame.org/project-Splash+screen-1186-.html by Rock Achu (rockhachu2)
# and tweaked ;)
import os
if os.sys.platform == 'linux2':
    os.sys.path.insert(1, os.path.expanduser('~/.local/lib/python2.7/site-packages'))
    os.sys.path.insert(1, os.path.abspath('./lib'))
import pygame
print 'Splash load...'
os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
pygame.font.init()
no_splash = False
cur_dir = os.path.dirname(__file__)
print "*** MCEDIT DEBUG: splash.py::__file__:", __file__
if '.app' in cur_dir:
    print "*** MCEDIT DEBUG: Running on MacOS"
    cur_dir = cur_dir.split('.app') + '.app'
    print "*** MCEDIT DEBUG: current directory:", cur_dir
splash_name = os.path.join(cur_dir, 'splash')

try:
    if os.path.exists(splash_name) and len(open(splash_name).read()) > 0:
        splash = pygame.image.load(open(splash_name).read().strip())
    else:
        splash = pygame.image.load(os.path.join(cur_dir, "splash.png"))
    screen = pygame.display.set_mode(splash.get_size(),pygame.NOFRAME)
    screen.blit(splash, (0,0))
except:
    try:
        font = pygame.font.Font(os.path.join(cur_dir, 'fonts', 'DejaVuSans-Bold.ttf'), 48)
        buf = font.render("MCEDit is loading...", True, (128, 128, 128))
        screen = pygame.display.set_mode((buf.get_width() + 20, buf.get_height() + 20), pygame.NOFRAME)
        screen.blit(buf, (10, 10))
        splash = pygame.display.get_surface()
    except:
        splash = pygame.display.set_mode((1, 1))
    no_splash = True
pygame.display.update()
os.environ['SDL_VIDEO_CENTERED'] = '0'

# Random splash
#
# Uses a 'splash' file to check the state.
# This file contains the name of the splash to be loaded next time MCEdit starts.
# No splash file means it has to be created.
# An empty file means the 'splash.png' file will alwas be used.
#

if not os.path.exists(splash_name):
    open(splash_name, 'w').write('scrap')

if len(open(splash_name).read()) > 0:
    from random import choice
    splashes_folder = os.path.join(cur_dir, 'splashes')
    if not os.path.exists(splashes_folder):
        splashes_folder = os.path.join(cur_dir, splashes_folder)
    if os.path.exists(splashes_folder) and os.listdir(splashes_folder):
        new_splash = choice(os.listdir(splashes_folder))
        open(splash_name, 'w').write(os.path.join(cur_dir, splashes_folder, new_splash))

