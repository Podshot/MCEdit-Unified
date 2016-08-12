from config import config
import release
import platform

from albow import AttrRef, Row, Column
from albow.resource import get_font
from albow.controls import Label
from albow.extended_widgets import HotkeyColumn
from pygame import key

from glbackground import Panel

arch = platform.architecture()[0]


class ControlPanel(Panel):
    @classmethod
    def getHeader(cls):
        header = Label("MCEdit {0} ({1})".format(release.get_version(), arch), font=get_font(18, "DejaVuSans-Bold.ttf"))
        return header

    def __init__(self, editor):
        Panel.__init__(self, name='Panel.ControlPanel')
        self.editor = editor

        self.bg_color = (0, 0, 0, 0.8)

        header = self.getHeader()
        keysColumn = [Label("")]
        buttonsColumn = [header]

        hotkeys = ([(config.keys.newWorld.get(), "Create New World",
                     editor.mcedit.createNewWorld),
                    (config.keys.quickLoad.get(), "Quick Load", editor.askLoadWorld),
                    (config.keys.open.get(), "Open...", editor.askOpenFile),
                    (config.keys.save.get(), "Save", editor.saveFile),
                    (config.keys.saveAs.get(), "Save As", editor.saveAs),
                    (config.keys.reloadWorld.get(), "Reload", editor.reload),
                    (config.keys.closeWorld.get(), "Close", editor.closeEditor),
                    (config.keys.uploadWorld.get(), "Upload to FTP Server", editor.uploadChanges),
                    (config.keys.gotoPanel.get(), "Goto", editor.showGotoPanel),
                    (config.keys.worldInfo.get(), "World Info", editor.showWorldInfo),
                    (config.keys.undo.get(), "Undo", editor.undo),
                    (config.keys.redo.get(), "Redo", editor.redo),
                    (config.keys.selectAll.get(), "Select All", editor.selectAll),
                    (config.keys.deselect.get(), "Deselect", editor.deselect),
                    (config.keys.viewDistance.get(),
                     AttrRef(editor, 'viewDistanceLabelText'), editor.swapViewDistance),
                    (config.keys.quit.get(), "Quit", editor.quit),
                   ])

        buttons = HotkeyColumn(hotkeys, keysColumn, buttonsColumn, item_spacing=2)

        sideColumn1 = editor.mcedit.makeSideColumn1()
        sideColumn2 = editor.mcedit.makeSideColumn2()
        spaceLabel = Label("")
        sideColumn = Column((sideColumn1, spaceLabel, sideColumn2))

        self.add(Row([buttons, sideColumn]))
        self.shrink_wrap()

    def key_down(self, evt):
        if key.name(evt.key) == 'escape':
            self.dismiss()
        else:
            self.editor.key_down(evt)

    def key_up(self, evt):
        self.editor.key_up(evt)

    def mouse_down(self, e):
        if e not in self:
            self.dismiss()
