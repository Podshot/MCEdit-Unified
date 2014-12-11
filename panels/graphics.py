import albow
from albow.dialogs import Dialog
import mceutils
import resource_packs
import pymclevel
from config import config


class GraphicsPanel(Dialog):
    anchor = 'wh'

    def __init__(self, mcedit):
        Dialog.__init__(self)

        self.mcedit = mcedit

        fieldOfViewRow = mceutils.FloatInputRow("Field of View: ",
                                                ref=config.settings.fov, width=100, min=25, max=120)

        targetFPSRow = mceutils.IntInputRow("Target FPS: ",
                                            ref=config.settings.targetFPS, width=100, min=1, max=60)

        bufferLimitRow = mceutils.IntInputRow("Vertex Buffer Limit (MB): ",
                                              ref=config.settings.vertexBufferLimit, width=100, min=0)

        fastLeavesRow = mceutils.CheckBoxLabel("Fast Leaves",
                                               ref=config.settings.fastLeaves,
                                               tooltipText="Leaves are solid, like Minecraft's 'Fast' graphics")

        roughGraphicsRow = mceutils.CheckBoxLabel("Rough Graphics",
                                                  ref=config.settings.roughGraphics,
                                                  tooltipText="All blocks are drawn the same way (overrides 'Fast Leaves')")

        enableMouseLagRow = mceutils.CheckBoxLabel("Enable Mouse Lag",
                                                   ref=config.settings.enableMouseLag,
                                                 tooltipText="Enable choppy mouse movement for faster loading.")

        packs = resource_packs.packs.get_available_resource_packs()
        packs.remove('Default')
        packs.sort()
        packs.insert(0, 'Default')
        self.resourcePackButton = mceutils.ChoiceButton(packs, choose=self.change_texture)
        self.resourcePackButton.selectedChoice = resource_packs.packs.get_selected_resource_pack_name()

        settingsColumn = albow.Column((fastLeavesRow,
                                       roughGraphicsRow,
                                       enableMouseLagRow,
                                       #                                  texturePackRow,
                                       fieldOfViewRow,
                                       targetFPSRow,
                                       bufferLimitRow,
                                       self.resourcePackButton,
                                      ), align='r')

        settingsColumn = albow.Column((albow.Label("Settings"),
                                       settingsColumn))

        settingsRow = albow.Row((settingsColumn,))

        optionsColumn = albow.Column((settingsRow, albow.Button("OK", action=self.dismiss)))

        self.add(optionsColumn)
        self.shrink_wrap()

    def _reloadTextures(self, pack):
        if hasattr(pymclevel.alphaMaterials, "terrainTexture"):
            self.mcedit.displayContext.loadTextures()

    def change_texture(self):
        resource_packs.packs.set_selected_resource_pack_name(self.resourcePackButton.selectedChoice)
        self.mcedit.displayContext.loadTextures()
    texturePack = config.settings.skin.property(_reloadTextures)
