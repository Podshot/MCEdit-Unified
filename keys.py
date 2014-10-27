import sys
import os
import directories
import config
import albow
import mceutils
from pygame import display, event, key, KMOD_ALT, KMOD_CTRL, KMOD_LALT, KMOD_META, KMOD_RALT, KMOD_SHIFT, mouse, \
    MOUSEMOTION
from albow.dialogs import Dialog, QuickDialog, wrapped_label
from albow import alert, ask, AttrRef, Button, Column, get_font, Grid, input_text, IntField, Menu, root, Row, \
    TableColumn, TableView, TextField, TimeField, Widget, CheckBox
from albow.controls import Label, SmallValueDisplay, ValueDisplay
from albow.translate import tr
from glbackground import Panel

ESCAPE = '\033'

def remapMouseButton(button):
    buttons = [0, 1, 3, 2, 4, 5, 6, 7]  # mouse2 is right button, mouse3 is middle
    if button < len(buttons):
        return buttons[button]
    return button
    
def getKey(evt, i=0):
    keyname = key.name(evt.key)
    if keyname == 'Enter':
            keyname = 'Return'
    if 'left' in keyname and len(keyname) > 5:
        keyname = keyname[5:]
    elif 'right' in keyname and len(keyname) > 6:
        keyname = keyname[6:]
    try:
        keyname = keyname.replace(keyname[0], keyname[0].upper(), 1)
    finally:
        if keyname == 'Meta':
            keyname = 'Ctrl'
        newKeyname = ""
        if evt.shift == True and keyname != "Shift" and i != 1:
            newKeyname += "Shift-"
        if (evt.ctrl == True or evt.cmd == True) and keyname != "Ctrl" and i != 1:
            newKeyname += "Ctrl-"
        if evt.alt == True and keyname != "Alt" and i != 1:
            newKeyname += "Alt-"
    
        keyname = newKeyname + keyname
        return keyname

class KeyConfigPanel(Dialog):
    keyConfigKeys = [
        "<Movement Controls>",
        "Forward",
        "Back",
        "Left",
        "Right",
        "Up",
        "Down",
        "Brake",
        "",
        "<Camera Controls>",
        "Pan Up",
        "Pan Down",
        "Pan Left",
        "Pan Right",
        "",
        "<Tool Controls>",
        "Rotate",
        "Roll",
        "Flip",
        "Mirror",
        "Swap",
        "Delete Blocks",
        "Line Tool",
        "Increase Reach",
        "Decrease Reach",
        "Reset Reach",
        "",
        "<Function Controls>",
        "Quit",
        "View Distance",
        "Select All",
        "Deselect",
        "Cut",
        "Copy",
        "Paste",
        "Reload World",
        "Open",
        "Quick Load",
        "Undo",
        "Save",
        "New World",
        "Close World",
        "World Info",
        "Goto Panel",
        "Export Selection",
        "Toggle Renderer",
        "",
        "Long-Distance Mode",
        "Fly Mode"
    ]

    presets = {"WASD": [
        ("Forward", "W"),
        ("Back", "S"),
        ("Left", "A"),
        ("Right", "D"),
        ("Up", "Space"),
        ("Down", "Shift"),
        ("Brake", "C"),

        ("Rotate", "E"),
        ("Roll", "R"),
        ("Flip", "F"),
        ("Mirror", "G"),
        ("Swap", "X"),
        ("Increase Reach", "Scroll Up"),
        ("Decrease Reach", "Scroll Down"),
        ("Reset Reach", "Button 3"),
        ("Delete Blocks", "Delete"),
        
        ("Quit", "Ctrl-Q"),
        ("View Distance", "Ctrl-F"),
        ("Select All", "Ctrl-A"),
        ("Deselect", "Ctrl-D"),
        ("Cut", "Ctrl-X"),
        ("Copy", "Ctrl-C"),
        ("Paste", "Ctrl-V"),
        ("Reload World", "Ctrl-R"),
        ("Open", "Ctrl-O"),
        ("Quick Load", "Ctrl-L"),
        ("Undo", "Ctrl-Z"),
        ("Save", "Ctrl-S"),
        ("New World", "Ctrl-N"),
        ("Close World", "Ctrl-W"),
        ("World Info", "Ctrl-I"),
        ("Goto Panel", "Ctrl-G"),
        ("Export Selection", "Ctrl-E"),
        ("Toggle Renderer", "Ctrl-M"),
        
        ("Long-Distance Mode", "Alt-Z"),
        ("Fly Mode", "None")
    ],
               "Arrows": [
                   ("Forward", "Up"),
                   ("Back", "Down"),
                   ("Left", "Left"),
                   ("Right", "Right"),
                   ("Up", "Page Up"),
                   ("Down", "Page Down"),
                   ("Brake", "Space"),

                   ("Rotate", "Home"),
                   ("Roll", "End"),
                   ("Flip", "Insert"),
                   ("Mirror", "Delete"),
                   ("Swap", "\\"),
                   ("Increase Reach", "Scroll Up"),
                   ("Decrease Reach", "Scroll Down"),
                   ("Reset Reach", "Button 3"),
                   ("Delete Blocks", "Backspace"),
                   
                   ("Quit", "Ctrl-Q"),
                   ("View Distance", "Ctrl-F"),
                   ("Select All", "Ctrl-A"),
                   ("Deselect", "Ctrl-D"),
                   ("Cut", "Ctrl-X"),
                   ("Copy", "Ctrl-C"),
                   ("Paste", "Ctrl-V"),
                   ("Reload World", "Ctrl-R"),
                   ("Open", "Ctrl-O"),
                   ("Quick Load", "Ctrl-L"),
                   ("Undo", "Ctrl-Z"),
                   ("Save", "Ctrl-S"),
                   ("New World", "Ctrl-N"),
                   ("Close World", "Ctrl-W"),
                   ("World Info", "Ctrl-I"),
                   ("Goto Panel", "Ctrl-G"),
                   ("Export Selection", "Ctrl-E"),
                   ("Toggle Renderer", "Ctrl-M"),
                   
                   ("Long-Distance Mode", "Alt-Z"),
                   ("Fly Mode", "None")
               ],
               "Numpad": [
                   ("Forward", "[8]"),
                   ("Back", "[5]"),
                   ("Left", "[4]"),
                   ("Right", "[6]"),
                   ("Up", "[7]"),
                   ("Down", "[1]"),
                   ("Brake", "[0]"),

                   ("Rotate", "[-]"),
                   ("Roll", "[+]"),
                   ("Flip", "[/]"),
                   ("Mirror", "[*]"),
                   ("Swap", "[.]"),
                   ("Increase Reach", "Scroll Up"),
                   ("Decrease Reach", "Scroll Down"),
                   ("Reset Reach", "Button 3"),
                   ("Delete Blocks", "Delete"),
                   
                   ("Quit", "Ctrl-Q"),
                   ("View Distance", "Ctrl-F"),
                   ("Select All", "Ctrl-A"),
                   ("Deselect", "Ctrl-D"),
                   ("Cut", "Ctrl-X"),
                   ("Copy", "Ctrl-C"),
                   ("Paste", "Ctrl-V"),
                   ("Reload World", "Ctrl-R"),
                   ("Open", "Ctrl-O"),
                   ("Quick Load", "Ctrl-L"),
                   ("Undo", "Ctrl-Z"),
                   ("Save", "Ctrl-S"),
                   ("New World", "Ctrl-N"),
                   ("Close World", "Ctrl-W"),
                   ("World Info", "Ctrl-I"),
                   ("Goto Panel", "Ctrl-G"),
                   ("Export Selection", "Ctrl-E"),
                   ("Toggle Renderer", "Ctrl-M"),
                   
                   ("Long-Distance Mode", "Alt-Z"),
                   ("Fly Mode", "None")
               ]}

    selectedKeyIndex = 0

    def __init__(self):
        Dialog.__init__(self)
        keyConfigTable = albow.TableView(nrows=30,
            columns=[albow.TableColumn("Command", 200, "l"), albow.TableColumn("Assigned Key", 150, "r")])
        keyConfigTable.num_rows = lambda: len(self.keyConfigKeys)
        keyConfigTable.row_data = self.getRowData
        keyConfigTable.row_is_selected = lambda x: x == self.selectedKeyIndex
        keyConfigTable.click_row = self.selectTableRow
        keyConfigTable.key_down = self.key_down
        self.changes = {}
        self.changesNum = 0
        tableWidget = albow.Widget()
        tableWidget.add(keyConfigTable)
        tableWidget.shrink_wrap()

        self.keyConfigTable = keyConfigTable

        buttonRow = (albow.Button("Assign Key...", action=self.askAssignSelectedKey),
                     albow.Button("Done", action=self.done))

        buttonRow = albow.Row(buttonRow)

        choiceButton = mceutils.ChoiceButton(["WASD", "Arrows", "Numpad"], choose=self.choosePreset)
        if config.config.get("Keys", "Forward") == "Up":
            choiceButton.selectedChoice = "Arrows"
        if config.config.get("Keys", "Forward") == "[8]":
            choiceButton.selectedChoice = "Numpad"

        choiceRow = albow.Row((albow.Label("Presets: "), choiceButton))
        self.choiceButton = choiceButton

        col = albow.Column((tableWidget, choiceRow, buttonRow))
        self.add(col)
        self.shrink_wrap()

    def done(self):
        self.changesNum = 0
        self.changes = {}
        config.saveConfig()
        self.dismiss()
    
    def choosePreset(self):
        preset = self.choiceButton.selectedChoice
        keypairs = self.presets[preset]
        for configKey, key in keypairs:
            config.config.set("Keys", configKey, key)

    def getRowData(self, i):
        configKey = self.keyConfigKeys[i]
        if self.isConfigKey(configKey):
            key = config.config.get("Keys", configKey)
            if key == 'mouse3':
                key = 'Button 3'
                config.config.set("Keys", configKey, "Button 3")
            elif key == 'mouse4':
                key = 'Scroll Up'
                config.config.set("Keys", configKey, "Scroll Up")
            elif key == 'mouse5':
                key = 'Scroll Down'
                config.config.set("Keys", configKey, "Scroll Down")
            elif key == 'mouse6':
                key = 'Button 4'
                config.config.set("Keys", configKey, "Button 4")
            elif key == 'mouse7':
                key = 'Button 5'
                config.config.set("Keys", configKey, "Button 5")
            
        else:
            key = ""
        return configKey, key

    def isConfigKey(self, configKey):
        return not (len(configKey) == 0 or configKey[0] == "<")

    def selectTableRow(self, i, evt):
        self.selectedKeyIndex = i
        if evt.num_clicks == 2:
            self.askAssignSelectedKey()
            
    def key_down(self, evt):
        keyname = getKey(evt)
        if keyname == 'Escape':
            if self.changesNum >= 1:
                result = albow.ask("Do you want to save your changes?", ["Save", "Don't Save", "Cancel"])
                if result == "Save":
                    self.done()
                elif result == "Don't Save":
                    for key in self.changes.keys():
                        config.config.set("Keys", key, self.changes[key])
                    self.changesNum = 0
                    self.changes = {}
                    self.dismiss()
            else:
                self.dismiss()

    def askAssignSelectedKey(self):
        self.askAssignKey(self.keyConfigKeys[self.selectedKeyIndex])

    def askAssignKey(self, configKey, labelString=None):
        if not self.isConfigKey(configKey):
            return

        panel = Panel()
        panel.bg_color = (0.5, 0.5, 0.6, 1.0)

        if labelString is None:
            labelString = tr("Press a key to assign to the action \"{0}\"\n\nPress ESC to cancel. Press Shift-ESC to unbind.").format(configKey)
        label = albow.Label(labelString)
        panel.add(label)
        panel.shrink_wrap()

        def panelKeyUp(evt):
            keyname = getKey(evt)
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
        if keyname != "Escape" and keyname != "Shift-Escape":
            occupiedKeys = [(v, k) for (k, v) in config.config.items("Keys") if config.getNewKey(v) == keyname and k != configKey.lower()]
            oldkey = config.config.get("Keys", configKey)
            config.config.set("Keys", configKey, keyname)
            self.changes[configKey] = oldkey
            self.changesNum = 1
            for keyname, setting in occupiedKeys:
                settings = setting.split(' ')
                newSettings = []
                for set in settings:
                    newSettings.append(set[0].upper() + set[1:])
                setting = ' '.join(newSettings)
                if self.askAssignKey(setting,
                                     tr("The key {0} is no longer bound to {1}. "
                                     "Press a new key for the action \"{1}\"\n\n"
                                     "Press ESC to cancel. Press Shift-ESC to unbind.")
                                     .format(keyname, setting)):
                    config.config.set("Keys", configKey, oldkey)
                    self.changes[configKey] = keyname
                    return True 
        elif keyname == "Shift-Escape":
            config.config.set("Keys", configKey, "None")
        else:
            return True