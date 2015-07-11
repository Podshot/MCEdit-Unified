from editortools.editortool import EditorTool
from glutils import DisplayList
from OpenGL import GL
from mceutils import loadPNGTexture, drawCube
from pymclevel.box import FloatBox
import numpy
import os
import json


class EntityModelTool(EditorTool):
    markerLevel = None
    model = None
    
    def __init__(self, *args):
        print "EntityModelTool"
        EditorTool.__init__(self, *args)
        fp = open(os.path.join("entity_models", "creeper.json"))
        model = json.load(fp)
        fp.close()
        
        creeperHeadVertices = numpy.array(model["vertices"]["head"], dtype='f4')
        creeperBodyVertices = numpy.array(model["vertices"]["body"], dtype='f4')
        creeperFeetVertices = numpy.array(model["vertices"]["feet"], dtype='f4')
        '''
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
        '''
        
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
        #self.creeperFeetOffsets = ((0, 8.875, -0.125), (0, 8.875, 0.375), (0.249, 8.875, -0.125), (0.249, 8.875, 0.375))
        self.creeperOffsets = (model["offsets"]["head"], model["offsets"]["body"], model["offsets"]["feet"])
        self.creeperBoxSizes = (model["sizes"]["head"], model["sizes"]["body"], model["sizes"]["feet"])
        
        self.markerList = DisplayList()
        
        self.creeper_tex = loadPNGTexture(model["texture"].replace("<sep>", os.path.sep))
        
    def drawToolMarkers(self):
        if self.markerLevel != self.editor.level:
            self.markerList.invalidate()
            self.markerLevel = self.editor.level
        self.markerList.call(self._drawToolMarkers)
        
    def _drawToolMarkers(self):
        GL.glColor(1.0, 1.0, 1.0, 0.5)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        for chunk in self.editor.level.getChunks():
            for e in chunk.Entities:
                try:
                    if e["id"].value == "Creeper":
                        x, y, z = e["Pos"][0].value, e["Pos"][1].value, e["Pos"][2].value
                        yaw, pitch = e["Rotation"][0].value, e["Rotation"][1].value
                        GL.glPushMatrix()
                        GL.glTranslate(x, y, z)
                        GL.glRotate(-yaw, 0, 1, 0)
                        GL.glRotate(pitch, 1, 0, 0)
                        GL.glColor(1, 1, 1, 1)
                        GL.glEnable(GL.GL_CULL_FACE)
                    
                        #creeper_head_box_origin = (x, y + 10, z)
                        creeper_head_box_origin = (x + self.creeperOffsets[0][0], y + self.creeperOffsets[0][1], z + self.creeperOffsets[0][2])
                        creeper_head_box_size = (self.creeperBoxSizes[0][0], self.creeperBoxSizes[0][1], self.creeperBoxSizes[0][1])
                        creeper_head_box = FloatBox(creeper_head_box_origin, creeper_head_box_size)
        
                        #creeper_body_box_origin = (x, y + 9.25, z + 0.125)
                        creeper_body_box_origin = (x + self.creeperOffsets[1][0], y + self.creeperOffsets[1][1], z + self.creeperOffsets[1][2])
                        creeper_body_box_size = (self.creeperBoxSizes[1][0], self.creeperBoxSizes[1][1], self.creeperBoxSizes[1][2])
                        creeper_body_box = FloatBox(creeper_body_box_origin, creeper_body_box_size)
                    
                        drawCube(creeper_head_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[0])
                        print "Drew Creeper head"
                        drawCube(creeper_body_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[1])
                        for offset in self.creeperOffsets[2]:
                            creeper_feet_box_origin = (x + offset[0], y + offset[1], z + offset[2])
                            creeper_feet_box_size = (self.creeperBoxSizes[2][0], self.creeperBoxSizes[2][1], self.creeperBoxSizes[2][2])
                            creeper_feet_box = FloatBox(creeper_feet_box_origin, creeper_feet_box_size)
                            drawCube(creeper_feet_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[2])
                        
                        GL.glDisable(GL.GL_CULL_FACE)
                        GL.glPopMatrix()
                except Exception, e:
                    print repr(e)
                    continue
        GL.glDisable(GL.GL_DEPTH_TEST)