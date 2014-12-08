from OpenGL import GL

from numpy import array
from albow import ButtonBase, ValueDisplay, AttrRef, Row
from albow.openglwidgets import GLOrtho
import thumbview
import blockpicker
from glbackground import Panel, GLBackground
from glutils import DisplayList
from pymclevel.items import items


class ItemView(GLOrtho):
    def __init__(self, materials, id_="minecraft:air", data=0):
        GLOrtho.__init__(self)
        self.list = DisplayList(self._gl_draw)
        self.id_ = id_
        self.data = data
        self.materials = materials

    listItemInfo = None

    def gl_draw(self):
        if self.listItemInfo != [self.id_, self.data]:
            self.list.invalidate()
            self.listItemInfo = [self.id_, self.data]

        self.list.call()

    def _gl_draw(self):
        id_ = self.id_
        data = self.data
        if id_ is 0:
            return

        GL.glColor(1.0, 1.0, 1.0, 1.0)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glEnable(GL.GL_ALPHA_TEST)
        self.materials.terrainTexture.bind()
        pixelScale = 0.5 if self.materials.name in ("Pocket", "Alpha") else 1.0
        texSize = 16 * pixelScale

        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glVertexPointer(2, GL.GL_FLOAT, 0, array([-1, -1,
                                                     - 1, 1,
                                                     1, 1,
                                                     1, -1, ], dtype='float32'))
        texOrigin = array(self.materials.blockTextures[items.items[id_]["id"], data, 0])
        texOrigin *= pixelScale

        GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, array([texOrigin[0], texOrigin[1] + texSize,
                                                       texOrigin[0], texOrigin[1],
                                                       texOrigin[0] + texSize, texOrigin[1],
                                                       texOrigin[0] + texSize, texOrigin[1] + texSize],
                                                      dtype='float32'))

        GL.glDrawArrays(GL.GL_QUADS, 0, 4)

        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisable(GL.GL_ALPHA_TEST)
        GL.glDisable(GL.GL_TEXTURE_2D)

    @property
    def tooltipText(self):
        return "{0}".format(items.findItem(self.id_, self.data).name)


class ItemButton(ButtonBase, Panel):
    _ref = None

    def __init__(self, materials, id_="minecraft:air" , data=0, ref=None, recentBlocks=None, *a, **kw):
        self.allowWildcards = False
        Panel.__init__(self, *a, **kw)

        self.bg_color = (1, 1, 1, 0.25)
        #self._ref = ref
        #if blockInfo is None and ref is not None:
        #    blockInfo = ref.get()
        #blockInfo = blockInfo or materials.Air

        if recentBlocks is not None:
            self.recentBlocks = recentBlocks
        else:
            self.recentBlocks = [["minecraft:air", 0]]

        self.itemView = thumbview.ItemThumbView(materials, id_, data, size=(48, 48))
        self.itemLabel = ValueDisplay(ref=AttrRef(self, 'labelText'), width=180, align="l")
        row = Row((self.itemView, self.itemLabel), align="b")

        # col = Column( (self.blockButton, self.blockNameLabel) )
        self.add(row)
        self.shrink_wrap()

        # self.blockLabel.bottom = self.blockButton.bottom
        # self.blockLabel.centerx = self.blockButton.centerx

        # self.add(self.blockLabel)

        self.materials = materials
        self.id_ = id_
        self.data = data
        # self._ref = ref
        self.updateRecentItemView()

    recentBlockLimit = 7

    #@property
    #def blockInfo(self):
    #    if self._ref:
    #        return self._ref.get()
    #    else:
    #        return self._blockInfo

    #@blockInfo.setter
    #def blockInfo(self, bi):
    #    if self._ref:
    #        self._ref.set(bi)
    #    else:
    #        self._blockInfo = bi
    #    self.blockView.blockInfo = bi
    #    if bi not in self.recentBlocks:
    #        self.recentBlocks.append(bi)
    #        if len(self.recentBlocks) > self.recentBlockLimit:
    #            self.recentBlocks.pop(0)
    #        self.updateRecentBlockView()

    @property
    def labelText(self):
        labelText = items.findItem(self.id_, self.data).name
        if len(labelText) > 24:
            labelText = labelText[:23] + "..."
        return labelText

        # self.blockNameLabel.text =

    def createRecentItemView(self):
        def makeItemView(ii):
            if "texture" in items.items[ii[0]]:
                texture = items.items[ii[0]]["texture"]
                if type(texture) != str and type(texture) != unicode:
                    if len(texture) -1 >= ii[1]:
                        texture = texture[ii[1]]
                image = pygame.image.load(os.path.join(directories.getDataDir(), "item-textures", ii[0].split(":")[0], texture))
                image = pygame.transform.scale(image, 16, 16)
                self.iv = Image(image)
                iv.size = (16, 16)
            else:
                iv = ItemView(self.materials, ii[0], ii[1])
                iv.size = (16, 16)
            

            def action(evt):
                self.blockInfo = ii

            iv.mouse_up = action
            return iv

        
        row = [makeItemView(ii) for ii in self.recentBlocks]
        row = Row(row)

        widget = GLBackground()
        widget.bg_color = (0.8, 0.8, 0.8, 0.8)
        widget.add(row)
        widget.shrink_wrap()
        widget.anchor = "whtr"
        return widget

    def updateRecentItemView(self):
        if self.recentItemView:
            self.recentItemView.set_parent(None)
        self.recentItemView = self.createRecentItemView()

        self.recentItemView.right = self.width
        self.add(self.recentItemView)
        # print self.rect, self.recentBlockView.rect

    recentItemView = None

    @property
    def tooltipText(self):
        return "{0}".format(items.findItem(self.id_, self.data).name)

    def action(self):
        blockPicker = blockpicker.BlockPicker(self.materials.Stone, self.materials, allowWildcards=False)
        blockPicker.present()
