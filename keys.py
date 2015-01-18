#.# Marks the layout modifications. -- D.C.-G.
from config import config
import albow
import mceutils
from pygame import key
from albow.dialogs import Dialog
from albow.translate import _
from glbackground import Panel

ESCAPE = '\033'


def remapMouseButton(button):
    buttons = [0, 1, 3, 2, 4, 5, 6, 7]  # mouse2 is right button, mouse3 is middle
    if button < len(buttons):
        return buttons[button]
    return button


class KeyConfigPanel(Dialog):
    keyConfigKeys = [
        "<Movement>",
        "Forward",
        "Back",
        "Left",
        "Right",
        "Up",
        "Down",
        "Brake",
        "",
        "<Camera>",
        "Pan Up",
        "Pan Down",
        "Pan Left",
        "Pan Right",
        "Toggle View",
        "Goto Panel",
        "View Distance",
        "Toggle Renderer",
        "",
        "<Blocks>",
        "Swap",
        "Delete Blocks",
        "Increase Reach",
        "Decrease Reach",
        "Reset Reach",
        "Export Selection",
        "Brush Line Tool",
        "",
        "<Clone>",
        "Rotate (Clone)",
        "Roll (Clone)",
        "Flip",
        "Mirror",
        "",
        "<Brush>",
        "Rotate (Brush)",
        "Roll (Brush)",
        "Increase Brush",
        "Decrease Brush",
        "",
        "<Fill and Replace>",
        "Replace Shortcut",
        "",
        "<Functions>",
        "Select All",
        "Deselect",
        "Undo",
        "Redo",
        "Cut",
        "Copy",
        "Paste",
        "Take a Screenshot",
        "Fast Nudge",
        "",
        "<Options>",
        "Long-Distance Mode",
        "Fly Mode",
        "",
        "<Menu>",
        "New World",
        "Quick Load",
        "Open",
        "Save",
        "Reload World",
        "Close World",
        "World Info",
        "Quit",
        "",
        "<Advanced>",
        "Debug Overlay",
        "Show Block Info",
        "Pick Block",
        "Select Chunks",
        "Deselect Chunks",
        "Snap Clone to Axis",
        "Blocks-Only Modifier",
        "Fast Increment Modifier"
    ]

    presets = {
                "WASD": [
                    ("Forward", "W"),
                    ("Back", "S"),
                    ("Left", "A"),
                    ("Right", "D"),
                    ("Up", "Space"),
                    ("Down", "Shift"),
                    ("Brake", "C"),

                    ("Pan Up", "I"),
                    ("Pan Down", "K"),
                    ("Pan Left", "J"),
                    ("Pan Right", "L"),
                    ("Toggle View", "Tab"),
                    ("Goto Panel", "Ctrl-G"),
                    ("View Distance", "Ctrl-F"),
                    ("Toggle Renderer", "Ctrl-M"),

                    ("Swap", "X"),
                    ("Delete Blocks", "Delete"),
                    ("Increase Reach", "Scroll Up"),
                    ("Decrease Reach", "Scroll Down"),
                    ("Reset Reach", "Button 3"),
                    ("Export Selection", "Ctrl-E"),
                    ("Brush Line Tool", "Z"),

                    ("Rotate (Clone)", "E"),
                    ("Roll (Clone)", "R"),
                    ("Flip", "F"),
                    ("Mirror", "G"),

                    ("Rotate (Brush)", "E"),
                    ("Roll (Brush)", "G"),
                    ("Increase Brush", "R"),
                    ("Decrease Brush", "F"),

                    ("Replace Shortcut", "R"),

                    ("Select All", "Ctrl-A"),
                    ("Deselect", "Ctrl-D"),
                    ("Undo", "Ctrl-Z"),
                    ("Redo", "Ctrl-Y"),
                    ("Cut", "Ctrl-X"),
                    ("Copy", "Ctrl-C"),
                    ("Paste", "Ctrl-V"),
                    ("Take a Screenshot", "F6"),
                    ("Fast Nudge", "None"),

                    ("Long-Distance Mode", "Alt-Z"),
                    ("Fly Mode", "None"),

                    ("New World", "Ctrl-N"),
                    ("Quick Load", "Ctrl-L"),
                    ("Open", "Ctrl-O"),
                    ("Save", "Ctrl-S"),
                    ("Reload World", "Ctrl-R"),
                    ("Close World", "Ctrl-W"),
                    ("World Info", "Ctrl-I"),
                    ("Quit", "Ctrl-Q"),

                    ("Debug Overlay", "0"),
                    ("Show Block Info", "Alt"),
                    ("Pick Block", "Alt"),
                    ("Select Chunks", "Z"),
                    ("Deselect Chunks", "Alt"),
                    ("Snap Clone to Axis", "Ctrl"),
                    ("Blocks-Only Modifier", "Alt"),
                    ("Fast Increment Modifier", "Ctrl")
                ],
                "Arrows": [
                    ("Forward", "Up"),
                    ("Back", "Down"),
                    ("Left", "Left"),
                    ("Right", "Right"),
                    ("Up", "Page Up"),
                    ("Down", "Page Down"),
                    ("Brake", "Space"),

                    ("Pan Up", "I"),
                    ("Pan Down", "K"),
                    ("Pan Left", "J"),
                    ("Pan Right", "L"),
                    ("Toggle View", "Tab"),
                    ("Goto Panel", "Ctrl-G"),
                    ("View Distance", "Ctrl-F"),
                    ("Toggle Renderer", "Ctrl-M"),

                    ("Swap", "\\"),
                    ("Delete Blocks", "Backspace"),
                    ("Increase Reach", "Scroll Up"),
                    ("Decrease Reach", "Scroll Down"),
                    ("Reset Reach", "Button 3"),
                    ("Export Selection", "Ctrl-E"),
                    ("Brush Line Tool", "Z"),

                    ("Rotate (Clone)", "Home"),
                    ("Roll (Clone)", "End"),
                    ("Flip", "Insert"),
                    ("Mirror", "Delete"),

                    ("Rotate (Brush)", "Home"),
                    ("Roll (Brush)", "Delete"),
                    ("Increase Brush", "End"),
                    ("Decrease Brush", "Insert"),

                    ("Replace Shortcut", "R"),

                    ("Select All", "Ctrl-A"),
                    ("Deselect", "Ctrl-D"),
                    ("Undo", "Ctrl-Z"),
                    ("Redo", "Ctrl-Y"),
                    ("Cut", "Ctrl-X"),
                    ("Copy", "Ctrl-C"),
                    ("Paste", "Ctrl-V"),
                    ("Take a Screenshot", "F6"),
                    ("Fast Nudge", "None"),

                    ("Long-Distance Mode", "Alt-Z"),
                    ("Fly Mode", "None"),

                    ("New World", "Ctrl-N"),
                    ("Quick Load", "Ctrl-L"),
                    ("Open", "Ctrl-O"),
                    ("Save", "Ctrl-S"),
                    ("Reload World", "Ctrl-R"),
                    ("Close World", "Ctrl-W"),
                    ("World Info", "Ctrl-I"),
                    ("Quit", "Ctrl-Q"),

                    ("Debug Overlay", "0"),
                    ("Show Block Info", "Alt"),
                    ("Pick Block", "Alt"),
                    ("Select Chunks", "Z"),
                    ("Deselect Chunks", "Alt"),
                    ("Snap Clone to Axis", "Ctrl"),
                    ("Blocks-Only Modifier", "Alt"),
                    ("Fast Increment Modifier", "Ctrl")
                ],
                "Numpad": [
                    ("Forward", "[8]"),
                    ("Back", "[5]"),
                    ("Left", "[4]"),
                    ("Right", "[6]"),
                    ("Up", "[7]"),
                    ("Down", "[1]"),
                    ("Brake", "[0]"),

                    ("Pan Up", "I"),
                    ("Pan Down", "K"),
                    ("Pan Left", "J"),
                    ("Pan Right", "L"),
                    ("Toggle View", "Tab"),
                    ("Goto Panel", "Ctrl-G"),
                    ("View Distance", "Ctrl-F"),
                    ("Toggle Renderer", "Ctrl-M"),

                    ("Swap", "[.]"),
                    ("Delete Blocks", "Delete"),
                    ("Increase Reach", "Scroll Up"),
                    ("Decrease Reach", "Scroll Down"),
                    ("Reset Reach", "Button 3"),
                    ("Export Selection", "Ctrl-E"),
                    ("Brush Line Tool", "Z"),

                    ("Rotate (Clone)", "[-]"),
                    ("Roll (Clone)", "[+]"),
                    ("Flip", "[/]"),
                    ("Mirror", "[*]"),

                    ("Rotate (Brush)", "[-]"),
                    ("Roll (Brush)", "[*]"),
                    ("Increase Brush", "[+]"),
                    ("Decrease Brush", "[/]"),

                    ("Replace Shortcut", "R"),

                    ("Select All", "Ctrl-A"),
                    ("Deselect", "Ctrl-D"),
                    ("Undo", "Ctrl-Z"),
                    ("Redo", "Ctrl-Y"),
                    ("Cut", "Ctrl-X"),
                    ("Copy", "Ctrl-C"),
                    ("Paste", "Ctrl-V"),
                    ("Take a Screenshot", "F6"),
                    ("Fast Nudge", "None"),

                    ("Long-Distance Mode", "Alt-Z"),
                    ("Fly Mode", "None"),

                    ("New World", "Ctrl-N"),
                    ("Quick Load", "Ctrl-L"),
                    ("Open", "Ctrl-O"),
                    ("Save", "Ctrl-S"),
                    ("Reload World", "Ctrl-R"),
                    ("Close World", "Ctrl-W"),
                    ("World Info", "Ctrl-I"),
                    ("Quit", "Ctrl-Q"),

                    ("Debug Overlay", "0"),
                    ("Show Block Info", "Alt"),
                    ("Pick Block", "Alt"),
                    ("Select Chunks", "Z"),
                    ("Deselect Chunks", "Alt"),
                    ("Snap Clone to Axis", "Ctrl"),
                    ("Blocks-Only Modifier", "Alt"),
                    ("Fast Increment Modifier", "Ctrl")
                ],
                "WASD Old": [
                    ("Forward", "W"),
                    ("Back", "S"),
                    ("Left", "A"),
                    ("Right", "D"),
                    ("Up", "Q"),
                    ("Down", "Z"),
                    ("Brake", "Space"),

                    ("Pan Up", "I"),
                    ("Pan Down", "K"),
                    ("Pan Left", "J"),
                    ("Pan Right", "L"),
                    ("Toggle View", "Tab"),
                    ("Goto Panel", "Ctrl-G"),
                    ("View Distance", "Ctrl-F"),
                    ("Toggle Renderer", "Ctrl-M"),

                    ("Swap", "X"),
                    ("Delete Blocks", "Delete"),
                    ("Increase Reach", "Scroll Up"),
                    ("Decrease Reach", "Scroll Down"),
                    ("Reset Reach", "Button 3"),
                    ("Export Selection", "Ctrl-E"),
                    ("Brush Line Tool", "Shift"),

                    ("Rotate (Clone)", "E"),
                    ("Roll (Clone)", "R"),
                    ("Flip", "F"),
                    ("Mirror", "G"),

                    ("Rotate (Brush)", "E"),
                    ("Roll (Brush)", "G"),
                    ("Increase Brush", "R"),
                    ("Decrease Brush", "F"),

                    ("Replace Shortcut", "R"),

                    ("Select All", "Ctrl-A"),
                    ("Deselect", "Ctrl-D"),
                    ("Undo", "Ctrl-Z"),
                    ("Redo", "Ctrl-Y"),
                    ("Cut", "Ctrl-X"),
                    ("Copy", "Ctrl-C"),
                    ("Paste", "Ctrl-V"),
                    ("Take a Screenshot", "F6"),
                    ("Fast Nudge", "Shift"),

                    ("Long-Distance Mode", "Alt-Z"),
                    ("Fly Mode", "None"),

                    ("New World", "Ctrl-N"),
                    ("Quick Load", "Ctrl-L"),
                    ("Open", "Ctrl-O"),
                    ("Save", "Ctrl-S"),
                    ("Reload World", "Ctrl-R"),
                    ("Close World", "Ctrl-W"),
                    ("World Info", "Ctrl-I"),
                    ("Quit", "Ctrl-Q"),

                    ("Debug Overlay", "0"),
                    ("Show Block Info", "Alt"),
                    ("Pick Block", "Alt"),
                    ("Select Chunks", "Ctrl"),
                    ("Deselect Chunks", "Shift"),
                    ("Snap Clone to Axis", "Shift"),
                    ("Blocks-Only Modifier", "Alt"),
                    ("Fast Increment Modifier", "Shift")
                ]}

    selectedKeyIndex = 0

    def __init__(self, mcedit):
        Dialog.__init__(self)
        #.#
        spacing = 0
        keyConfigTable = albow.TableView(nrows=30,
            columns=[albow.TableColumn("Command", 200, "l"), albow.TableColumn("Assigned Key", 150, "r")])
        keyConfigTable.num_rows = lambda: len(self.keyConfigKeys)
        keyConfigTable.row_data = self.getRowData
        keyConfigTable.row_is_selected = lambda x: x == self.selectedKeyIndex
        keyConfigTable.click_row = self.selectTableRow
        keyConfigTable.key_down = self.key_down
        keyConfigTable.key_up = self.key_up
        #.#
        self.changes = {}
        self.changesNum = False
        self.enter = 0
        self.root = None
        self.editor = None
        tableWidget = albow.Widget()
        tableWidget.add(keyConfigTable)
        tableWidget.shrink_wrap()

        self.keyConfigTable = keyConfigTable

        buttonRow = (albow.Button("Assign Key...", action=self.askAssignSelectedKey),
                    albow.Button("Done", action=self.done), albow.Button("Cancel", action=self.cancel))

        buttonRow = albow.Row(buttonRow)

        resetToDefaultRow = albow.Row((albow.Button("Reset to default", action=self.resetDefault),))

        choiceButton = mceutils.ChoiceButton(["WASD", "Arrows", "Numpad", "WASD Old"], choose=self.choosePreset)
        if config.keys.forward.get() == "Up":
            choiceButton.selectedChoice = "Arrows"
        elif config.keys.forward.get() == "[8]":
            choiceButton.selectedChoice = "Numpad"
        elif config.keys.brake.get() == "Space":
            choiceButton.selectedChoice = "WASD Old"

        self.oldChoice = choiceButton.selectedChoice

        choiceRow = albow.Row((albow.Label("Presets: "), choiceButton))
        self.choiceButton = choiceButton

        col = albow.Column((tableWidget, choiceRow, buttonRow, resetToDefaultRow), spacing=spacing, margin=0)
        self.add(col)
        self.shrink_wrap()

    def presentControls(self):
        self.present()
        self.oldChoice = self.choiceButton.selectedChoice

    def done(self):
        self.changesNum = False
        self.changes = {}
        config.save()

        self.editor.movements = [
            config.keys.left.get(),
            config.keys.right.get(),
            config.keys.forward.get(),
            config.keys.back.get(),
            config.keys.up.get(),
            config.keys.down.get()
        ]

        self.editor.cameraPan = [
            config.keys.panLeft.get(),
            config.keys.panRight.get(),
            config.keys.panUp.get(),
            config.keys.panDown.get()
        ]

        self.dismiss()

    def choosePreset(self):
        preset = self.choiceButton.selectedChoice
        keypairs = self.presets[preset]
        for configKey, k in keypairs:
            oldOne = config.keys[config.convert(configKey)].get()
            if k != oldOne:
                self.changesNum = True
                if configKey not in self.changes:
                    self.changes[configKey] = oldOne
                config.keys[config.convert(configKey)].set(k)

    def getRowData(self, i):
        if self.root is None:
            self.root = self.get_root()
        if self.editor is None:
            self.editor = self.root.editor
        configKey = self.keyConfigKeys[i]
        if self.isConfigKey(configKey):
            key = config.keys[config.convert(configKey)].get()
            try:
                key = self.editor.different_keys[key]
            except:
                pass

        else:
            key = ""
        return configKey, key

    @staticmethod
    def isConfigKey(configKey):
        return not (len(configKey) == 0 or configKey[0] == "<")

    def selectTableRow(self, i, evt):
        self.selectedKeyIndex = i
        if evt.num_clicks == 2:
            self.askAssignSelectedKey()

    def resetDefault(self):
        self.choiceButton.selectedChoice = "WASD"
        self.choosePreset()

    def cancel(self):
        if self.changesNum:
            result = albow.ask("Do you want to save your changes?", ["Save", "Don't Save", "Cancel"])
            if result == "Save":
                self.done()
            elif result == "Don't Save":
                for k in self.changes.keys():
                    config.keys[config.convert(k)].set(self.changes[k])
                self.changesNum = False
                self.changes = {}
                self.choiceButton.selectedChoice = self.oldChoice
                config.save()
                self.dismiss()
        else:
            self.dismiss()

    def key_down(self, evt):
        keyname = self.root.getKey(evt)
        if keyname == 'Escape':
            self.cancel()
        elif keyname == 'Up' and self.selectedKeyIndex > 0:
            self.selectedKeyIndex -= 1
        elif keyname == 'Down' and self.selectedKeyIndex < len(self.keyConfigKeys) - 1:
            self.selectedKeyIndex += 1
        elif keyname == 'Return':
            self.enter += 1
            self.askAssignSelectedKey()

    def key_up(self, evt):
        pass

    def askAssignSelectedKey(self):
        self.askAssignKey(self.keyConfigKeys[self.selectedKeyIndex])

    def askAssignKey(self, configKey, labelString=None):
        if not self.isConfigKey(configKey):
            self.enter = 0
            return

        panel = Panel()
        panel.bg_color = (0.5, 0.5, 0.6, 1.0)

        if labelString is None and configKey != "Fast Nudge":
            labelString = _("Press a key to assign to the action \"{0}\"\n\nPress ESC to cancel. Press Shift-ESC to unbind.").format(configKey)
        elif labelString is None:
            labelString = _("Press a key to assign to the action \"{0}\"\nNo key means right click to fast nudge.\nPress ESC to cancel. Press Shift-ESC to unbind.").format(configKey)
        label = albow.Label(labelString)
        panel.add(label)
        panel.shrink_wrap()

        def panelKeyUp(evt):
            keyname = self.root.getKey(evt)
            panel.dismiss(keyname)

        def panelMouseUp(evt):
            button = remapMouseButton(evt.button)
            if button == 3:
                keyname = "Button 3"
            elif button == 4:
                keyname = "Scroll Up"
            elif button == 5:
                keyname = "Scroll Down"
            elif button == 6:
                keyname = "Button 4"
            elif button == 7:
                keyname = "Button 5"
            if button > 2:
                panel.dismiss(keyname)

        panel.key_up = panelKeyUp
        panel.mouse_up = panelMouseUp

        keyname = panel.present()
        if keyname == "Return" and self.enter == 1:
            self.enter = 0
            self.askAssignKey(configKey)
            return True

        self.enter = 0
        if keyname != "Escape" and keyname != "Shift-Escape" and keyname not in ["Alt-F4","F1","F2","F3","F4","F5","1","2","3","4","5","6","7","8","9","Ctrl-Alt-F9","Ctrl-Alt-F10"]:
            if "Modifier" in configKey and keyname != "Ctrl" and keyname != "Alt" and keyname != "Shift":
                self.askAssignKey(configKey,
                                    _("{0} is not a modifier. Press a new key.\n\nPress ESC to cancel. Press Shift-ESC to unbind.")
                                    .format(keyname))
                return True
            if configKey in ['Down','Up','Back','Forward','Left','Right','Pan Down','Pan Up','Pan Left','Pan Right']:
                if 'Ctrl' in keyname or '-' in keyname:
                    self.askAssignKey(configKey,
                                    "Movement keys can't use Ctrl or be with modifiers. Press a new key.\n\nPress ESC to cancel. Press Shift-ESC to unbind.")
                    return True
            oldkey = config.keys[config.convert(configKey)].get()
            config.keys[config.convert(configKey)].set(keyname)
            if configKey not in self.changes:
                self.changes[configKey] = oldkey
            self.changesNum = True
        elif keyname == "Shift-Escape":
            config.keys[config.convert(configKey)].set("None")
        elif keyname != "Escape":
            self.askAssignKey(configKey,
                                    _("You can't use the key {0}. Press a new key.\n\nPress ESC to cancel. Press Shift-ESC to unbind.")
                                    .format(keyname))
            return True

        else:
            return True
