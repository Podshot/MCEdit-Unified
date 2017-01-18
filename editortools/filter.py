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
# Modified by D.C.-G. for translation purpose
import collections
import os
import traceback
import copy
from albow import FloatField, IntField, AttrRef, Row, Label, Widget, TabPanel, \
    CheckBox, Column, Button, TextFieldWrapped, translate
from editortools.tooloptions import ToolOptions
from albow.extended_widgets import CheckBoxLabel
_ = translate._
import albow
from config import config
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from glbackground import Panel
from mceutils import setWindowCaption, alertException
from albow import ChoiceButton, showProgress, TextInputRow
import mcplatform
from operation import Operation
from albow.dialogs import wrapped_label, alert, Dialog
import pymclevel
from pymclevel import BoundingBox, MCEDIT_DEFS, MCEDIT_IDS
import urllib2
import urllib
import json
import shutil
import directories
import sys
import keys
import imp
from nbtexplorer import NBTExplorerToolPanel

import logging
log = logging.getLogger(__name__)

class FilterUtils(object):
    
    def __init__(self, **kwargs):
        self._given_data = []
        for arg in kwargs:
            self._given_data.append(arg)
            self.__dict__[arg] = kwargs[arg]
            
    def Available_Attributes(self):
        return self._given_data

def alertFilterException(func):
    def _func(*args, **kw):
        try:
            func(*args, **kw)
        except Exception, e:
            print traceback.format_exc()
            alert(_(u"Exception during filter operation. See console for details.\n\n{0}").format(e))

    return _func


def addNumField(page, optionName, oName, val, min_value=None, max_value=None, increment=0.1):
    if isinstance(val, float):
        field_type = FloatField
        if isinstance(increment, int):
            increment = float(increment)
    else:
        field_type = IntField
        if increment == 0.1:
            increment = 1
        if isinstance(increment, float):
            increment = int(round(increment))

    if min_value == max_value:
        min_value = None
        max_value = None

    field = field_type(value=val, width=200, min=min_value, max=max_value)
    field._increment = increment
    page.optionDict[optionName] = AttrRef(field, 'value')

    row = Row([Label(oName, doNotTranslate=True), field])
    return row


class JsonDictProperty(dict):
    def __init__(self, filename, **kwargs):
        super(JsonDictProperty, self).__init__(**kwargs)
        self._filename = filename

    def __setitem__(self, key, value):
        data = self._getJson()
        data[key] = value
        self._putJson(data)

    def __getitem__(self, key):
        return self._getJson()[key]

    def __delitem__(self, key):
        data = self._getJson()
        del data[key]
        self._putJson(data)

    def _putJson(self, data):
        with open(self._filename, 'wb') as f:
            json.dump(data, f)

    def _getJson(self):
        try:
            filter_json = json.load(open(self._filename), 'rb')
            if "Macros" not in filter_json.keys():
                filter_json["Macros"] = {}
            return filter_json
        except (ValueError, IOError):
            return {"Macros": {}}
        
class SingleFileChooser(Widget):
    OPEN_FILE = 0
    SAVE_FILE = 1
    
    def _open_file(self):
        file_types = []
        for f_type in self.file_types:
            file_types.append(f_type.replace("*.", ""))
        file_path = mcplatform.askOpenFile(title='Select a file...', suffixes=file_types)
        if file_path:
            self._button.set_text("{filen}".format(filen=os.path.basename(file_path)), True)
            self.file_path = file_path
        else:
            self._button.set_text("Choose a file")
            self.file_path = None
        self._button.shrink_wrap()
        self.shrink_wrap()
    
    def _save_file(self):
        file_types = 'Custom File\0{}\0'.format(';'.join(self.file_types))
        if not self.file_types[0].startswith("*"):
            name = self.file_types[0]
        else:
            name = self.file_types[0][1:]
        file_path = mcplatform.askSaveFile(".", "Save as...", name, file_types, self.file_types[0][1:])
        if file_path:
            self._button.set_text(os.path.basename(file_path), True)
            self.file_path = file_path
        else:
            self._button.set_text('Save a file')
            self.file_path = None
        self._button.shrink_wrap()
        self.shrink_wrap()
    
    def __init__(self, file_types=None, operation=0, **kwds):
        Widget.__init__(self, **kwds)
        if file_types is None:
            self.file_types = ["*.*",]
        else:
            self.file_types = file_types
        self.file_path = None
        self._button = None
            
        if operation == self.OPEN_FILE:
            self._button = Button("Choose a file", action=self._open_file)
        elif operation == self.SAVE_FILE:
            self._button = Button("Save a file", action=self._save_file)
            
        self.add(self._button)
        
        self.shrink_wrap()


class MacroModuleOptions(Widget):
    is_gl_container = True

    def __init__(self, macro_data, *args, **kw):
        self._parent = None
        self._macro_data = macro_data
        if '_parent' in kw.keys():
            self._parent = kw.pop('_parent')

        Widget.__init__(self, *args, **kw)

        infoColList = []
        stepsLabel = wrapped_label("Number of steps: %s" % macro_data["Number of steps"], 300)
        infoColList.append(stepsLabel)
        for step in sorted(macro_data.keys()):
            if step != "Number of steps":
                infoColList.append(wrapped_label("Step %s: %s" % (int(step) + 1, macro_data[step]["Name"]), 300))
        self.add(Column(infoColList))
        self.shrink_wrap()

    @property
    def options(self):
        return {}

    @options.setter
    def options(self, value):
        pass

    def run(self):
        pass

    @alertFilterException
    def confirm(self, tool):
        with setWindowCaption("Applying Macro..."):
            options = []
            filters = []
            for step in sorted(self._macro_data.keys()):
                if step != "Number of steps":
                    filters.append(tool.filterModules[self._macro_data[step]["Name"]])
                    for module_input in self._macro_data[step]["Inputs"].keys():
                        if not isinstance(self._macro_data[step]["Inputs"][module_input], (str, unicode)):
                            continue
                        if not self._macro_data[step]["Inputs"][module_input].startswith("block-"):
                            continue
                        toFind = self._macro_data[step]["Inputs"][module_input][6:].split(":")
                        block = tool.editor.materials.get((toFind[0], toFind[1]))
                        self._macro_data[step]["Inputs"][module_input] = block
                    options.append(self._macro_data[step]["Inputs"])

            op = MacroOperation(tool.editor, tool.editor.level, tool.selectionBox(), filters, options)

            tool.editor.level.showProgress = showProgress

            tool.editor.addOperation(op)
            tool.editor.addUnsavedEdit()

            tool.editor.invalidateBox(tool.selectionBox())


class FilterModuleOptions(Widget):
    is_gl_container = True

    def __init__(self, tool, module, *args, **kw):
        self._parent = None
        self.nbttree = None
        self.module = module
        if '_parent' in kw.keys():
            self._parent = kw.pop('_parent')
        Widget.__init__(self, *args, **kw)
        self.spacing = 2
        self.tool = tool
        self.pages = pages = TabPanel()
        pages.is_gl_container = True
        self.optionDict = {}

        self.giveEditorObject(module)
        log.info("Creating options for " + str(module))
        if hasattr(module, "inputs"):
            trn = getattr(module, "trn", None)
            self.trn = trn
            if isinstance(module.inputs, list):
                self.pgs = []
                for tabData in module.inputs:
                    title, page, pageRect = self.makeTabPage(self.tool, tabData, trn=trn)
                    self.pgs.append((title, page))
                pages.set_parent(None)
                self.pages = pages = TabPanel(self.pgs)
            elif isinstance(module.inputs, tuple):
                title, page, pageRect = self.makeTabPage(self.tool, module.inputs, trn=trn)
                pages.add_page(title, page)
                pages.set_rect(pageRect)
        else:
            self.size = (0, 0)

        pages.shrink_wrap()
        self.add(pages)
        self.shrink_wrap()
        if len(pages.pages):
            if pages.current_page is not None:
                pages.show_page(pages.current_page)
            else:
                pages.show_page(pages.pages[0])

        for eachPage in pages.pages:
            self.optionDict = dict(self.optionDict.items() + eachPage.optionDict.items())
            

    def rebuildTabPage(self, inputs, **kwargs):
        title, page, rect = self.makeTabPage(self.tool, inputs, self.trn, **kwargs)
        for i, t, p, s, r in self.pages.iter_tabs():
            if t == title:
                self.pages.remove_page(p)
                self.pages.add_page(title, page, idx=i)
                self.pages.show_page(page)
                break

    def makeTabPage(self, tool, inputs, trn=None, **kwargs):
        page = Widget(**kwargs)
        page.is_gl_container = True
        rows = []
        cols = []
        max_height = tool.editor.mainViewport.height - tool.editor.toolbar.height - tool.editor.subwidgets[0].height -\
            self._parent.filterSelectRow.height - self._parent.confirmButton.height - self.pages.tab_height

        page.optionDict = {}
        page.tool = tool
        title = "Tab"

        for optionSpec in inputs:
            optionName = optionSpec[0]
            optionType = optionSpec[1]
            if trn is not None:
                n = trn._(optionName)
            else:
                n = optionName
            if n == optionName:
                oName = _(optionName)
            else:
                oName = n
            if isinstance(optionType, tuple):
                if isinstance(optionType[0], (int, long, float)):
                    if len(optionType) == 3:
                        val, min, max = optionType
                        increment = 0.1
                    elif len(optionType) == 2:
                        min, max = optionType
                        val = min
                        increment = 0.1
                    else:
                        val, min, max, increment = optionType

                    rows.append(addNumField(page, optionName, oName, val, min, max, increment))

                if isinstance(optionType[0], (str, unicode)):
                    isChoiceButton = False

                    if optionType[0] == "string":
                        kwds = []
                        wid = None
                        val = None
                        for keyword in optionType:
                            if isinstance(keyword, (str, unicode)) and keyword != "string":
                                kwds.append(keyword)
                        for keyword in kwds:
                            splitWord = keyword.split('=')
                            if len(splitWord) > 1:
                                v = None

                                try:
                                    v = int(splitWord[1])
                                except ValueError:
                                    pass

                                key = splitWord[0]
                                if v is not None:
                                    if key == "width":
                                        wid = v
                                else:
                                    if key == "value":
                                        val = "=".join(splitWord[1:])

                        if val is None:
                            val = ""
                        if wid is None:
                            wid = 200

                        field = TextFieldWrapped(value=val, width=wid)
                        page.optionDict[optionName] = AttrRef(field, 'value')

                        row = Row((Label(oName, doNotTranslate=True), field))
                        rows.append(row)
                    elif optionType[0] == "block":
                        blockButton = BlockButton(tool.editor.level.materials)
                        try:
                            blockButton.blockInfo = tool.editor.level.materials[optionType[1]]
                        except AttributeError:
                            blockButton.blockInfo = tool.editor.level.materials[0]
                        except KeyError:
                            if tool.editor.level.materials == pymclevel.pocketMaterials:
                                blockButton.blockInfo = pymclevel.alphaMaterials[optionType[1]]
                            else:
                                raise
                
                        row = Column((Label(oName, doNotTranslate=True), blockButton))
                        page.optionDict[optionName] = AttrRef(blockButton, 'blockInfo')
                
                        rows.append(row)
                    elif optionType[0] == "file-save":
                        if len(optionType) == 2:
                            file_chooser = SingleFileChooser(file_types=optionType[1], operation=SingleFileChooser.SAVE_FILE)
                        else:
                            file_chooser = SingleFileChooser(operation=SingleFileChooser.SAVE_FILE)
                        
                        row = Row((Label(oName, doNotTranslate=True), file_chooser))
                        page.optionDict[optionName] = AttrRef(file_chooser, 'file_path')
                        
                        rows.append(row)
                    elif optionType[0] == "file-open":
                        if len(optionType) == 2:
                            file_chooser = SingleFileChooser(file_types=optionType[1], operation=SingleFileChooser.OPEN_FILE)
                        else:
                            file_chooser = SingleFileChooser(operation=SingleFileChooser.OPEN_FILE)
                        
                        row = Row((Label(oName, doNotTranslate=True), file_chooser))
                        page.optionDict[optionName] = AttrRef(file_chooser, 'file_path')
                        
                        rows.append(row)
                    else:
                        isChoiceButton = True

                    if isChoiceButton:
                        if trn is not None:
                            __ = trn._
                        else:
                            __ = _
                        choices = [__("%s" % a) for a in optionType]
                        choiceButton = ChoiceButton(choices, doNotTranslate=True)
                        page.optionDict[optionName] = AttrRef(choiceButton, 'selectedChoice')

                        rows.append(Row((Label(oName, doNotTranslate=True), choiceButton)))
                        

            elif isinstance(optionType, bool):
                cbox = CheckBox(value=optionType)
                page.optionDict[optionName] = AttrRef(cbox, 'value')

                row = Row((Label(oName, doNotTranslate=True), cbox))
                rows.append(row)

            elif isinstance(optionType, (int, float)):
                rows.append(addNumField(self, optionName, oName, optionType))
                
            elif optionType == "blocktype" or isinstance(optionType, pymclevel.materials.Block):
                blockButton = BlockButton(tool.editor.level.materials)
                if isinstance(optionType, pymclevel.materials.Block):
                    blockButton.blockInfo = optionType

                row = Column((Label(oName, doNotTranslate=True), blockButton))
                page.optionDict[optionName] = AttrRef(blockButton, 'blockInfo')

                rows.append(row)
            elif optionType == "label":
                rows.append(wrapped_label(oName, 50, doNotTranslate=True))
            elif optionType == "string":
                inp = None
                # not sure how to pull values from filters,
                # but leaves it open for the future. Use this variable to set field width.
                if inp is not None:
                    size = inp
                else:
                    size = 200
                field = TextFieldWrapped(value="")
                row = TextInputRow(oName, ref=AttrRef(field, 'value'), width=size, doNotTranslate=True)
                page.optionDict[optionName] = AttrRef(field, 'value')
                rows.append(row)
            elif optionType == "title":
                title = oName
                
            elif optionType == "file-save":
                file_chooser = SingleFileChooser(operation=SingleFileChooser.SAVE_FILE)
                row = Row((Label(oName, doNotTranslate=True), file_chooser))
                page.optionDict[optionName] = AttrRef(file_chooser, 'file_path')
                        
                rows.append(row)
            elif optionType == "file-open":
                file_chooser = SingleFileChooser(operation=SingleFileChooser.OPEN_FILE)
                row = Row((Label(oName, doNotTranslate=True), file_chooser))
                page.optionDict[optionName] = AttrRef(file_chooser, 'file_path')
                        
                rows.append(row)
            elif type(optionType) == list and optionType[0].lower() == "nbttree":
                kw = {'close_text': None, 'load_text': None}
                if len(optionType) >= 3:
                    def close():
                        self.pages.show_page(self.pages.pages[optionType[2]])
                    kw['close_action'] = close
                    kw['close_text'] = "Go Back"
                if len(optionType) >= 4:
                    if optionType[3]:
                        kw['load_text'] = optionType[3]
                if hasattr(self.module, 'nbt_ok_action'):
                    kw['ok_action'] = getattr(self.module, 'nbt_ok_action')
                self.nbttree = NBTExplorerToolPanel(self.tool.editor, nbtObject=optionType[1],
                                                    height=max_height, no_header=True, copy_data=False, **kw)
                self.module.set_tree(self.nbttree.tree)
                for meth_name in dir(self.module):
                    if meth_name.startswith('nbttree_'):
                        setattr(self.nbttree.tree.treeRow, meth_name.split('nbttree_')[-1],
                                getattr(self.module, meth_name))
                        # elif meth_name.startswith('nbt_'):
                        #     setattr(self.nbttree, meth_name.split('nbt_')[-1], getattr(self.module, meth_name))
                page.optionDict[optionName] = AttrRef(self, 'rebuildTabPage')
                rows.append(self.nbttree)
                self.nbttree.page = len(self.pgs)

            else:
                raise ValueError(("Unknown option type", optionType))

        height = sum(r.height for r in rows) + (len(rows) - 1) * self.spacing

        if height > max_height:
            h = 0
            for i, r in enumerate(rows):
                h += r.height
                if h > height / 2:
                    if rows[:i]:
                        cols.append(Column(rows[:i], spacing=0))
                    rows = rows[i:]
                    break

        if len(rows):
            cols.append(Column(rows, spacing=0))

        if len(cols):
            page.add(Row(cols, spacing=0))
        page.shrink_wrap()

        return title, page, page._rect

    @property
    def options(self):
        options = {}
        for k, v in self.optionDict.iteritems():
            options[k] = v.get() if not isinstance(v.get(), pymclevel.materials.Block) else copy.copy(v.get())
        if self.pages.current_page is not None:
            options["__page_index__"] = self.pages.pages.index(self.pages.current_page)
        return options

    @options.setter
    def options(self, val):
        for k in val:
            if k in self.optionDict:
                self.optionDict[k].set(val[k])
        index = val.get("__page_index__", -1)
        if len(self.pages.pages) > index > -1:
            self.pages.show_page(self.pages.pages[index])

    def giveEditorObject(self, module):
        module.editor = self.tool.editor

    @staticmethod
    def confirm(tool):
        with setWindowCaption("Applying Filter... - "):
            filterModule = tool.filterModules[tool.panel.filterSelect.selectedChoice]

            op = FilterOperation(tool.editor, tool.editor.level, tool.selectionBox(), filterModule,
                                 tool.panel.filterOptionsPanel.options)

            tool.editor.level.showProgress = showProgress

            tool.editor.addOperation(op)
            tool.editor.addUnsavedEdit()

            tool.editor.invalidateBox(tool.selectionBox())


class FilterToolPanel(Panel):

    BACKUP_FILTER_JSON = False
    """If set to true, the filter.json is backed up to the hard disk
    every time it's edited. The default is false, which makes the file save
    only whenever the tool gets closed. If MCEdit were to crash, any recorded
    macros would not be saved."""

    def __init__(self, tool):
        Panel.__init__(self, name='Panel.FilterToolPanel')
        self.macro_steps = []
        self.current_step = 0
        self._filter_json = None
        self.keys_panel = None
        self.filterOptionsPanel = None
        self.filterSelect = ChoiceButton([], choose=self.filterChanged, doNotTranslate=True)
        self.binding_button = Button("", action=self.bind_key,
                                     tooltipText="Click to bind this filter to a key")

        self.filterLabel = Label("Filter:", fg_color=(177, 177, 255, 255))
        self.filterLabel.mouse_down = lambda x: mcplatform.platform_open(directories.getFiltersDir())
        self.filterLabel.tooltipText = "Click to open filters folder"

        self.macro_button = Button("Record Macro", action=self.start_record_macro)
        self.filterSelectRow = Row((self.filterLabel, self.filterSelect,
                                    self.macro_button, self.binding_button))

        self.confirmButton = Button("Filter", action=self.confirm)

        self._recording = False
        self._save_macro = False
        self.tool = tool
        self.selectedName = self.filter_json.get("Last Filter Opened", "")
        
        
        utils = FilterUtils(
                            editor=tool.editor, 
                            materials=self.tool.editor.level.materials,
                            custom_widget=tool.editor.addExternalWidget,
                            resize_selection_box=tool.editor._resize_selection_box
                            )
        utils_module = imp.new_module("filter_utils")
        utils_module = utils
        sys.modules["filter_utils"] = utils_module

    @staticmethod
    def load_filter_json():
        filter_json_file = os.path.join(directories.getDataDir(), "filters.json")
        filter_json = {}
        if FilterToolPanel.BACKUP_FILTER_JSON:
            filter_json = JsonDictProperty(filter_json_file)
        else:
            try:
                if os.path.exists(filter_json_file):
                    filter_json = json.load(open(filter_json_file, 'rb'))
            except (ValueError, IOError) as e:
                log.error("Error while loading filters.json %s", e)
        if "Macros" not in filter_json.keys():
            filter_json["Macros"] = {}
        return filter_json

    @property
    def filter_json(self):
        if self._filter_json is None:
            self._filter_json = FilterToolPanel.load_filter_json()
        return self._filter_json

    def close(self):
        self._saveOptions()
        self.filter_json["Last Filter Opened"] = self.selectedName
        if not FilterToolPanel.BACKUP_FILTER_JSON:
            with open(os.path.join(directories.getDataDir(), "filters.json"), 'w') as f:
                json.dump(self.filter_json, f)

    def reload(self):
        for i in list(self.subwidgets):
            self.remove(i)

        tool = self.tool

        # Display "No filter modules found" if there are no filters
        if len(tool.filterModules) is 0:
            self.add(Label("No filter modules found!"))
            self.shrink_wrap()
            return

        names_list = sorted([n for n in tool.filterNames if not n.startswith("[")])

        # We get a list of names like ["[foo] bar", "[test] thing"]
        # The to sort on is created by splitting on "[": "[foo", " bar" and then
        # removing the first char: "foo", "bar"

        subfolder_names_list = sorted([n for n in tool.filterNames if n.startswith("[")],
                                      key=lambda x: x.split("]")[0][1:])

        names_list.extend(subfolder_names_list)
        names_list.extend([macro for macro in self.filter_json["Macros"].keys()])

        if self.selectedName is None or self.selectedName not in names_list:
            self.selectedName = names_list[0]

        # Remove any keybindings that don't have a filter
        for (i, j) in config.config.items("Filter Keys"):
            if i == "__name__":
                continue
            if not any([i == m.lower() for m in names_list]):
                config.config.remove_option("Filter Keys", i)

        self.filterSelect.choices = names_list

        name = self.selectedName.lower()
        names = [k for (k, v) in config.config.items("Filter Keys")]
        btn_name = config.config.get("Filter Keys", name) if name in names else "*"
        self.binding_button.set_text(btn_name)

        self.filterOptionsPanel = None
        while self.filterOptionsPanel is None:
            module = self.tool.filterModules.get(self.selectedName, None)
            if module is not None:
                try:
                    self.filterOptionsPanel = FilterModuleOptions(self.tool, module, _parent=self)
                except Exception as e:
                    alert(_("Error creating filter inputs for {0}: {1}").format(module, e))
                    traceback.print_exc()
                    self.tool.filterModules.pop(self.selectedName)
                    self.selectedName = tool.filterNames[0]

                if len(tool.filterNames) == 0:
                    raise ValueError("No filters loaded!")
                if not self._recording:
                    self.confirmButton.set_text("Filter")
            else:  # We verified it was an existing macro already
                macro_data = self.filter_json["Macros"][self.selectedName]
                self.filterOptionsPanel = MacroModuleOptions(macro_data)
                self.confirmButton.set_text("Run Macro")

        # This has to be recreated every time in case a macro has a longer name then everything else.
        self.filterSelect = ChoiceButton(names_list, choose=self.filterChanged, doNotTranslate=True)
        self.filterSelect.selectedChoice = self.selectedName
        self.filterSelectRow = Row((self.filterLabel, self.filterSelect,
                                    self.macro_button, self.binding_button))

        self.add(Column((self.filterSelectRow, self.filterOptionsPanel, self.confirmButton)))

        self.shrink_wrap()

        if self.parent:
            height = self.parent.mainViewport.height - self.parent.toolbar.height
            self.centery = height / 2 + self.parent.subwidgets[0].height

        if self.selectedName in self.tool.savedOptions:
            self.filterOptionsPanel.options = self.tool.savedOptions[self.selectedName]

    @property
    def macroSelected(self):
        return self.filterSelect.selectedChoice not in self.tool.filterNames

    def filterChanged(self):
        # if self.filterSelect.selectedChoice not in self.tool.filterModules:
        #     return
        self._saveOptions()
        self.selectedName = self.filterSelect.selectedChoice
        if self.macroSelected:  # Is macro
            self.macro_button.set_text("Delete Macro")
            self.macro_button.action = self.delete_macro
        elif not self._recording:
            self.macro_button.set_text("Record Macro")
            self.macro_button.action = self.start_record_macro
        self.reload()

    def delete_macro(self):
        macro_name = self.selectedName
        if macro_name in self.filter_json["Macros"]:
            del self.filter_json["Macros"][macro_name]
        if len(self.filterSelect.choices) == 1:  # Just this macro available
            self.reload()
            return
        choices = self.filterSelect.choices
        self.filterSelect.selectedChoice = choices[0] if choices[0] != macro_name else choices[1]
        self.filterChanged()

    def stop_record_macro(self):
        macro_dialog = Dialog()
        macroNameLabel = Label("Macro Name: ")
        macroNameField = TextFieldWrapped(width=200)

        def save_macro():
            macro_name = "{Macro} " + macroNameField.get_text()

            self.filter_json["Macros"][macro_name] = {}
            self.filter_json["Macros"][macro_name]["Number of steps"] = len(self.macro_steps)
            self.filterSelect.choices.append(macro_name)
            for entry in self.macro_steps:
                for inp in entry["Inputs"].keys():
                    if not isinstance(entry["Inputs"][inp], pymclevel.materials.Block):
                        if not entry["Inputs"][inp] == "blocktype":
                            continue
                    _inp = entry["Inputs"][inp]
                    entry["Inputs"][inp] = "block-{0}:{1}".format(_inp.ID, _inp.blockData)
                self.filter_json["Macros"][macro_name][entry["Step"]] = {"Name": entry["Name"],
                                                                         "Inputs": entry["Inputs"]}
            stop_dialog()
            self.filterSelect.selectedChoice = macro_name
            self.filterChanged()

        def stop_dialog():
            self.macro_button.text = "Record Macro"
            self.macro_button.tooltipText = None
            self.macro_button.action = self.start_record_macro
            macro_dialog.dismiss()
            self.macro_steps = []
            self.current_step = 0
            self._recording = False

        input_row = Row((macroNameLabel, macroNameField))
        saveButton = Button("Save", action=save_macro)
        closeButton = Button("Cancel", action=stop_dialog)
        button_row = Row((saveButton, closeButton))
        macro_dialog.add(Column((input_row, button_row)))
        macro_dialog.shrink_wrap()
        macro_dialog.present()

    def start_record_macro(self):
        self.macro_button.text = "Stop recording"
        self.macro_button.tooltipText = "Currently recording a macro"
        self.macro_button.action = self.stop_record_macro
        self.confirmButton.text = "Add macro"
        self.confirmButton.width += 75
        self.confirmButton.centerx = self.centerx
        self._recording = True

    def _addMacroStep(self, name=None, inputs=None):
        data = {"Name": name, "Step": self.current_step, "Inputs": inputs}
        self.current_step += 1
        self.macro_steps.append(data)

    def unbind_key(self):
        config.config.remove_option("Filter Keys", self.selectedName)
        self.binding_button.text = "*"
        self.keys_panel.dismiss()
        # self.saveOptions()
        self.reload()

    def bind_key(self, message=None):
        panel = Panel(name='Panel.FilterToolPanel.bind_key')
        panel.bg_color = (0.5, 0.5, 0.6, 1.0)
        if not message:
            message = _("Press a key to assign to the filter \"{0}\"\n\n"
                        "Press ESC to cancel.").format(self.selectedName)
        label = albow.Label(message)
        unbind_button = Button("Press to unbind", action=self.unbind_key)
        column = Column((label, unbind_button))
        panel.add(column)
        panel.shrink_wrap()

        def panelKeyUp(evt):
            _key_name = self.root.getKey(evt)
            panel.dismiss(_key_name)

        def panelMouseUp(evt):
            button = keys.remapMouseButton(evt.button)
            _key_name = None
            if button == 3:
                _key_name = "Button 3"
            elif button == 4:
                _key_name = "Scroll Up"
            elif button == 5:
                _key_name = "Scroll Down"
            elif button == 6:
                _key_name = "Button 4"
            elif button == 7:
                _key_name = "Button 5"
            if 2 < button < 8:
                panel.dismiss(_key_name)

        panel.key_up = panelKeyUp
        panel.mouse_up = panelMouseUp

        self.keys_panel = panel
        key_name = panel.present()

        if type(key_name) is bool:
            return True
        if key_name != "Escape":
            if key_name in ["Alt-F4", "F1", "F2", "F3", "F4", "F5", "1", "2", "3",
                            "4", "5", "6", "7", "8", "9", "Ctrl-Alt-F9", "Ctrl-Alt-F10"]:
                self.bind_key(_("You can't use the key {0}.\n"
                                "Press a key to assign to the filter \"{1}\"\n\n"
                                ""
                                "Press ESC to cancel.").format(_(key_name), self.selectedName))
                return True

            keysUsed = [(j, i) for (j, i) in config.config.items("Keys") if i == key_name]
            if keysUsed:
                self.bind_key(_("Can't bind. {0} is already used by {1}.\n"
                                "Press a key to assign to the filter \"{2}\"\n\n"
                                ""
                                "Press ESC to cancel.").format(_(key_name), keysUsed[0][0], self.selectedName))
                return True

            filter_keys = [i for (i, j) in config.config.items("Filter Keys") if j == key_name]
            if filter_keys:
                self.bind_key(_("Can't bind. {0} is already used by the \"{1}\" filter.\n"
                                "Press a new key.\n\n"
                                ""
                                "Press ESC to cancel.").format(_(key_name), filter_keys[0]))
                return True
            config.config.set("Filter Keys", self.selectedName.lower(), key_name)
        config.save()
        self.reload()

    def _saveOptions(self):
        """Should never be called. Call filterchanged() or close() instead,
        which will then call this.
        :return:
        """
        if self.filterOptionsPanel is not None:
            options = {}
            options.update(self.filterOptionsPanel.options)
            options.pop("", "")
            self.tool.savedOptions[self.selectedName] = options

    @alertFilterException
    def confirm(self):
        if self._recording:
            self._addMacroStep(self.selectedName, self.filterOptionsPanel.options)
        else:
            self.filterOptionsPanel.confirm(self.tool)


class FilterOperation(Operation):
    def __init__(self, editor, level, box, filter, options):
        super(FilterOperation, self).__init__(editor, level)
        self.box = box
        self.filter = filter
        self.options = options
        self.canUndo = False

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self.box)

        # Inject the defs for blocks/entities in the module
        # Need to reimport the defs and ids to get the 'fresh' ones
        from pymclevel import MCEDIT_DEFS, MCEDIT_IDS
        self.filter.MCEDIT_DEFS = MCEDIT_DEFS
        self.filter.MCEDIT_IDS = MCEDIT_IDS
        self.filter.perform(self.level, BoundingBox(self.box), self.options)

        self.canUndo = True

    def dirtyBox(self):
        return self.box

class MacroOperation(Operation):
    def __init__(self, editor, level, box, filters, options):
        super(MacroOperation, self).__init__(editor, level)
        self._box = box
        self.options = options
        self.filters = filters
        self.canUndo = False

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self._box)

        for o, f in zip(self.options, self.filters):
            f.perform(self.level, BoundingBox(self._box), o)
        self.canUndo = True

    def dirtyBox(self):
        return self._box


class FilterToolOptions(ToolOptions):
    
    def __init__(self, tool):
        ToolOptions.__init__(self, name='Panel.FilterToolOptions')
        self.tool = tool
        
        self.notifications_disabled = False
        
        disable_error_popup = CheckBoxLabel("Disable Error Notification",
                                            ref=AttrRef(self, 'notifications_disabled'))
        ok_button = Button("Ok", action=self.dismiss)
        
        col = Column((disable_error_popup, ok_button,), spacing=2)
        self.add(col)
        self.shrink_wrap()

class FilterTool(EditorTool):
    tooltipText = "Filter"
    toolIconName = "filter"

    def __init__(self, editor):
        EditorTool.__init__(self, editor)

        self.filterModules = {}
        self.savedOptions = {}
        
        self.filters_not_imported = []
        
        self.optionsPanel = FilterToolOptions(self)

    @property
    def statusText(self):
        return "Choose a filter, then click Filter or press Enter to apply it."

    def toolEnabled(self):
        return not (self.selectionBox() is None)

    def toolSelected(self):
        self.showPanel()

    @alertException
    def showPanel(self):
        self.panel = FilterToolPanel(self)
        
        self.not_imported_filters = []
        self.reloadFilters()

        self.panel.reload()
        height = self.editor.mainViewport.height - self.editor.toolbar.height
        self.panel.centery = height / 2 + self.editor.subwidgets[0].height
        self.panel.left = self.editor.left

        self.editor.add(self.panel)

    def hidePanel(self):
        if self.panel is None:
            return
        self.panel.close()
        if self.panel.parent:
            self.panel.parent.remove(self.panel)
        self.panel = None

    def reloadFilters(self):
        filterFiles = []
        unicode_module_names = []

        # Tracking stock and custom filters names in order to load correctly the translations.
        stock_filters = []
        cust_filters = []

        def searchForFiltersInDir(searchFolder, stock=False):
            for root, folders, files in os.walk(os.path.join(searchFolder), True):
                filter_dir = os.path.basename(root)

                if filter_dir.startswith('demo') or filter_dir.startswith('lib'):
                    continue

                subFolderString = root.replace(searchFolder, "")
                if subFolderString.endswith(os.sep):
                    subFolderString = subFolderString[:len(os.sep)]
                if subFolderString.startswith(os.sep):
                    subFolderString = subFolderString[len(os.sep):]
                if len(subFolderString) > 0:
                    subFolderString = "[" + subFolderString + "]"

                try:
                    root = str(root)
                    if root not in sys.path:
                        sys.path.append(root)
                except UnicodeEncodeError:
                    unicode_module_names.extend([filter_name for filter_name in files])

                for possible_filter in files:
                    if possible_filter.endswith(".py"):
                        if stock:
                            stock_filters.append(possible_filter)
                            _stock = True
                        else:
                            cust_filters.append(possible_filter)
                            _stock = False
                        # Force the 'stock' parameter if the filter was found in the stock-filters directory
                        if possible_filter in stock_filters:
                            _stock = True
                        filterFiles.append((root, possible_filter, _stock, subFolderString))

        # Search first for the stock filters.
        searchForFiltersInDir(os.path.join(directories.getDataDir(), "stock-filters"), True)
        searchForFiltersInDir(directories.getFiltersDir(), False)

        filterModules = []

        org_lang = albow.translate.lang


        # If the path has unicode chars, there's no way of knowing what order to add the
        # files to the sys.modules. To fix this, we keep trying to import until we import
        # fail to import all leftover files.
        shouldContinue = True
        while shouldContinue:
            shouldContinue = False
            for f in filterFiles:
                if f[1] in self.not_imported_filters:
                    continue
                module = tryImport(f[0], f[1], org_lang, f[2], f[3], f[1] in unicode_module_names, notify=(not self.optionsPanel.notifications_disabled))
                if module is None:
                    self.not_imported_filters.append(f[1])
                    continue
                filterModules.append(module)
                filterFiles.remove(f)
                shouldContinue |= True

        displayNames = []
        for m in filterModules:
            while m.displayName in displayNames:
                m.displayName += "_"
            displayNames.append(m)

        filterModules = filter(lambda mod: hasattr(mod, "perform"), filterModules)
        self.filterModules = collections.OrderedDict(sorted(
            [(FilterTool.moduleDisplayName(x), x) for x in filterModules],
            key=lambda module_name: (module_name[0].lower(),
                                     module_name[1])))

    @staticmethod
    def moduleDisplayName(module):
        subFolderString = getattr(module, 'foldersForDisplayName', "")
        subFolderString = subFolderString if len(subFolderString) < 1 else subFolderString + " "
        name = getattr(module, "displayName", module.__name__)
        return subFolderString + _(name[0].upper() + name[1:])

    @property
    def filterNames(self):
        return [FilterTool.moduleDisplayName(module) for module in self.filterModules.itervalues()]


#-# WIP. Reworking on the filters translations.
#-# The 'new_method' variable is used to select the latest working code or the actual under development one.
#-# This variable must be on False when releasing unless the actual code is fully working.

new_method = True

def tryImport_old(_root, name, org_lang, stock=False, subFolderString="", unicode_name=False, notify=True):
    with open(os.path.join(_root, name)) as module_file:
        module_name = name.split(os.path.sep)[-1].replace(".py", "")
        try:
            if unicode_name:
                source_code = module_file.read()
                module = imp.new_module(module_name)
                exec (source_code, module.__dict__)
                if module_name not in sys.modules.keys():
                    sys.modules[module_name] = module
            else:
                module = imp.load_source(module_name, os.path.join(_root, name), module_file)
            module.foldersForDisplayName = subFolderString
            if not (hasattr(module, 'displayName')):
                module.displayName = module_name  # Python is awesome
            if not stock:
                if "trn" in sys.modules.keys():
                    del sys.modules["trn"]
                if "albow.translate" in sys.modules.keys():
                    del sys.modules["albow.translate"]
                from albow import translate as trn
                if directories.getFiltersDir() in name:
                    trn_path = os.path.split(name)[0]
                else:
                    trn_path = directories.getFiltersDir()
                trn_path = os.path.join(trn_path, subFolderString[1:-1], module_name)
                module.trn = trn
                if os.path.exists(trn_path):
                    module.trn.setLangPath(trn_path)
                    module.trn.buildTranslation(config.settings.langCode.get())
                    n = module.displayName
                    if hasattr(module, "trn"):
                        n = module.trn._(module.displayName)
                    if n == module.displayName:
                        n = _(module.displayName)
                    module.displayName = n
                import albow.translate
                albow.translate.lang = org_lang
            return module

        except Exception as e:
            traceback.print_exc()
            if notify:
                alert(_(u"Exception while importing filter module {}. " +
                        u"See console for details.\n\n{}").format(name, e))
            return None

def tryImport_new(_root, name, org_lang, stock=False, subFolderString="", unicode_name=False, notify=True):
    with open(os.path.join(_root, name)) as module_file:
        module_name = name.split(os.path.sep)[-1].replace(".py", "")
        try:
            if unicode_name:
                source_code = module_file.read()
                module = imp.new_module(module_name)
                exec (source_code, module.__dict__)
                if module_name not in sys.modules.keys():
                    sys.modules[module_name] = module
            else:
                module = imp.load_source(module_name, os.path.join(_root, name), module_file)
            module.foldersForDisplayName = subFolderString
            if not (hasattr(module, 'displayName')):
                module.displayName = module_name  # Python is awesome
            if not stock:
                # This work fine with custom filters, but the choice buttons are broken for the stock ones...
                if directories.getFiltersDir() in name:
                    trn_path = os.path.split(name)[0]
                else:
                    trn_path = directories.getFiltersDir()
                trn_path = os.path.join(trn_path, subFolderString[1:-1], module_name)
                if os.path.exists(trn_path):
                    albow.translate.buildTranslation(config.settings.langCode.get(), extend=True, langPath=trn_path)
#                     module.trn = albow.translate
                    module.displayName = _(module.displayName)
            module.trn = albow.translate
            return module

        except Exception as e:
            traceback.print_exc()
            if notify:
                alert(_(u"Exception while importing filter module {}. " +
                        u"See console for details.\n\n{}").format(name, e))
            return None

if new_method:
    tryImport = tryImport_new
else:
    tryImport = tryImport_old
