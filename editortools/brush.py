"""Copyright (c) 2010-2012 David Rio Vierra

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."""

#Modified by D.C.-G. for translation purposes
import imp
import traceback
import copy
from OpenGL import GL
import datetime
import os
import sys
from albow import AttrRef, ItemRef, Button, ValueDisplay, Row, Label, ValueButton, Column, IntField, FloatField, alert, CheckBox, TextFieldWrapped, TableView, TableColumn
from albow.dialogs import Dialog
import albow.translate
_ = albow.translate._
import ast
import bresenham
from clone import CloneTool
import collections
from config import config
import directories
from editortools.blockpicker import BlockPicker
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from editortools.tooloptions import ToolOptions
from glbackground import Panel, GLBackground
from glutils import gl
import itertools
from albow.root import get_root
import leveleditor
import logging
from mceutils import alertException, drawTerrainCuttingWire
from albow import ChoiceButton, CheckBoxLabel, showProgress, IntInputRow, FloatInputRow
import mcplatform
from numpy import newaxis
import numpy
from operation import Operation, mkundotemp
from os.path import basename
from pymclevel import block_fill, BoundingBox, materials, blockrotation
import pymclevel
from pymclevel.mclevelbase import exhaust
from pymclevel.entity import TileEntity
import random
from __builtin__ import __import__
from locale import getdefaultlocale
DEF_ENC = getdefaultlocale()[1]
if DEF_ENC is None:
    DEF_ENC = "UTF-8"

log = logging.getLogger(__name__)


class BrushOperation(Operation):
    def __init__(self, tool):
        super(BrushOperation, self).__init__(tool.editor, tool.editor.level)
        self.tool = tool
        self.points = tool.draggedPositions
        self.options = tool.options
        self.brushMode = tool.brushMode
        boxes = [self.tool.getDirtyBox(p, self.tool) for p in self.points]
        self._dirtyBox = reduce(lambda a, b: a.union(b), boxes)
        self.canUndo = False

    def dirtyBox(self):
        return self._dirtyBox

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return
        if recordUndo:
            self.canUndo = True
            self.undoLevel = self.extractUndo(self.level, self._dirtyBox)

        def _perform():
            yield 0, len(self.points), _("Applying {0} brush...").format(_(self.brushMode.displayName))
            if hasattr(self.brushMode, 'apply'):
                for i, point in enumerate(self.points):
                    f = self.brushMode.apply(self.brushMode, self, point)
                    if hasattr(f, "__iter__"):
                        for progress in f:
                            yield progress
                    else:
                        yield i, len(self.points), _("Applying {0} brush...").format(_(self.brushMode.displayName))
            if hasattr(self.brushMode, 'applyToChunkSlices'):
                for j, cPos in enumerate(self._dirtyBox.chunkPositions):
                    if not self.level.containsChunk(*cPos):
                        continue
                    chunk = self.level.getChunk(*cPos)
                    for i, point in enumerate(self.points):
                        brushBox = self.tool.getDirtyBox(point, self.tool)
                        brushBoxThisChunk, slices = chunk.getChunkSlicesForBox(brushBox)
                        f = self.brushMode.applyToChunkSlices(self.brushMode, self, chunk, slices, brushBox, brushBoxThisChunk)
                        if brushBoxThisChunk.volume == 0:
                            f = None
                        if hasattr(f, "__iter__"):
                            for progress in f:
                                yield progress
                        else:
                            yield j * len(self.points) + i, len(self.points) * self._dirtyBox.chunkCount, _("Applying {0} brush...").format(_(self.brushMode.displayName))
                    chunk.chunkChanged()
        if len(self.points) > 10:
            showProgress("Performing brush...", _perform(), cancel=True)
        else:
            exhaust(_perform())


class BrushPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self, name='Panel.BrushPanel')
        self.tool = tool
        """
        presets, modeRow and styleRow are always created, no matter
        what brush is selected. styleRow can be disabled by putting disableStyleButton = True
        in the brush file.
        """
        presets = self.createPresetRow()

        self.brushModeButtonLabel = Label("Mode:")
        self.brushModeButton = ChoiceButton(sorted([mode for mode in tool.brushModes]),
                                       width=150,
                                       choose=self.brushModeChanged,
                                       doNotTranslate=True,
                                       )
        modeRow = Row([self.brushModeButtonLabel, self.brushModeButton])

        self.brushStyleButtonLabel = Label("Style:")
        self.brushStyleButton = ValueButton(ref=ItemRef(self.tool.options, "Style"),
                                            action=self.tool.swapBrushStyles,
                                            width=150)

        styleRow = Row([self.brushStyleButtonLabel, self.brushStyleButton])
        self.brushModeButton.selectedChoice = self.tool.selectedBrushMode
        optionsColumn = []
        optionsColumn.extend([presets, modeRow])
        if not getattr(tool.brushMode, 'disableStyleButton', False):
            optionsColumn.append(styleRow)
        """
        We're going over all options in the selected brush module, and making
        a field for all of them.
        """
        for r in tool.brushMode.inputs:
            row = []
            for key, value in r.iteritems():
                field = self.createField(key, value)
                row.append(field)
            row = Row(row)
            optionsColumn.append(row)
        if getattr(tool.brushMode, 'addPasteButton', False):
            importButton = Button("Import", action=tool.importPaste)
            importRow = Row([importButton])
            optionsColumn.append(importRow)
        optionsColumn = Column(optionsColumn, spacing=0)
        self.add(optionsColumn)
        self.shrink_wrap()

    def createField(self, key, value):
        """
        Creates a field matching the input type.
        :param key, key to store the value in, also the name of the label if type is float or int.
        :param value, default value for the field.
        """
        if hasattr(self.tool.brushMode, "trn"):
            doNotTranslate = True
        else:
            doNotTranslate = False
        type = value.__class__.__name__
        mi = 0
        ma = 100
        if key in ('W', 'H', 'L'):
            reference = AttrRef(self.tool, key)
        else:
            reference = ItemRef(self.tool.options, key)
        if type == 'tuple':
            type = value[0].__class__.__name__
            mi = value[1]
            ma = value[2]
        if type == 'Block':
            if key not in self.tool.recentBlocks:
                self.tool.recentBlocks[key] = []
            wcb = getattr(self.tool.brushMode, 'wildcardBlocks', [])
            aw = False
            if key in wcb:
                aw = True
            field = BlockButton(self.tool.editor.level.materials,
                                ref=reference,
                                recentBlocks=self.tool.recentBlocks[key],
                                allowWildcards=aw
                                )
        elif type == 'instancemethod':
            field = Button(key, action=value)
        else:
            if doNotTranslate:
                key = self.tool.brushMode.trn._(key)
                value = self.tool.brushMode.trn._(value)
            if type == 'int':
                field = IntInputRow(key, ref=reference, width=50, min=mi, max=ma, doNotTranslate=doNotTranslate)
            elif type == 'float':
                field = FloatInputRow(key, ref=reference, width=50, min=mi, max=ma, doNotTranslate=doNotTranslate)
            elif type == 'bool':
                field = CheckBoxLabel(key, ref=reference, doNotTranslate=doNotTranslate)
            elif type == 'str':
                field = Label(value, doNotTranslate=doNotTranslate)
            else:
                print type
                field = None
        return field

    def brushModeChanged(self):
        """
        Called on selecting a brushMode, sets it in BrushTool as well.
        """
        self.tool.selectedBrushMode = self.brushModeButton.selectedChoice
        self.tool.brushMode = self.tool.brushModes[self.tool.selectedBrushMode]
        self.tool.saveBrushPreset('__temp__')
        self.tool.setupPreview()
        self.tool.showPanel()

    @staticmethod
    def getBrushFileList():
        """
        Returns a list of strings of all .preset files in the brushes directory.
        """
        list = []
        presetdownload = os.listdir(directories.brushesDir)
        for p in presetdownload:
            if p.endswith('.preset'):
                list.append(os.path.splitext(p)[0])
        if '__temp__' in list:
            list.remove('__temp__')
        return list

    def createPresetRow(self):
        """
        Creates the brush preset widget, called by BrushPanel when creating the panel.
        """
        self.presets = ["Load Preset"]
        self.presets.extend(self.getBrushFileList())
        self.presets.append('Remove Presets')

        self.presetListButton = ChoiceButton(self.presets, width=100, choose=self.presetSelected)
        self.presetListButton.selectedChoice = "Load Preset"
        self.saveButton = Button("Save as Preset", action=self.openSavePresetDialog)

        presetListButtonRow = Row([self.presetListButton])
        saveButtonRow = Row([self.saveButton])
        row = Row([presetListButtonRow, saveButtonRow])
        widget = GLBackground()
        widget.bg_color = (0.8, 0.8, 0.8, 0.8)
        widget.add(row)
        widget.shrink_wrap()
        widget.anchor = "whtr"
        return widget

    def openSavePresetDialog(self):
        """
        Opens up a dialgo to input the name of the to save Preset.
        """
        panel = Dialog()
        label = Label("Preset Name:")
        nameField = TextFieldWrapped(width=200)

        def okPressed():
            panel.dismiss()
            name = nameField.value

            if name in ['Load Preset', 'Remove Presets', '__temp__']:
                alert("That preset name is reserved. Try pick another preset name.")
                return

            for p in ['<','>',':','\"', '/', '\\', '|', '?', '*', '.']:
                if p in name:
                    alert('Invalid character in file name')
                    return

            self.tool.saveBrushPreset(name)
            self.tool.showPanel()

        okButton = Button("OK", action=okPressed)
        cancelButton = Button("Cancel", action=panel.dismiss)
        namerow = Row([label,nameField])
        buttonRow = Row([okButton,cancelButton])

        panel.add(Column([namerow, buttonRow]))
        panel.shrink_wrap()
        panel.present()

    def removePreset(self):
        """
        Brings up a panel to remove presets.
        """
        panel = Dialog()
        p = self.getBrushFileList()
        if not p:
            alert('No presets saved')
            return

        def okPressed():
            panel.dismiss()
            name = p[presetTable.selectedIndex] + ".preset"
            os.remove(os.path.join(directories.brushesDir, name))
            self.tool.showPanel()

        def selectTableRow(i, evt):
            presetTable.selectedIndex = i
            if evt.num_clicks == 2:
                okPressed()

        presetTable = TableView(columns=(TableColumn("", 200),))
        presetTable.num_rows = lambda: len(p)
        presetTable.row_data = lambda i: (p[i],)
        presetTable.row_is_selected = lambda x: x == presetTable.selectedIndex
        presetTable.click_row = selectTableRow
        presetTable.selectedIndex = 0
        choiceCol = Column((ValueDisplay(width=200, get_value=lambda:"Select preset to delete"), presetTable))
        okButton = Button("OK", action=okPressed)
        cancelButton = Button("Cancel", action=panel.dismiss)
        row = Row([okButton,cancelButton])
        panel.add(Column((choiceCol, row)))
        panel.shrink_wrap()
        panel.present()

    def presetSelected(self):
        """
        Called ons selecting item on Load Preset, to check if remove preset is selected. Calls removePreset if true, loadPreset(name) otherwise.
        """
        choice = self.presetListButton.selectedChoice
        if choice == 'Remove Presets':
            self.removePreset()
        elif choice == 'Load Preset':
            return
        else:
            self.tool.loadBrushPreset(choice)
        self.tool.showPanel()


class BrushToolOptions(ToolOptions):
    def __init__(self, tool):
        ToolOptions.__init__(self, name='Panel.BrushToolOptions')
        alphaField = FloatField(ref=ItemRef(tool.settings, 'brushAlpha'), min=0.0, max=1.0, width=60)
        alphaField.increment = 0.1
        alphaRow = Row((Label("Alpha: "), alphaField))
        autoChooseCheckBox = CheckBoxLabel("Choose Block Immediately",
                                            ref=ItemRef(tool.settings, "chooseBlockImmediately"),
                                            tooltipText="When the brush tool is chosen, prompt for a block type.")

        updateOffsetCheckBox = CheckBoxLabel("Reset Distance When Brush Size Changes",
                                            ref=ItemRef(tool.settings, "updateBrushOffset"),
                                            tooltipText="Whenever the brush size changes, reset the distance to the brush blocks.")

        col = Column((Label("Brush Options"), alphaRow, autoChooseCheckBox, updateOffsetCheckBox, Button("OK", action=self.dismiss)))
        self.add(col)
        self.shrink_wrap()
        return


class BrushTool(CloneTool):
    tooltipText = "Brush\nRight-click for options"
    toolIconName = "brush"

    options = {
    'Style':'Round',
    }
    settings = {
    'chooseBlockImmediately':False,
    'updateBrushOffset':False,
    'brushAlpha':1.0,
    }
    brushModes = {}
    recentBlocks = {}
    previewDirty = False
    cameraDistance = EditorTool.cameraDistance
    optionBackup = None

    def __init__(self, *args):
        """
        Called on starting mcedit.
        Creates some basic variables.
        """
        CloneTool.__init__(self, *args)
        self.optionsPanel = BrushToolOptions(self)
        self.recentFillBlocks = []
        self.recentReplaceBlocks = []
        self.draggedPositions = []
        self.pickBlockKey = False
        self.lineToolKey = False
        self.lastPosition = None
        self.root = get_root()

    """
    Property reticleOffset.
    Used to determine the distance between the block the cursor is pointing at, and the center of the brush.
    Increased by scrolling up, decreased by scrolling down (default keys)
    """

    _reticleOffset = 1

    @property
    def reticleOffset(self):
        if getattr(self.brushMode, 'draggableBrush', True):
            return self._reticleOffset
        return 0

    @reticleOffset.setter
    def reticleOffset(self, val):
        self._reticleOffset = val

    """
    Properties W,H,L. Used to reset the Brush Preview whenever they change.
    """
    @property
    def W(self):
        return self.options['W']

    @W.setter
    def W(self, val):
        self.options['W'] = val
        self.setupPreview()

    @property
    def H(self):
        return self.options['H']

    @H.setter
    def H(self, val):
        self.options['H'] = val
        self.setupPreview()

    @property
    def L(self):
        return self.options['L']

    @L.setter
    def L(self, val):
        self.options['L'] = val
        self.setupPreview()

    """
    Statustext property, rendered in the black line at the bottom of the screen.
    """
    @property
    def statusText(self):
        return _("Click and drag to place blocks. Pick block: {P}-Click. Increase: {R}. Decrease: {F}. Rotate: {E}. Roll: {G}. Mousewheel to adjust distance.").format(
            P=config.keys.pickBlock.get(),
            R=config.keys.increaseBrush.get(),
            F=config.keys.decreaseBrush.get(),
            E=config.keys.rotateBrush.get(),
            G=config.keys.rollBrush.get(),
            )

    def toolEnabled(self):
        """
        Brush tool is always enabled on the toolbar.
        It does not need a selection.
        """
        return True

    def setupBrushModes(self):
        """
        Makes a dictionary of all mode names and their corresponding module. If no name is found, it uses the name of the file.
        Creates dictionary entries for all inputs in import brush modules.
        Called by toolSelected
        """
        self.importedBrushModes = self.importBrushModes()
        for m in self.importedBrushModes:
            if m.displayName:
                if hasattr(m, "trn"):
                    displayName = m.trn._(m.displayName)
                else:
                    displayName = _(m.displayName)
                self.brushModes[displayName] = m
            else:
                self.brushModes[m.__name__] = m
            if m.inputs:
                for r in m.inputs:
                    for key in r:
                        if not hasattr(self.options, key):
                            if type(r[key]) == tuple:
                                self.options[key] = r[key][0]
                            elif type(r[key]) != str:
                                self.options[key] = r[key]
            if not hasattr(self.options, 'Minimum Spacing'):
                self.options['Minimum Spacing'] = 1
        self.renderedBlock = None

    def importBrushModes(self):
        """
        Imports all Stock Brush Modes from their files.
        Called by setupBrushModes
        """
        sys.path.append(os.path.join(directories.getDataDir(), u'stock-filters')) ### Why? Is 'stock-filters' needed here? Should'nt be 'stoch-brushes'?
        modes = [self.tryImport(x[:-3], 'stock-brushes') for x in filter(lambda x: x.endswith(".py"), os.listdir(os.path.join(directories.getDataDir(), u'stock-brushes')))]
        cust_modes = [self.tryImport(x[:-3], directories.brushesDir) for x in filter(lambda x: x.endswith(".py"), os.listdir(directories.brushesDir))]
        modes = filter(lambda m: (hasattr(m, "apply") or hasattr(m, 'applyToChunkSlices')) and hasattr(m, 'inputs'), modes)
        modes.extend(filter(lambda m: (hasattr(m, "apply") or hasattr(m, 'applyToChunkSlices')) and hasattr(m, 'inputs') and hasattr(m, 'trn'), cust_modes))
        return modes

    def tryImport(self, name, dir):
        """
        Imports a brush module. Called by importBrushModules
        :param name, name of the module to import.
        """
        if dir != "stock-brushes":
            embeded = False
        else:
            embeded = True
        try:
            path = os.path.join(dir, (name + ".py"))
            if type(path) == unicode and DEF_ENC != "UTF-8":
                path = path.encode(DEF_ENC)
            globals()[name] = m = imp.load_source(name, path)
            if not embeded:
                old_trn_path = albow.translate.getLangPath()
                if "trn" in sys.modules.keys():
                    del sys.modules["trn"]
                import albow.translate as trn
                trn_path = os.path.join(directories.brushesDir, name)
                if os.path.exists(trn_path):
                    trn.setLangPath(trn_path)
                    trn.buildTranslation(config.settings.langCode.get())
                m.trn = trn
                albow.translate.setLangPath(old_trn_path)
                albow.translate.buildTranslation(config.settings.langCode.get())
                self.editor.mcedit.set_update_ui(True)
                self.editor.mcedit.set_update_ui(False)
            m.materials = self.editor.level.materials
            m.tool = self
            m.createInputs(m)
            return m
        except Exception, e:
            print traceback.format_exc()
            alert(_(u"Exception while importing brush mode {}. See console for details.\n\n{}").format(name, e))
            return object()

    def toolSelected(self):
        """
        Applies options of BrushToolOptions.
        It then imports all brush modes from their files,
        sets up the panel,
        and sets up the brush preview.
        Called on pressing "2" or pressing the brush button in the hotbar when brush is not selected.
        """
        self.setupBrushModes()
        self.selectedBrushMode = [m for m in self.brushModes][0]
        self.brushMode = self.brushModes[self.selectedBrushMode]
        if self.settings['chooseBlockImmediately']:
            key = getattr(self.brushMode, 'mainBlock', 'Block')
            wcb = getattr(self.brushMode, 'wildcardBlocks', [])
            aw = False
            if key in wcb:
                aw = True
            blockPicker = BlockPicker(self.options[key], self.editor.level.materials, allowWildcards=aw)
            if blockPicker.present():
                    self.options[key] = blockPicker.blockInfo
        if self.settings['updateBrushOffset']:
            self.reticleOffset = self.offsetMax()
        self.resetToolDistance()
        if os.path.isfile(os.path.join(directories.brushesDir, '__temp__.preset')):
            self.loadBrushPreset('__temp__')
        else:
            print 'No __temp__ file found.'
            self.showPanel()
            self.setupPreview()
        if getattr(self.brushMode, 'addPasteButton', False):
            stack = self.editor.copyStack
            if len(stack) == 0:
                self.importPaste()
            else:
                self.loadLevel(stack[0])

    def saveBrushPreset(self, name):
        """
        Saves current brush presets in a file name.preset
        :param name, name of the file to store the preset in.
        """
        optionsToSave = {}
        for key in self.options:
            if self.options[key].__class__.__name__ == 'Block':
                optionsToSave[key + 'blockID'] = self.options[key].ID
                optionsToSave[key + 'blockData'] = self.options[key].blockData
                saveList = []
                if key in self.recentBlocks:
                    blockList = self.recentBlocks[key]
                    for b in blockList:
                        saveList.append((b.ID, b.blockData))
                    optionsToSave[key + 'recentBlocks'] = saveList
            elif self.options[key].__class__.__name__ == 'instancemethod':
                continue
            else:
                optionsToSave[key] = self.options[key]
        optionsToSave["Mode"] = getattr(self, 'selectedBrushMode', 'Fill')
        name += ".preset"
        f = open(os.path.join(directories.brushesDir, name), "w")
        f.write(repr(optionsToSave))

    def loadBrushPreset(self, name):
        """
        Loads a brush preset name.preset
        :param name, name of the preset to load.
        """
        name += '.preset'
        try:
            f = open(os.path.join(directories.brushesDir, name), "r")
        except:
            alert('Exception while trying to load preset. See console for details.')
        loadedBrushOptions = ast.literal_eval(f.read())

        brushMode = self.brushModes.get(loadedBrushOptions.get("Mode", None), None)
        if brushMode is not None:
            self.selectedBrushMode = loadedBrushOptions["Mode"]
            self.brushMode = self.brushModes[self.selectedBrushMode]
            for key in loadedBrushOptions:
                if key.endswith('blockID'):
                    key = key[:-7]
                    self.options[key] = self.editor.level.materials.blockWithID(loadedBrushOptions[key + 'blockID'], loadedBrushOptions[key+ 'blockData'])
                    if key + 'recentBlocks' in loadedBrushOptions:
                        list = []
                        blockList = loadedBrushOptions[key + 'recentBlocks']
                        for b in blockList:
                            list.append(self.editor.level.materials.blockWithID(b[0], b[1]))
                        self.recentBlocks[key] = list
                elif key.endswith('blockData'):
                    continue
                elif key.endswith('recentBlocks'):
                    continue
#                elif key == "Mode":
#                    self.selectedBrushMode = loadedBrushOptions[key]
#                    self.brushMode = self.brushModes[self.selectedBrushMode]
                else:
                    self.options[key] = loadedBrushOptions[key]
        self.showPanel()
        self.setupPreview()

    @property
    def worldTooltipText(self):
        """
        Displays the corresponding tooltip if ALT is pressed.
        Called by leveleditor every tick.
        """
        if self.pickBlockKey:
            try:
                if self.editor.blockFaceUnderCursor is None:
                    return
                pos = self.editor.blockFaceUnderCursor[0]
                blockID = self.editor.level.blockAt(*pos)
                blockdata = self.editor.level.blockDataAt(*pos)
                return _("Click to use {0} ({1}:{2})").format(self.editor.level.materials.names[blockID][blockdata], blockID, blockdata)
            except Exception, e:
                return repr(e)

    def keyDown(self, evt):
        """
        Triggered on pressing a key,
        sets the corresponding variable to True
        """
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        if keyname == config.keys.pickBlock.get():
            self.pickBlockKey = True
        if keyname == config.keys.brushLineTool.get():
            self.lineToolKey = True

    def keyUp(self, evt):
        """
        Triggered on releasing a key,
        sets the corresponding variable to False
        """
        keyname = evt.dict.get('keyname', None) or self.root.getKey(evt)
        if keyname == config.keys.pickBlock.get():
            self.pickBlockKey = False
        if keyname == config.keys.brushLineTool.get():
            self.lineToolKey = False
            self.draggedPositions = []

    @alertException
    def mouseDown(self, evt, pos, direction):
        """
        Called on pressing the mouseButton.
        Sets bllockButton if pickBlock is True.
        Also starts dragging.
        """
        if self.pickBlockKey:
            id = self.editor.level.blockAt(*pos)
            data = self.editor.level.blockDataAt(*pos)
            key = getattr(self.brushMode, 'mainBlock', 'Block')
            self.options[key] = self.editor.level.materials.blockWithID(id, data)
            self.showPanel()
        else:
            self.draggedDirection = direction
            point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
            self.dragLineToPoint(point)

    @alertException
    def mouseDrag(self, evt, pos, _dir):
        """
        Called on dragging the mouse.
        Adds the current point to draggedPositions.
        """

        if getattr(self.brushMode, 'draggableBrush', True):
            if len(self.draggedPositions):  #If we're dragging the mouse
                self.lastPosition = lastPoint = self.draggedPositions[-1]
                direction = self.draggedDirection
                point = [p + d * self.reticleOffset for p, d in zip(pos, direction)]
                if any([abs(a - b) >= self.options['Minimum Spacing']
                        for a, b in zip(point, lastPoint)]):
                    self.dragLineToPoint(point)

    def dragLineToPoint(self, point):
        """
        Calculates the new point and adds it to self.draggedPositions.
        Called by mouseDown and mouseDrag
        """
        if getattr(self.brushMode, 'draggableBrush', True):
            if self.lineToolKey:
                if len(self.draggedPositions):
                    points = bresenham.bresenham(self.draggedPositions[0], point)
                    self.draggedPositions = [self.draggedPositions[0]]
                    self.draggedPositions.extend(points[::self.options['Minimum Spacing']][1:])
                elif self.lastPosition is not None:
                    points = bresenham.bresenham(self.lastPosition, point)
                    self.draggedPositions.extend(points[::self.options['Minimum Spacing']][1:])
            else:
                self.draggedPositions.append(point)
        else:
            self.draggedPositions = [point]

    @alertException
    def mouseUp(self, evt, pos, direction):
        """
        Called on releasing the Mouse Button.
        Creates Operation object and passes it to the leveleditor.
        """
        if 0 == len(self.draggedPositions):
            return
        op = BrushOperation(self)
        self.editor.addOperation(op)
        if op.canUndo:
            self.editor.addUnsavedEdit()
        self.editor.invalidateBox(op.dirtyBox())
        self.lastPosition = self.draggedPositions[-1]
        self.draggedPositions = []

    def swapBrushStyles(self):
        """
        Swaps the BrushStyleButton to the next Brush Style.
        Called by pressing BrushStyleButton in panel.
        """
        styles = ["Square","Round","Diamond"]
        brushStyleIndex = styles.index(self.options["Style"]) + 1
        brushStyleIndex %= 3
        self.options["Style"] = styles[brushStyleIndex]
        self.setupPreview()

    def toolReselected(self):
        """
        Called on reselecting the brush.
        Makes a blockpicker show up for the Main Block of the brush mode.
        """
        if not self.panel:
            self.toolSelected()
        key = getattr(self.brushMode, 'mainBlock', 'Block')
        wcb = getattr(self.brushMode, 'wildcardBlocks', [])
        aw = False
        if key in wcb:
            aw = True
        blockPicker = BlockPicker(self.options[key], self.editor.level.materials, allowWildcards=aw)
        if blockPicker.present():
            self.options[key] = blockPicker.blockInfo
        self.setupPreview()

    def showPanel(self):
        """
        Removes old panels.
        Makes new panel instance and add it to leveleditor.
        """
        if self.panel:
            self.panel.parent.remove(self.panel)
        panel = BrushPanel(self)
        panel.centery = self.editor.centery
        panel.left = self.editor.left
        panel.anchor = "lwh"
        self.panel = panel
        self.editor.add(panel)

    def offsetMax(self):
        """
        Sets the Brush Offset (space between face the cursor is pointing at and center of brush.
        Called by toolSelected if updateBrushOffset is Checked in BrushOptions
        """
        brushSizeOffset = max(self.getBrushSize()) + 1
        return max(1, (0.5 * brushSizeOffset))

    def resetToolDistance(self):
        """
        Resets the distance of the brush in right-click mode, appropriate to the size of the brush.
        """
        distance = 6 + max(self.getBrushSize()) * 1.25
        self.editor.cameraToolDistance = distance

    def resetToolReach(self):
        """
        Resets reticleOffset or tooldistance in right-click mode.
        """
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            self.resetToolDistance()
        else:
            self.reticleOffset = self.offsetMax()
        return True

    def getBrushSize(self):
        """
        Returns an array of the sizes of the brush.
        Called by methods that need the size of the brush like createBrushMask
        """
        size = []
        if getattr(self.brushMode, 'disableStyleButton', False):
            return 1,1,1
        for dim in ['W','H','L']:
            size.append(self.options[dim])
        return size

    @alertException
    def setupPreview(self):
        """
        Creates the Brush Preview
        Passes it as a FakeLevel object to the renderer
        Called whenever the preview needs to be recalculated
        """
        brushSize = self.getBrushSize()
        brushStyle = self.options['Style']
        key = getattr(self.brushMode, 'mainBlock', 'Block')
        blockInfo = self.options[key]

        class FakeLevel(pymclevel.MCLevel):
            filename = "Fake Level"
            materials = self.editor.level.materials

            def __init__(self):
                self.chunkCache = {}

            Width, Height, Length = brushSize
            zerolight = numpy.zeros((16, 16, Height), dtype='uint8')
            zerolight[:] = 15

            def getChunk(self, cx, cz):
                if (cx, cz) in self.chunkCache:
                    return self.chunkCache[cx, cz]

                class FakeBrushChunk(pymclevel.level.FakeChunk):
                    Entities = []
                    TileEntities = []

                f = FakeBrushChunk()
                f.world = self
                f.chunkPosition = (cx, cz)

                mask = createBrushMask(brushSize, brushStyle, (0, 0, 0), BoundingBox((cx << 4, 0, cz << 4), (16, self.Height, 16)))
                f.Blocks = numpy.zeros(mask.shape, dtype='uint8')
                f.Data = numpy.zeros(mask.shape, dtype='uint8')
                f.BlockLight = self.zerolight
                f.SkyLight = self.zerolight

                if blockInfo.ID:
                    f.Blocks[mask] = blockInfo.ID
                    f.Data[mask] = blockInfo.blockData

                else:
                    f.Blocks[mask] = 255
                self.chunkCache[cx, cz] = f
                return f

        self.level = FakeLevel()
        CloneTool.setupPreview(self, alpha=self.settings['brushAlpha'])

    def getReticlePoint(self, pos, direction):
        """
        Calculates the position of the reticle.
        Called by drawTerrainReticle.
        """
        if len(self.draggedPositions):
            direction = self.draggedDirection
        return map(lambda a, b: a + (b * self.reticleOffset), pos, direction)

    def increaseToolReach(self):
        """
        Called on scrolling up (default).
        Increases the reticleOffset (distance between face and brush center) by 1.
        (unless you're in right-click mode and don't have long-distance mode enabled)
        """
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            return False
        self.reticleOffset += 1
        return True

    def decreaseToolReach(self):
        """
        Called on scrolling down (default).
        Decreases the reticleOffset (distance between face and brush center) by 1.
        (unless you're in right-click mode and don't have long-distance mode enabled)
        """
        if self.editor.mainViewport.mouseMovesCamera and not self.editor.longDistanceMode:
            return False
        self.reticleOffset = max(self.reticleOffset - 1, 0)
        return True

    def drawToolReticle(self):
        """
        Draws a yellow reticle at every position where you dragged the brush.
        Called by leveleditor.render
        """
        for pos in self.draggedPositions:
            drawTerrainCuttingWire(BoundingBox(pos, (1, 1, 1)),
                                   (0.75, 0.75, 0.1, 0.4),
                                   (1.0, 1.0, 0.5, 1.0))

    def getDirtyBox(self, point, tool):
        """
        Returns a box around the Brush given point and size of the brush.
        """
        if hasattr(self.brushMode, 'createDirtyBox'):
            return self.brushMode.createDirtyBox(self.brushMode, point, tool)
        else:
            size = tool.getBrushSize()
            origin = map(lambda x, s: x - (s >> 1), point, size)
            return BoundingBox(origin, size)

    def drawTerrainReticle(self):
        """
        Draws the white reticle where the cursor is pointing.
        Called by leveleditor.render
        """
        if self.optionBackup != self.options:
            self.saveBrushPreset('__temp__')
            self.optionBackup = copy.copy(self.options)
        if not hasattr(self, 'brushMode'):
            return
        if self.options[getattr(self.brushMode, 'mainBlock', 'Block')] != self.renderedBlock and not getattr(self.brushMode, 'addPasteButton', False):
            self.setupPreview()
            self.renderedBlock = self.options[getattr(self.brushMode, 'mainBlock', 'Block')]

        if self.pickBlockKey == 1:  #Alt is pressed
            self.editor.drawWireCubeReticle(color=(0.2, 0.6, 0.9, 1.0))
        else:
            pos, direction = self.editor.blockFaceUnderCursor
            reticlePoint = self.getReticlePoint(pos, direction)
            self.editor.drawWireCubeReticle(position=reticlePoint)
            if reticlePoint != pos:
                GL.glColor4f(1.0, 1.0, 0.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))  #Center of reticle block
                    GL.glVertex3f(*map(lambda a, b: a + 0.5 + b * 0.5, pos, direction))  #Top side of surface block
            dirtyBox = self.getDirtyBox(reticlePoint, self)
            self.drawTerrainPreview(dirtyBox.origin)
            if self.lineToolKey and self.lastPosition and getattr(self.brushMode, 'draggableBrush', True):  #If dragging mouse with Linetool pressed.
                GL.glColor4f(1.0, 1.0, 1.0, 0.7)
                with gl.glBegin(GL.GL_LINES):
                    GL.glVertex3f(*map(lambda a: a + 0.5, self.lastPosition))
                    GL.glVertex3f(*map(lambda a: a + 0.5, reticlePoint))

    def decreaseBrushSize(self):
        """
        Increases Brush Size, triggered by pressing corresponding key.
        """
        for key in ('W', 'H', 'L'):
            self.options[key] = max(self.options[key] - 1, 0)
        self.setupPreview()

    def increaseBrushSize(self):
        """
        Decreases Brush Size, triggered by pressing corresponding key.
        """
        for key in ('W', 'H', 'L'):
            self.options[key] += 1
        self.setupPreview()

    def swap(self):
        main = getattr(self.brushMode, 'mainBlock', 'Block')
        secondary = getattr(self.brushMode, 'secondaryBlock', 'Block To Replace With')
        bi = self.options[main]
        self.options[main] = self.options[secondary]
        self.options[secondary] = bi
        self.showPanel()

    def rotate(self, blocksOnly=False):
        """
        Rotates the brush.
        :keyword blocksOnly: Also rotate the data value of the block we're brushing with.
        """
        def rotateBlock():
            list = [key for key in self.options if self.options[key].__class__.__name__ == 'Block']
            list = getattr(self.brushMode, 'rotatableBlocks', list)
            for key in list:
                bl = self.options[key]
                data = [[[bl.blockData]]]
                blockrotation.RotateLeft([[[bl.ID]]], data)
                bl.blockData = data[0][0][0]
            self.showPanel()

        if config.settings.rotateBlockBrush.get() or blocksOnly:
            rotateBlock()
        if not blocksOnly:
            W = self.options['W']
            self.options['W'] = self.options['L']
            self.options['L'] = W
        self.setupPreview()

    def roll(self, blocksOnly=False):
        """
        Rolls the brush.
        :keyword blocksOnly: Also roll the data value of the block we're brushing with.
        """
        def rollBlock():
            list = [key for key in self.options if self.options[key].__class__.__name__ == 'Block']
            list = getattr(self.brushMode, 'rotatableBlocks', list)
            for key in list:
                bl = self.options[key]
                data = [[[bl.blockData]]]
                blockrotation.Roll([[[bl.ID]]], data)
                bl.blockData = data[0][0][0]
            self.showPanel()

        if config.settings.rotateBlockBrush.get() or blocksOnly:
            rollBlock()
        if not blocksOnly:
            H = self.options['H']
            self.options['H'] = self.options['W']
            self.options['W'] = H
        self.setupPreview()

    def importPaste(self):
        """
        Hack for paste to import a level.
        """
        clipFilename = mcplatform.askOpenFile(title='Choose a schematic or level...', schematics=True)
        if clipFilename:
            try:
                self.loadLevel(pymclevel.fromFile(clipFilename, readonly=True))
            except Exception:
                alert("Failed to load file %s" % clipFilename)
                self.brushMode = "Fill"
                return

    def loadLevel(self, level):
        self.level = level
        self.options['Minimum Spacing'] = min([s / 4 for s in level.size])
        CloneTool.setupPreview(self, alpha = self.settings['brushAlpha'])


def createBrushMask(shape, style="Round", offset=(0, 0, 0), box=None, chance=100, hollow=False):
    """
    Return a boolean array for a brush with the given shape and style.
    If 'offset' and 'box' are given, then the brush is offset into the world
    and only the part of the world contained in box is returned as an array.
    :param shape, UNKWOWN
    :keyword style, style of the brush. Round if not given.
    :keyword offset, UNKWOWN
    :keyword box, UNKWOWN
    :keyword chance, also known as Noise. Input in stock-brushes like Fill and Replace.
    :keyword hollow, input to calculate a hollow brush.
    """

    #We are returning indices for a Blocks array, so swap axes
    if box is None:
        box = BoundingBox(offset, shape)
    if chance < 100 or hollow:
        box = box.expand(1)

    outputShape = box.size
    outputShape = (outputShape[0], outputShape[2], outputShape[1])

    shape = shape[0], shape[2], shape[1]
    offset = numpy.array(offset) - numpy.array(box.origin)
    offset = offset[[0, 2, 1]]

    inds = numpy.indices(outputShape, dtype=float)
    halfshape = numpy.array([(i >> 1) - ((i & 1 == 0) and 0.5 or 0) for i in shape])

    blockCenters = inds - halfshape[:, newaxis, newaxis, newaxis]
    blockCenters -= offset[:, newaxis, newaxis, newaxis]

    # odd diameter means measure from the center of the block at 0,0,0 to each block center
    # even diameter means measure from the 0,0,0 grid point to each block center

    # if diameter & 1 == 0: blockCenters += 0.5
    shape = numpy.array(shape, dtype='float32')

    # if not isSphere(shape):
    if style == "Round":
        blockCenters *= blockCenters
        shape /= 2
        shape *= shape

        blockCenters /= shape[:, newaxis, newaxis, newaxis]
        distances = sum(blockCenters, 0)
        mask = distances < 1
    elif style == "Cylinder":
        pass

    elif style == "Square":
        # mask = ones(outputShape, dtype=bool)
        # mask = blockCenters[:, newaxis, newaxis, newaxis] < shape
        blockCenters /= shape[:, None, None, None]

        distances = numpy.absolute(blockCenters).max(0)
        mask = distances < .5

    elif style == "Diamond":
        blockCenters = numpy.abs(blockCenters)
        shape /= 2
        blockCenters /= shape[:, newaxis, newaxis, newaxis]
        distances = sum(blockCenters, 0)
        mask = distances < 1
    else:
        raise ValueError("Unknown style: " + style)

    if (chance < 100 or hollow) and max(shape) > 1:
        threshold = chance / 100.0
        exposedBlockMask = numpy.ones(shape=outputShape, dtype='bool')
        exposedBlockMask[:] = mask
        submask = mask[1:-1, 1:-1, 1:-1]
        exposedBlockSubMask = exposedBlockMask[1:-1, 1:-1, 1:-1]
        exposedBlockSubMask[:] = False

        for dim in (0, 1, 2):
            slices = [slice(1, -1), slice(1, -1), slice(1, -1)]
            slices[dim] = slice(None, -2)
            exposedBlockSubMask |= (submask & (mask[slices] != submask))
            slices[dim] = slice(2, None)
            exposedBlockSubMask |= (submask & (mask[slices] != submask))

        if hollow:
            mask[~exposedBlockMask] = False
        if chance < 100:
            rmask = numpy.random.random(mask.shape) < threshold

            mask[exposedBlockMask] = rmask[exposedBlockMask]

    if chance < 100 or hollow:
        return mask[1:-1, 1:-1, 1:-1]
    else:
        return mask

def createTileEntities(block, box, chunk):
    if box is None or block.stringID not in TileEntity.stringNames.keys():
        return

    tileEntity = TileEntity.stringNames[block.stringID]
    for (x, y, z) in box.positions:
        if chunk.world.blockAt(x, y, z) == block.ID:
            if chunk.tileEntityAt(x, y, z):
                chunk.removeTileEntitiesInBox(BoundingBox((x, y, z), (1, 1, 1)))
            tileEntityObject = TileEntity.Create(tileEntity, (x, y, z))
            chunk.TileEntities.append(tileEntityObject)
            chunk._fakeEntities = None
