import albow
from albow.dialogs import Dialog
from config import config
import pygame
from albow.translate import _, buildTemplate
import sys
import os
import logging
import traceback
import directories

old_lang = None
old_fprop = None

class OptionsPanel(Dialog):
    anchor = 'wh'

    def __init__(self, mcedit):
        Dialog.__init__(self)

        self.mcedit = mcedit

        self.langs = {}
        self.sgnal = {}
        self.portableVar = albow.AttrRef(self, 'portableLabelText')
        self.saveOldPortable = self.portableVar.get()

        self.saveOldConfig = {
            config.controls.autobrake:                        config.controls.autobrake.get(),
            config.controls.swapAxes:                         config.controls.swapAxes.get(),
            config.controls.cameraAccel:                      config.controls.cameraAccel.get(),
            config.controls.cameraDrag:                       config.controls.cameraDrag.get(),
            config.controls.cameraMaxSpeed:                   config.controls.cameraMaxSpeed.get(),
            config.controls.cameraBrakingSpeed:               config.controls.cameraBrakingSpeed.get(),
            config.controls.mouseSpeed:                       config.controls.mouseSpeed.get(),
            config.settings.undoLimit:                        config.settings.undoLimit.get(),
            config.settings.maxCopies:                        config.settings.maxCopies.get(),
            config.controls.invertMousePitch:                 config.controls.invertMousePitch.get(),
            config.settings.spaceHeight:                      config.settings.spaceHeight.get(),
            albow.AttrRef(self, 'blockBuffer'):               albow.AttrRef(self, 'blockBuffer').get(),
            config.settings.setWindowPlacement:               config.settings.setWindowPlacement.get(),
            config.settings.rotateBlockBrush:                 config.settings.rotateBlockBrush.get(),
            config.settings.shouldResizeAlert:                config.settings.shouldResizeAlert.get(),
            config.settings.superSecretSettings:              config.settings.superSecretSettings.get(),
            config.settings.longDistanceMode:                 config.settings.longDistanceMode.get(),
            config.settings.flyMode:                          config.settings.flyMode.get(),
            config.settings.langCode:                         config.settings.langCode.get(),
            config.settings.compassToggle:                    config.settings.compassToggle.get(),
            config.settings.compassSize:                      config.settings.compassSize.get(),
            config.settings.fontProportion:                   config.settings.fontProportion.get(),
            config.settings.fogIntensity:                     config.settings.fogIntensity.get(),
            config.schematicCopying.cancelCommandBlockOffset: config.schematicCopying.cancelCommandBlockOffset.get()
        }
        global old_lang
        if old_lang == None:
            old_lang = config.settings.langCode.get()
        global old_fprop
        if old_fprop == None:
            old_fprop = config.settings.fontProportion.get()

    def initComponents(self):
        """Initilize the window components. Call this after translation hs been loaded."""
        autoBrakeRow = albow.CheckBoxLabel("Autobrake",
                                              ref=config.controls.autobrake,
                                              tooltipText="Apply brake when not pressing movement keys")

        swapAxesRow = albow.CheckBoxLabel("Swap Axes Looking Down",
                                             ref=config.controls.swapAxes,
                                             tooltipText="Change the direction of the Forward and Backward keys when looking down")

        cameraAccelRow = albow.FloatInputRow("Camera Acceleration: ",
                                                ref=config.controls.cameraAccel, width=100, min=5.0)

        cameraDragRow = albow.FloatInputRow("Camera Drag: ",
                                               ref=config.controls.cameraDrag, width=100, min=1.0)

        cameraMaxSpeedRow = albow.FloatInputRow("Camera Max Speed: ",
                                                   ref=config.controls.cameraMaxSpeed, width=100, min=1.0)

        cameraBrakeSpeedRow = albow.FloatInputRow("Camera Braking Speed: ",
                                                     ref=config.controls.cameraBrakingSpeed, width=100,
                                                     min=1.0)

        mouseSpeedRow = albow.FloatInputRow("Mouse Speed: ",
                                               ref=config.controls.mouseSpeed, width=100, min=0.1,
                                               max=20.0)

        undoLimitRow = albow.IntInputRow("Undo Limit: ",
                                            ref=config.settings.undoLimit, width=100, min=0)

        maxCopiesRow = albow.IntInputRow("Copy Stack Size: ",
                                            ref=config.settings.maxCopies, width=100, min=0,
                                            tooltipText="Maximum number of copied objects.")

        compassSizeRow = albow.IntInputRow("Compass Size (%): ",
                                            ref=config.settings.compassSize, width=100, min=0, max=100)

        fontProportion = albow.IntInputRow("Fonts Proportion (%): ",
                                            ref=config.settings.fontProportion, width=100, min=0,
                                            tooltipText="Fonts sizing proportion. The number is a percentage.\nRestart needed!")
        albow.resource.font_proportion = config.settings.fontProportion.get()

        fogIntensityRow = albow.IntInputRow("Fog Intensity (%): ",
                                            ref=config.settings.fogIntensity, width=100, min=0, max=100)

        invertRow = albow.CheckBoxLabel("Invert Mouse",
                                           ref=config.controls.invertMousePitch,
                                           tooltipText="Reverse the up and down motion of the mouse.")

        spaceHeightRow = albow.IntInputRow("Low Detail Height",
                                              ref=config.settings.spaceHeight,
                                              tooltipText="When you are this far above the top of the world, move fast and use low-detail mode.")

        blockBufferRow = albow.IntInputRow("Block Buffer (MB):",
                                              ref=albow.AttrRef(self, 'blockBuffer'), min=1,
                                              tooltipText="Amount of memory used for temporary storage.  When more than this is needed, the disk is used instead.")

        setWindowPlacementRow = albow.CheckBoxLabel("Set Window Placement",
                                                       ref=config.settings.setWindowPlacement,
                                                       tooltipText="Try to save and restore the window position.")

        rotateBlockBrushRow = albow.CheckBoxLabel("Rotate block with brush",
                                                        ref=config.settings.rotateBlockBrush,
                                                        tooltipText="When rotating your brush, also rotate the orientation of the block your brushing with")

        compassToggleRow =albow.CheckBoxLabel("Toggle compass",
                                                        ref=config.settings.compassToggle)

        windowSizeRow = albow.CheckBoxLabel("Window Resize Alert",
                                               ref=config.settings.shouldResizeAlert,
                                               tooltipText="Reminds you that the cursor won't work correctly after resizing the window.")

        superSecretSettingsRow = albow.CheckBoxLabel("Super Secret Settings",
                                                ref=config.settings.superSecretSettings,
                                                tooltipText="Weird stuff happen!")

        longDistanceRow = albow.CheckBoxLabel("Long-Distance Mode",
                                                 ref=config.settings.longDistanceMode,
                                                 tooltipText="Always target the farthest block under the cursor, even in mouselook mode.")

        flyModeRow = albow.CheckBoxLabel("Fly Mode",
                                            ref=config.settings.flyMode,
                                            tooltipText="Moving forward and Backward will not change your altitude in Fly Mode.")
        
        showCommandsRow = albow.CheckBoxLabel("Show Block Info when hovering",
                                              ref=config.settings.showQuickBlockInfo,
                                              tooltipText="Shows summarized info of some Blocks when hovering over it.")

        cancelCommandBlockOffset = albow.CheckBoxLabel("Cancel Command Block Offset",
                                                       ref=config.schematicCopying.cancelCommandBlockOffset,
                                                       tooltipText="Cancels the command blocks coords changed when copied.")

        lng = config.settings.langCode.get()

        langs = sorted(self.getLanguageChoices().items())

        langNames = [k for k, v in langs]

        self.languageButton = albow.ChoiceButton(langNames, choose=self.changeLanguage, doNotTranslate=True)
        if self.sgnal[lng] in self.languageButton.choices:
            self.languageButton.selectedChoice = self.sgnal[lng]

        langButtonRow = albow.Row((albow.Label("Language", tooltipText="Choose your language."), self.languageButton))

        portableList = ["Portable", "Fixed"]
        self.goPortableButton = goPortableButton = albow.ChoiceButton(portableList, choose=self.togglePortable)
        goPortableButton.selectedChoice = self.saveOldPortable

        goPortableButton.tooltipText = self.portableButtonTooltip()
        goPortableRow = albow.Row((albow.Label("Install Mode"), goPortableButton))

# Disabled Crash Reporting Option
#       reportRow = albow.CheckBoxLabel("Report Errors",
#                                          ref=config.settings.reportCrashes,
#                                          tooltipText="Automatically report errors to the developer.")

        self.inputs = (
            spaceHeightRow,
            cameraAccelRow,
            cameraDragRow,
            cameraMaxSpeedRow,
            cameraBrakeSpeedRow,
            blockBufferRow,
            mouseSpeedRow,
            undoLimitRow,
            maxCopiesRow,
            compassSizeRow,
            fontProportion,
            fogIntensityRow,
        )

        options = (
                    longDistanceRow,
                    flyModeRow,
                    autoBrakeRow,
                    swapAxesRow,
                    invertRow,
                    superSecretSettingsRow,
                    rotateBlockBrushRow,
                    compassToggleRow,
                    showCommandsRow,
                    cancelCommandBlockOffset,
                    langButtonRow,
                    ) + (
                        ((sys.platform == "win32" and pygame.version.vernum == (1, 9, 1)) and (windowSizeRow,) or ())
                    ) + (
                        (sys.platform == "win32") and (setWindowPlacementRow,) or ()
                    ) + (
                        (not sys.platform == "darwin") and (goPortableRow,) or ()
                    )

        rightcol = albow.Column(options, align='r')
        leftcol = albow.Column(self.inputs, align='r')

        optionsColumn = albow.Column((albow.Label("Options"),
                                      albow.Row((leftcol, rightcol), align="t")))

        settingsRow = albow.Row((optionsColumn,))

        buttonsRow = albow.Row((albow.Button("OK", action=self.dismiss), albow.Button("Cancel", action=self.cancel)))

        resetToDefaultRow = albow.Row((albow.Button("Reset to default", action=self.resetDefault),))

        optionsColumn = albow.Column((settingsRow, buttonsRow, resetToDefaultRow))
        optionsColumn.key_down = self.key_down

        self.add(optionsColumn)
        self.shrink_wrap()

    @property
    def blockBuffer(self):
        return config.settings.blockBuffer.get() / 1048576

    @blockBuffer.setter
    def blockBuffer(self, val):
        config.settings.blockBuffer.set(int(val * 1048576))

    def getLanguageChoices(self, current=None):
        files = os.listdir(albow.translate.langPath)
        langs = {}
        sgnal = {}
        for file in files:
            name, ext = os.path.splitext(file)
            if ext == ".trn" and len(name) == 5 and name[2] == "_":
                langName = albow.translate.getLangName(file)
                langs[langName] = name
                sgnal[name] = langName
        if "English (US)" not in langs.keys():
            langs[u"English (US)"] = "en_US"
            sgnal["en_US"] = u"English (US)"
        self.langs = langs
        self.sgnal = sgnal
        logging.debug("Detected languages: %s"%self.langs)
        return langs

    def changeLanguage(self):
        if albow.translate.buildTemplate:
            self.languageButton.selectedChoice = 'English (US)'
            return
        langName = self.languageButton.selectedChoice
        if langName not in self.langs:
            lng = "en_US"
        else:
            lng = self.langs[langName]
        config.settings.langCode.set(lng)
        #-# Translation live update preparation
        logging.debug('*** Language change detected.')
        logging.debug('    Former language: %s.'%albow.translate.getLang())
        logging.debug('    New language: %s.'%lng)
        albow.translate.langPath = os.sep.join((directories.getDataDir(), "lang"))
        update = albow.translate.setLang(lng)[2]
        logging.debug('    Update done? %s (Magic %s)'%(update, update or lng == 'en_US'))
        self.mcedit.root.set_update_ui(update or lng == 'en_US')
        self.mcedit.root.set_update_ui(False)
        self.mcedit.editor.set_update_ui(update or lng == 'en_US')
        self.mcedit.editor.set_update_ui(False)
        #-#

    @staticmethod
    def portableButtonTooltip():
        return (
        "Click to make your MCEdit install self-contained by moving the settings and schematics into the program folder",
        "Click to make your MCEdit install persistent by moving the settings and schematics into your Documents folder")[
            directories.portable]

    @property
    def portableLabelText(self):
        return ("Portable", "Fixed")[1 - directories.portable]

    @portableLabelText.setter
    def portableLabelText(self, *args, **kwargs):
        pass

    def togglePortable(self):
        if sys.platform == "darwin":
            return False
        textChoices = [
            _("This will make your MCEdit \"portable\" by moving your settings and schematics into the same folder as {0}. Continue?").format(
                (sys.platform == "darwin" and _("the MCEdit application") or _("MCEditData"))),
            _("This will move your settings and schematics to your Documents folder. Continue?"),
        ]
        useExisting = False

        alertText = textChoices[directories.portable]
        if albow.ask(alertText) == "OK":
            if [directories.hasPreviousPortableInstallation, directories.hasPreviousFixedInstallation][directories.portable]():
                asked = albow.ask("Found a previous %s installation"%["portable", "fixed"][directories.portable], responses=["Use", "Overwrite", "Cancel"])
                if asked == "Use":
                    useExisting = True
                elif asked == "Overwrite":
                    useExisting = False
                elif asked == "Cancel":
                    return False
            try:
                [directories.goPortable, directories.goFixed][directories.portable](useExisting)
            except Exception, e:
                traceback.print_exc()
                albow.alert(_(u"Error while moving files: {0}").format(repr(e)))
        else:
            self.goPortableButton.selectedChoice = self.saveOldPortable

        self.goPortableButton.tooltipText = self.portableButtonTooltip()
        return True

    def dismiss(self, *args, **kwargs):
        """Used to change the font proportion."""
        # If font proportion setting has changed, update the UI.
        if config.settings.fontProportion.get() != self.saveOldConfig[config.settings.fontProportion]:
            albow.resource.reload_fonts(proportion=config.settings.fontProportion.get())
            self.mcedit.root.set_update_ui(True)
            self.mcedit.root.set_update_ui(False)
            self.mcedit.editor.set_update_ui(True)
            self.mcedit.editor.set_update_ui(False)

        self.reshowNumberFields()
        for key in self.saveOldConfig.keys():
            self.saveOldConfig[key] = key.get()

        config.save()
        Dialog.dismiss(self, *args, **kwargs)

    def cancel(self, *args, **kwargs):
        Changes = False
        self.reshowNumberFields()
        for key in self.saveOldConfig.keys():
            if key.get() != self.saveOldConfig[key]:
                Changes = True
        oldLanguage = self.saveOldConfig[config.settings.langCode]
        if config.settings.langCode.get() != oldLanguage:
            Changes = True
        newPortable = self.portableVar.get()
        if newPortable != self.saveOldPortable:
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

        if config.settings.langCode.get() != oldLanguage:
            self.languageButton.selectedChoice = self.sgnal[oldLanguage]
            self.changeLanguage()

        if _(newPortable) != _(self.saveOldPortable):
            self.portableVar.set(newPortable)
            self.togglePortable()

        for key in self.saveOldConfig.keys():
            key.set(self.saveOldConfig[key])

        config.save()
        Dialog.dismiss(self, *args, **kwargs)

    def resetDefault(self):
        self.reshowNumberFields()
        for key in self.saveOldConfig.keys():
            if "AttrRef" in str(key):
                key.set(config.settings.blockBuffer.default / 1048576)
            elif "lang" not in str(key):
                key.set(key.default)

        if config.settings.langCode.get() != "en_US":
            config.settings.langCode.set("en_US")
            self.changeLanguage()
        if "Fixed" != self.portableVar.get():
            self.portableVar.set("Fixed")
            self.togglePortable()

        config.save()

    def reshowNumberFields(self):
        for key in self.inputs:
            key.subwidgets[1].editing = False

    def dispatch_key(self, name, evt):
        super(OptionsPanel, self).dispatch_key(name, evt)
        if name == "key_down":
            keyname = self.get_root().getKey(evt)
            if keyname == 'Escape':
                self.cancel()
