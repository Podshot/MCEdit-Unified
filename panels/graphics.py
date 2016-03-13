import albow
from albow.dialogs import Dialog
from resource_packs import ResourcePackHandler
import pymclevel
from config import config


class GraphicsPanel(Dialog):
    anchor = 'wh'

    def __init__(self, mcedit):
        Dialog.__init__(self)

        self.mcedit = mcedit

        self.saveOldConfig = {
            config.settings.fov: config.settings.fov.get(),
            config.settings.targetFPS: config.settings.targetFPS.get(),
            config.settings.vertexBufferLimit: config.settings.vertexBufferLimit.get(),
            config.settings.fastLeaves: config.settings.fastLeaves.get(),
            config.settings.roughGraphics: config.settings.roughGraphics.get(),
            config.settings.enableMouseLag: config.settings.enableMouseLag.get(),
            config.settings.maxViewDistance: config.settings.maxViewDistance.get()
        }

        self.saveOldResourcePack = ResourcePackHandler.Instance().get_selected_resource_pack_name()

        self.fieldOfViewRow = albow.FloatInputRow("Field of View: ",
                                                ref=config.settings.fov, width=100, min=25, max=120)

        self.targetFPSRow = albow.IntInputRow("Target FPS: ",
                                                ref=config.settings.targetFPS, width=100, min=1, max=60)

        self.bufferLimitRow = albow.IntInputRow("Vertex Buffer Limit (MB): ",
                                                ref=config.settings.vertexBufferLimit, width=100, min=0)

        fastLeavesRow = albow.CheckBoxLabel("Fast Leaves",
                                                ref=config.settings.fastLeaves,
                                                tooltipText="Leaves are solid, like Minecraft's 'Fast' graphics")

        roughGraphicsRow = albow.CheckBoxLabel("Rough Graphics",
                                                ref=config.settings.roughGraphics,
                                                tooltipText="All blocks are drawn the same way (overrides 'Fast Leaves')")

        enableMouseLagRow = albow.CheckBoxLabel("Enable Mouse Lag",
                                                ref=config.settings.enableMouseLag,
                                                tooltipText="Enable choppy mouse movement for faster loading.")
        
        playerSkins = albow.CheckBoxLabel("Show Player Skins",
                                             ref=config.settings.downloadPlayerSkins,
                                             tooltipText="Show player skins while editing the world")
        
        self.maxView = albow.IntInputRow("Max View Distance",
                                       ref=config.settings.maxViewDistance,
                                       tooltipText="Sets the maximum view distance for the renderer. Values over 32 can possibly be unstable, so use it at your own risk"
                                       )
        self.maxView.subwidgets[1]._increment = 2

        packs = ResourcePackHandler.Instance().get_available_resource_packs()
        packs.remove('Default Resource Pack')
        packs.sort()
        packs.insert(0, 'Default Resource Pack')
        self.resourcePackButton = albow.ChoiceButton(packs, choose=self.change_texture, doNotTranslate=True)
        self.resourcePackButton.selectedChoice = self.saveOldResourcePack

        settingsColumn = albow.Column((fastLeavesRow,
                                       roughGraphicsRow,
                                       enableMouseLagRow,
                                       #                                  texturePackRow,
                                       self.fieldOfViewRow,
                                       self.targetFPSRow,
                                       self.bufferLimitRow,
                                       self.maxView,
                                       playerSkins,
                                       self.resourcePackButton,
                                      ), align='r')

        settingsColumn = albow.Column((albow.Label("Graphics Settings"),
                                       settingsColumn))

        settingsRow = albow.Row((settingsColumn,))

        buttonsRow = albow.Row((albow.Button("OK", action=self.dismiss), albow.Button("Cancel", action=self.cancel)))

        resetToDefaultRow = albow.Row((albow.Button("Reset to default", action=self.resetDefault),))

        optionsColumn = albow.Column((settingsRow, buttonsRow, resetToDefaultRow))

        self.add(optionsColumn)
        self.shrink_wrap()

    def _reloadTextures(self, pack):
        if hasattr(pymclevel.alphaMaterials, "terrainTexture"):
            self.mcedit.displayContext.loadTextures()

    def change_texture(self):
        ResourcePackHandler.Instance().set_selected_resource_pack_name(self.resourcePackButton.selectedChoice)
        self.mcedit.displayContext.loadTextures()
    texturePack = config.settings.skin.property(_reloadTextures)
    
    def checkMaxView(self):
        if (config.settings.maxViewDistance.get() % 2) != 0:
            config.settings.maxViewDistance.set(config.settings.maxViewDistance.get()-1)

    def dismiss(self, *args, **kwargs):
        self.reshowNumberFields()
        self.checkMaxView()
        for key in self.saveOldConfig.keys():
            self.saveOldConfig[key] = key.get()
        self.saveOldResourcePack = self.resourcePackButton.selectedChoice

        config.save()
        Dialog.dismiss(self, *args, **kwargs)

    def cancel(self, *args, **kwargs):
        Changes = False

        self.reshowNumberFields()

        for key in self.saveOldConfig.keys():
            if key.get() != self.saveOldConfig[key]:
                Changes = True
        if self.saveOldResourcePack != self.resourcePackButton.selectedChoice:
            Changes = True

        if not Changes:
            Dialog.dismiss(self, *args, **kwargs)
            return

        result = albow.ask("Do you want to save your changes?", ["Save", "Don't Save", "Cancel"])
        if result == "Cancel":
            return
        if result == "Save":
            self.dismiss(*args, **kwargs)
            return

        for key in self.saveOldConfig.keys():
            key.set(self.saveOldConfig[key])
        if self.resourcePackButton.selectedChoice != self.saveOldResourcePack:
            self.resourcePackButton.selectedChoice = self.saveOldResourcePack
            self.change_texture()
        config.save()
        Dialog.dismiss(self, *args, **kwargs)

    def resetDefault(self):
        for key in self.saveOldConfig.keys():
            key.set(key.default)
        self.reshowNumberFields()
        if self.resourcePackButton.selectedChoice != "Default Resource Pack":
            self.resourcePackButton.selectedChoice = "Default Resource Pack"
            self.change_texture()

        config.save()

    def reshowNumberFields(self):
        self.fieldOfViewRow.subwidgets[1].editing = False
        self.targetFPSRow.subwidgets[1].editing = False
        self.bufferLimitRow.subwidgets[1].editing = False
        self.maxView.subwidgets[1].editing = False

    def dispatch_key(self, name, evt):
        super(GraphicsPanel, self).dispatch_key(name, evt)
        if name == "key_down":
            keyname = self.get_root().getKey(evt)
            if keyname == 'Escape':
                self.cancel()
