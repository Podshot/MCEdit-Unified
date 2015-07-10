# Fair warning, most of this is hacky/repurposed stuff from the player head rendering


from mceutils import loadPNGTexture, drawCube
from pymclevel.box import FloatBox
import numpy
from OpenGL import GL
from glutils import DisplayList

class CreeperModel:
    
    def __init__(self, creepers):
        self.creepers = creepers
        creeperHeadVertices = numpy.array(
            (
                # Backside of Head
                24, 16, # Bottom Left
                24, 8, # Top Left
                32, 8, # Top Right
                32, 16, # Bottom Right

                # Front of Head
                8, 16,
                8, 8,
                16, 8,
                16, 16,

                # Bottom
                24, 0,
                16, 0,
                16, 8,
                24, 8,

                # Top
                16, 0,
                8, 0,
                8, 8,
                16, 8,

                # Left
                8, 8,
                0, 8,
                0, 16,
                8, 16,

                # Right
                16, 16,
                24, 16,
                24, 8,
                16, 8,

            ), dtype='f4')
        
        creeperBodyVertices = numpy.array(
            (
                # Back of body
                32, 32,
                32, 20,
                40, 20,
                40, 32,
                
                # Front
                20, 32,
                20, 20,
                28, 20,
                28, 32,
                
                # Bottom
                36, 16,
                28, 16,
                28, 20,
                36, 20,
                
                # Top
                28, 16,
                20, 16,
                20, 20,
                28, 20,
                
                # Left
                20, 20,
                16, 20,
                16, 32,
                20, 32,
                
                # Right
                28, 32,
                32, 32,
                32, 20,
                28, 20,
                
             ), dtype='f4')
        
        creeperFeetVertices = numpy.array(
            (
                # Back
                12, 26,
                12, 20,
                16, 20,
                16, 26,
                
                # Front
                4, 26,
                4, 20,
                8, 20,
                8, 26,
                
                # Bottom
                12, 16,
                8, 16,
                8, 20,
                12, 20,
                
                # Top
                8, 16,
                4, 16,
                4, 20,
                8, 20,
                
                # Left
                4, 20,
                0, 20,
                0, 26,
                4, 26,
                
                # Right
                8, 26,
                12, 26,
                12, 20,
                8, 20,
            ), dtype='f4')
        
        creeperHeadVertices.shape = (24, 2)
        creeperHeadVertices *= 4
        creeperHeadVertices[:, 1] *= 2
        
        creeperBodyVertices.shape = (24, 2)
        creeperBodyVertices *= 4
        creeperBodyVertices[:, 1] *= 2
        
        creeperFeetVertices.shape = (24, 2)
        creeperFeetVertices *= 4
        creeperFeetVertices[:, 1] *= 2
        
        self.creeperVertices = (creeperHeadVertices, creeperBodyVertices, creeperFeetVertices)
        self.creeperFeetOffsets = ((0, 8.875, -0.125), (0, 8.875, 0.375), (0.249, 8.875, -0.125), (0.249, 8.875, 0.375))
        
        self.creeper_tex = loadPNGTexture('creeper.png')
        
        self.drawList = DisplayList()
        self.drawList.call(self.draw)
        
    def draw(self):
        for creeper in self.creepers:
            x, y, z = creeper
            creeper_head_box_origin = (x, y + 10, z)
            creeper_head_box_size = (0.5, 0.5, 0.5)
            self.creeper_head_box = FloatBox(creeper_head_box_origin, creeper_head_box_size)
        
            creeper_body_box_origin = (x, y + 9.25, z + 0.125)
            creeper_body_box_size = (0.5, 0.75, 0.25)
            self.creeper_body_box = FloatBox(creeper_body_box_origin, creeper_body_box_size)
        
            drawCube(self.creeper_head_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[0])
            drawCube(self.creeper_body_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[1])
            for offset in self.creeperFeetOffsets:
                creeper_feet_box_origin = (x + offset[0], y + offset[1], z + offset[2])
                creeper_feet_box_size = (0.25, 0.375, 0.25)
                creeper_feet_box = FloatBox(creeper_feet_box_origin, creeper_feet_box_size)
                drawCube(creeper_feet_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[2])