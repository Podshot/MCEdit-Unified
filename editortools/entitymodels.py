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
    
    def shapeVertices(self, verts):
        verts.shape = (24, 2)
        verts *= 4
        verts[:, 1] *= 2
        return verts
    
    def __init__(self, *args):
        print "EntityModelTool"
        EditorTool.__init__(self, *args)
        
        # Start Creeper Model
        creeper_fp = open(os.path.join("entity_models", "creeper.json"))
        creeper_model = json.load(creeper_fp)
        creeper_fp.close()
        
        creeperHeadVertices = self.shapeVertices(numpy.array(creeper_model["vertices"]["head"], dtype='f4'))
        creeperBodyVertices = self.shapeVertices(numpy.array(creeper_model["vertices"]["body"], dtype='f4'))
        creeperFeetVertices = self.shapeVertices(numpy.array(creeper_model["vertices"]["feet"], dtype='f4'))
        
        self.creeperVertices = (creeperHeadVertices, creeperBodyVertices, creeperFeetVertices)
        #self.creeperFeetOffsets = ((0, 8.875, -0.125), (0, 8.875, 0.375), (0.249, 8.875, -0.125), (0.249, 8.875, 0.375))
        self.creeperOffsets = (creeper_model["offsets"]["head"], creeper_model["offsets"]["body"], creeper_model["offsets"]["feet"])
        self.creeperBoxSizes = (creeper_model["sizes"]["head"], creeper_model["sizes"]["body"], creeper_model["sizes"]["feet"])
        
        self.creeper_tex = loadPNGTexture(creeper_model["texture"].replace("<sep>", os.path.sep))
        # End Creeper Model
        
        # Start Enderman Model
        enderman_fp = open(os.path.join("entity_models", "enderman.json"))
        enderman_model = json.load(enderman_fp)
        enderman_fp.close()
        
        endermanHeadVertices = self.shapeVertices(numpy.array(enderman_model["vertices"]["head"], dtype='f4'))
        endermanBodyVertices = self.shapeVertices(numpy.array(enderman_model["vertices"]["body"], dtype='f4'))
        endermanArmsVertices = self.shapeVertices(numpy.array(enderman_model["vertices"]["arms"], dtype='f4'))
        
        self.endermanVertices = (endermanHeadVertices, endermanBodyVertices, endermanArmsVertices, None)
        self.endermanOffsets = (enderman_model["offsets"]["head"], enderman_model["offsets"]["body"], enderman_model["offsets"]["arms"], enderman_model["offsets"]["feet"])
        self.endermanBoxSizes = (enderman_model["sizes"]["head"], enderman_model["sizes"]["body"], enderman_model["sizes"]["arms"], enderman_model["sizes"]["feet"])
        
        self.enderman_tex = loadPNGTexture(enderman_model["texture"].replace("<sep>", os.path.sep))
        
        self.markerList = DisplayList()
        
        
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
                        yaw = e["Rotation"][0].value
                        
                        GL.glPushMatrix()
                        GL.glTranslate(x, y, z)
                        x, y, z = (0,0,0)
                        GL.glRotate(yaw, 0, 1, 0)
                        GL.glColor(1, 1, 1, 1)
                        GL.glEnable(GL.GL_CULL_FACE)
                    
                        creeper_head_box = FloatBox(self.creeperOffsets[0], self.creeperBoxSizes[0])
        
                        creeper_body_box = FloatBox(self.creeperOffsets[1], self.creeperBoxSizes[1])
                    
                        drawCube(creeper_head_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[0])
                        print "Drew Creeper head at {0} {1} {2}".format(x, y, z)
                        drawCube(creeper_body_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[1])
                        for offset in self.creeperOffsets[2]:
                            creeper_feet_box = FloatBox(offset, self.creeperBoxSizes[2])
                            drawCube(creeper_feet_box, texture=self.creeper_tex, textureVertices=self.creeperVertices[2])
                        
                        GL.glDisable(GL.GL_CULL_FACE)
                        GL.glPopMatrix()

                    elif e["id"].value == "Enderman":
                        x, y, z = e["Pos"][0].value, e["Pos"][1].value, e["Pos"][2].value
                        yaw = e["Rotation"][0].value
                        
                        GL.glPushMatrix()
                        GL.glTranslate(x, y, z)
                        x, y, z = (0,0,0)
                        GL.glRotate(yaw, 0, 1, 0)
                        GL.glColor(1, 1, 1, 1)
                        GL.glEnable(GL.GL_CULL_FACE)
                        
                        enderman_head_box = FloatBox(self.endermanOffsets[0], self.endermanBoxSizes[0])
                        drawCube(enderman_head_box, texture=self.enderman_tex, textureVertices=self.endermanVertices[0])
                        
                        enderman_body_box = FloatBox(self.endermanOffsets[1], self.endermanBoxSizes[1])
                        drawCube(enderman_body_box, texture=self.enderman_tex, textureVertices=self.endermanVertices[1])
                        
                        for offset in self.endermanOffsets[2]:
                            enderman_arm_box = FloatBox(offset, self.endermanBoxSizes[2])
                            drawCube(enderman_arm_box, texture=self.enderman_tex, textureVertices=self.endermanVertices[2])
                        
                        for offset in self.endermanOffsets[3]:
                            enderman_feet_box = FloatBox(offset, self.endermanBoxSizes[2])
                            drawCube(enderman_feet_box, texture=self.enderman_tex, textureVertices=self.endermanVertices[2])
                        
                        GL.glDisable(GL.GL_CULL_FACE)
                        GL.glPopMatrix()
                        
                except Exception, e:
                    print repr(e)
                    continue
        GL.glDisable(GL.GL_DEPTH_TEST)