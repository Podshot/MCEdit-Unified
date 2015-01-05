#! /usr/bin/env python
# Taken from http://www.pygame.org/project-Splash+screen-1186-.html by Rock Achu (rockhachu2)
# and tweaked ;)
import pygame
import os
print 'Splash load...'
os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
pygame.font.init()
splash = pygame.image.load("splash.png")
screen = pygame.display.set_mode(splash.get_size(),pygame.NOFRAME)
screen.blit(splash, (0,0))
pygame.display.update()
os.environ['SDL_VIDEO_CENTERED'] = '0'

