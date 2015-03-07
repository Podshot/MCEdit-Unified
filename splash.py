#! /usr/bin/env python
# Taken from http://www.pygame.org/project-Splash+screen-1186-.html by Rock Achu (rockhachu2)
# and tweaked ;)
import pygame
import os
print 'Splash load...'
os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
pygame.font.init()
no_splash = False
try:
    try:
        splash = pygame.image.load("splash.png")
    except:
        splash = pygame.image.load(os.path.join(".", "splash.png"))
    screen = pygame.display.set_mode(splash.get_size(),pygame.NOFRAME)
    screen.blit(splash, (0,0))
except:
    font = pygame.font.Font(pygame.font.get_default_font(), 48)
    buf = font.render("MCEDit is loading...", True, (128, 128, 128))
    screen = pygame.display.set_mode((buf.get_width() + 20, buf.get_height() + 20), pygame.NOFRAME)
    screen.blit(buf, (10, 10))
    splash = pygame.display.get_surface()
    no_splash = True
pygame.display.update()
os.environ['SDL_VIDEO_CENTERED'] = '0'

# Random splash
if not no_splash:
    from random import choice
    from shutil import copyfile
    splashes_folder = 'splashes'
    if not os.path.exists(splashes_folder):
        splashes_folder = os.path.join('.', splashes_folder)
    if os.path.exists(splashes_folder):
        new_splash = choice(os.listdir(splashes_folder))
        copyfile(os.path.join(splashes_folder, new_splash), os.path.join('.', 'splash.png'))

