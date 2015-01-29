from OpenGL.GLU import *
from OpenGL.GL import *
import pygame
from pygame.locals import *
import sys
import math

class Camera:
    
    def __init__(self, fov, near, far):
        self.fov = fov
        self.near = near
        self.far = far
        self.x = 0
        self.y = 3
        self.z = -50
        self.rx = 0
        self.ry = 0
        self.rz = 0
        
    def updateView(self, width, height):
        self.width = width
        self.height = height
        self.aspect = float(width) / float(height)
        glViewport(0, 0, width, height)
        gluPerspective(self.fov, self.aspect, self.near, self.far)
        
    def make3D(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, self.aspect, self.near, self.far)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

        glMatrixMode(GL_MODELVIEW)
        
    def make2D(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, 0, 1)

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        glMatrixMode(GL_MODELVIEW)
        
    def setup(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        
        glLineWidth(1)
        
        glClearColor(0.58, 0.75, 0.95, 1)
        
    def useView(self):
        glRotatef(self.rx, 1, 0, 0)
        glRotatef(self.ry, 0, 1, 0)
        glRotatef(self.rz, 0, 0, 1)
        glTranslatef(self.x, -self.y, self.z)
        
    def move(self, amt, dir):
        self.z = self.z + amt * math.sin(math.radians(self.ry + 90 * dir))
        self.x = self.x + amt * math.cos(math.radians(self.ry + 90 * dir))
    
    def rotateX(self, x):
        self.rx += x
    
        if self.rx > 90:
            self.rx = 90
        elif self.rx < -90:
            self.rx = -90
            
    def rotateY(self, y):
        self.ry = (self.ry + y) % 360

def render():
    #Use lists here. See registerMap() function in World.java
    glPushMatrix()
    glBegin(GL_QUADS);
    glColor3f(1.0, 0.0, 0.0);
    glVertex3f(0.0, 1.0, 1.0);
    glVertex3f(1.0, 1.0, 1.0);
    glVertex3f(1.0, 1.0, 0.0);
    glVertex3f(0.0, 1.0, 0.0);
    glEnd();
 
    glBegin(GL_QUADS);
    glColor3f(0.0, 1.0, 0.0);
    glVertex3f(1.0, 0.0, 1.0);
    glVertex3f(1.0, 1.0, 1.0);
    glVertex3f(0.0, 1.0, 1.0);
    glVertex3f(0.0, 0.0, 1.0);
    glEnd();
 
    glBegin(GL_QUADS);
    glColor3f(0.0, 0.0, 1.0);
    glVertex3f(1.0, 1.0, 0.0);
    glVertex3f(1.0, 1.0, 1.0);
    glVertex3f(1.0, 0.0, 1.0);
    glVertex3f(1.0, 0.0, 0.0);
    glEnd();
 
    glBegin(GL_QUADS);
    glColor3f(0.0, 0.0, 1.0);
    glVertex3f(0.0, 0.0, 1.0);
    glVertex3f(0.0, 1.0, 1.0);
    glVertex3f(0.0, 1.0, 0.0);
    glVertex3f(0.0, 0.0, 0.0);
    glEnd();
 
    glBegin(GL_QUADS);
    glColor3f(1.0, 0.0, 0.0);
    glVertex3f(1.0, 0.0, 1.0);
    glVertex3f(0.0, 0.0, 1.0);
    glVertex3f(0.0, 0.0, 0.0);
    glVertex3f(1.0, 0.0, 0.0);
    glEnd();
 
    glBegin(GL_QUADS);
    glColor3f(0.0, 1.0, 0.0);
    glVertex3f(1.0, 1.0, 0.0);
    glVertex3f(1.0, 0.0, 0.0);
    glVertex3f(0.0, 0.0, 0.0);
    glVertex3f(0.0, 1.0, 0.0);
    glEnd();
    glPopMatrix()

def init():
    pygame.init()
    width = 800
    height = 600
    display = (width, height)
    pygame.display.set_mode(display, DOUBLEBUF|OPENGL|RESIZABLE)
    cam = Camera(70, 0.3, 16*16)
    cam.updateView(width, height)
    cam.setup()
    cam.make3D()
    
    looped = False
    x = 0
    z = 0
    
    while True:
        glLoadIdentity()
        glFinish()
    
        for event in pygame.event.get():
            if looped:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:
                    cam.updateView(event.w, event.h)
                elif event.type == pygame.MOUSEMOTION:
                    cam.rotateX(event.rel[1])
                    cam.rotateY(event.rel[0])
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_w:
                        z += 1
                    elif event.key == pygame.K_s:
                        z -= 1
                    if event.key == pygame.K_a:
                        x -= 1
                    elif event.key == pygame.K_d:
                        x += 1
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_w:
                        z -= 1
                    elif event.key == pygame.K_s:
                        z += 1
                    if event.key == pygame.K_a:
                        x += 1
                    elif event.key == pygame.K_d:
                        x -= 1
                    
        glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)
        
        if z == 1:
            cam.move(0.01, 1)
        elif z == -1:
            cam.move(-0.01, 1)
        if x == -1:
            cam.move(0.01, 0)
        elif x == 1:
            cam.move(-0.01, 0)
        
        cam.useView()
        
        render()
        pygame.display.flip()
        looped = True
        
if __name__ == "__main__": init()












