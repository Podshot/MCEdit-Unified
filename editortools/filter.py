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
#-# Modified by D.C.-G. for translation purpose
import collections
import os
import traceback
import uuid
from albow import FloatField, IntField, AttrRef, Row, Label, Widget, TabPanel, CheckBox, Column, Button, TextFieldWrapped
import albow.translate
_ = albow.translate._
from config import config
from editortools.blockview import BlockButton
from editortools.editortool import EditorTool
from glbackground import Panel
from mceutils import ChoiceButton, alertException, setWindowCaption, showProgress, TextInputRow
import mcplatform
from operation import Operation
from albow.dialogs import wrapped_label, alert, Dialog
import pymclevel
from pymclevel import BoundingBox
import urllib2
import urllib
import json
import shutil
import directories
import sys
import mceutils


def alertFilterException(func):
    def _func(*args, **kw):
        try:
            func(*args, **kw)
        except Exception, e:
            print traceback.format_exc()
            alert(_(u"Exception during filter operation. See console for details.\n\n{0}").format(e))

    return _func


def addNumField(page, optionName, oName, val, min=None, max=None, increment=0.1):
    if isinstance(val, float):
        ftype = FloatField
        if isinstance(increment, int):
            increment = float(increment)
    else:
        ftype = IntField
        if increment == 0.1:
            increment = 1
        if isinstance(increment, float):
            increment = int(round(increment))

    if min == max:
        min = None
        max = None

    field = ftype(value=val, width=100, min=min, max=max)
    field._increment = increment
    page.optionDict[optionName] = AttrRef(field, 'value')

    row = Row([Label(oName, doNotTranslate=True), field])
    return row


class FilterModuleOptions(Widget):
    is_gl_container = True

    def __init__(self, tool, module, *args, **kw):
        self._parent = None
        if '_parent' in kw.keys():
            self._parent = kw.pop('_parent')
        Widget.__init__(self, *args, **kw)
        self.spacing = 2
        self.tool = tool
        self.pages = pages = TabPanel()
        pages.is_gl_container = True
        self.optionDict = {}

        self.giveEditorObject(module)
        print "Creating options for ", module
        if hasattr(module, "inputs"):
            trn = getattr(module, "trn", None)
            if isinstance(module.inputs, list):
                pgs = []
                for tabData in module.inputs:
                    title, page, pageRect = self.makeTabPage(self.tool, tabData, trn=trn)
                    pgs.append((title, page))
                pages.set_parent(None)
                self.pages = pages = TabPanel(pgs)
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

    def makeTabPage(self, tool, inputs, trn=None):
        page = Widget()
        page.is_gl_container = True
        rows = []
        cols = []
        max_height = self.tool.editor.mainViewport.height - self.tool.editor.toolbar.height - self._parent.filterSelectRow.height - self._parent.confirmButton.height - self.pages.tab_height
        page.optionDict = {}
        page.tool = tool
        title = "Tab"

        for optionName, optionType in inputs:
            if trn is not None:
                oName = trn._(optionName)
            else:
                oName = _(optionName)
            if isinstance(optionType, tuple):
                if isinstance(optionType[0], (int, long, float)):
                    if len(optionType) == 3:
                        val, min, max = optionType
                        increment = 0.1
                    elif len(optionType) == 2:
                        min, max = optionType
                        val = min
                        increment = 0.1
                    elif len(optionType) == 4:
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
                                except:
                                    pass

                                key = splitWord[0]
                                if v is not None:
                                    if key == "width":
                                        wid = v
                                else:
                                    if key == "value":
                                        val = splitWord[1]

                        if val is None:
                            val = ""
                        if wid is None:
                            wid = 200

                        field = TextFieldWrapped(value=val, width=wid)
                        page.optionDict[optionName] = AttrRef(field, 'value')

                        row = Row((Label(oName, doNotTranslate=True), field))
                        rows.append(row)
                    else:
                        isChoiceButton = True

                    if isChoiceButton:
                        if trn is not None:
                            __ = trn._
                        else:
                            __ = _
                        choices = [__("%s"%a) for a in optionType]
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
                input = None  # not sure how to pull values from filters, but leaves it open for the future. Use this variable to set field width.
                if input is not None:
                    size = input
                else:
                    size = 200
                field = TextFieldWrapped(value="")
                row = TextInputRow(oName, ref=AttrRef(field, 'value'), width=size, doNotTranslate=True)
                page.optionDict[optionName] = AttrRef(field, 'value')
                rows.append(row)

            elif optionType == "title":
                title = oName

            else:
                raise ValueError(("Unknown option type", optionType))

        height = sum(r.height for r in rows) + (len(rows) -1) * self.spacing

        if height > max_height:
            h = 0
            for i, r in enumerate(rows):
                h += r.height
                if h > height / 2:
                    break
            cols.append(Column(rows[:i], spacing=0))
            rows = rows[i:]

        if len(rows):
            cols.append(Column(rows, spacing=0))

        if len(cols):
            page.add(Row(cols, spacing=0))
        page.shrink_wrap()

        return title, page, page._rect

    @property
    def options(self):
        return dict((k, v.get()) for k, v in self.optionDict.iteritems())

    @options.setter
    def options(self, val):
        for k in val:
            if k in self.optionDict:
                self.optionDict[k].set(val[k])

    def giveEditorObject(self, module):
        module.editor = self.tool.editor


class FilterToolPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self)

        self.savedOptions = {}
        self._recording = False
        self._save_macro = False

        self.tool = tool
        self.selectedFilterName = None
        self.usingMacro = False
        if len(self.tool.filterModules):
            self.reload()

    def reload(self):
        for i in list(self.subwidgets):
            self.remove(i)

        tool = self.tool

        if len(tool.filterModules) is 0:
            self.add(Label("No filter modules found!"))
            self.shrink_wrap()
            return

        if self.selectedFilterName is None or self.selectedFilterName not in tool.filterNames:
            self.selectedFilterName = tool.filterNames[0]
        
        tool.names_list = []
        for name in tool.filterNames:
            if name.startswith("[Macro]"):
                name = name.replace("[Macro]", "")
            tool.names_list.append(name)
        if os.path.exists(os.path.join(directories.getCacheDir(), "macros.json")):
            self.macro_json = json.load(open(os.path.join(directories.getCacheDir(), "macros.json"), 'rb'))
            for saved_macro in self.macro_json["Macros"].keys():
                name = "[Macro] "+saved_macro
                tool.names_list.append(name)
        self.filterSelect = ChoiceButton(tool.names_list, choose=self.filterChanged, doNotTranslate=True)
        self.filterSelect.selectedChoice = self.selectedFilterName
        
        if not self._recording:
            self.macro_button = Button("Record a Macro", action=self.start_record_macro)

        filterLabel = Label("Filter:", fg_color=(177, 177, 255, 255))
        filterLabel.mouse_down = lambda x: mcplatform.platform_open(directories.getFiltersDir())
        filterLabel.tooltipText = "Click to open filters folder"
        self.filterSelectRow = filterSelectRow = Row((filterLabel, self.filterSelect, self.macro_button))
        
        if not self._recording:
            self.confirmButton = Button("Filter", action=self.tool.confirm)

        self.filterOptionsPanel = None
        while self.filterOptionsPanel is None:
            module = self.tool.filterModules[self.selectedFilterName]
            try:
                self.filterOptionsPanel = FilterModuleOptions(self.tool, module, _parent=self)
            except Exception, e:
                alert(_("Error creating filter inputs for {0}: {1}").format(module, e))
                traceback.print_exc()
                self.tool.filterModules.pop(self.selectedFilterName)
                self.selectedFilterName = tool.filterNames[0]

            if len(tool.filterNames) == 0:
                raise ValueError("No filters loaded!")

        self.add(Column((filterSelectRow, self.filterOptionsPanel, self.confirmButton)))
#        self.filterOptionsPanel.top = (filterSelectRow.bottom - self.filterOptionsPanel.top) / 2 + filterSelectRow.height

        self.shrink_wrap()
        if self.parent:
            self.centery = self.parent.centery

        if self.selectedFilterName in self.savedOptions:
            self.filterOptionsPanel.options = self.savedOptions[self.selectedFilterName]

    def run_macro(self):
        self.tool.run_macro(self.macro_data)

    def reload_macro(self):
        self.usingMacro = True
        for i in list(self.subwidgets):
            self.remove(i)
        self.macro_data = self.macro_json["Macros"][self.selectedFilterName.replace("[Macro] ", "")]
        self.filterOptionsPanel = None
        filterLabel = Label("Filter:", fg_color=(177, 177, 255, 255))
        filterLabel.mouse_down = lambda x: mcplatform.platform_open(directories.getFiltersDir())
        filterLabel.tooltipText = "Click to open filters folder"
        self.filterSelectRow = filterSelectRow = Row((filterLabel, self.filterSelect, self.macro_button))
        self.confirmButton = Button("Run Macro", action=self.run_macro)
        
        self.filterOptionsPanel = Widget()
        infoColList = []
        stepsLabel = wrapped_label("Number of steps: "+str(self.macro_data["Number of steps"]), 300)
        infoColList.append(stepsLabel)
        for step in sorted(self.macro_data.keys()):
            if step != "Number of steps":
                infoColList.append(wrapped_label("Step "+str(int(step)+1)+": "+str(self.macro_data[step]["Name"]),300))
        self.filterOptionsPanel.add(Column(infoColList))
        self.filterOptionsPanel.shrink_wrap()
        
        self.add(Column((filterSelectRow, self.filterOptionsPanel, self.confirmButton)))

        self.shrink_wrap()
        if self.parent:
            self.centery = self.parent.centery

    def filterChanged(self):
        if not self.filterSelect.selectedChoice.startswith("[Macro]"):
            self.saveOptions()
            self.selectedFilterName = self.filterSelect.selectedChoice
            self.reload()
        else:
            self.saveOptions()
            self.selectedFilterName = self.filterSelect.selectedChoice
            self.reload_macro()

    def set_save(self):
        self._save_macro = True
        self.macro_diag.dismiss()

    def stop_record_macro(self):
        
        self.macro_diag = Dialog()
        macroNameLabel = Label("Macro Name: ")
        macroNameField = TextFieldWrapped()
        input_row = Row((macroNameLabel, macroNameField))
        saveButton = Button("Save", action=self.set_save)
        closeButton = Button("Close", action=self.macro_diag.dismiss)
        button_row = Row((saveButton, closeButton))
        self.macro_diag.add(Column((input_row, button_row)))
        self.macro_diag.shrink_wrap()
        self.macro_diag.present()
        self.macro_button.text = "Record a Macro"
        self.macro_button.tooltipText = ""
        self.macro_button.action = self.start_record_macro
        self._recording = False
        if self._save_macro:
            if os.path.exists(os.path.join(directories.getCacheDir(), "macros.json")):
                try:
                    macro_dict = json.load(open(os.path.join(directories.getCacheDir(), "macros.json"), 'rb'))
                except ValueError:
                    macro_dict = {"Macros": {}}
            else:
                macro_dict = {"Macros": {}}
            macro_dict["Macros"][macroNameField.get_text()] = {}
            macro_dict["Macros"][macroNameField.get_text()]["Number of steps"] = len(self.macro_steps)
            for entry in self.macro_steps:
                for inp in entry["Inputs"].keys():
                    if isinstance(entry["Inputs"][inp], pymclevel.materials.Block) or entry["Inputs"][inp] == "blocktype":
                        entry["Inputs"][inp] = "block-"+str(entry["Inputs"][inp].ID)+":"+str(entry["Inputs"][inp].blockData)
                macro_dict["Macros"][macroNameField.get_text()][entry["Step"]] = {"Name":entry["Name"],"Inputs":entry["Inputs"]}
            with open(os.path.join(directories.getCacheDir(), "macros.json"), 'w') as f:
                json.dump(macro_dict, f)
        self.reload()

    def start_record_macro(self):
        self.macro_steps = []
        self.current_step = 0
        self.macro_button.text = "Stop recording"
        self.macro_button.tooltipText = "Currently recording a macro"
        self.macro_button.action = self.stop_record_macro
        self.confirmButton = Button("Add macro", action=self.tool.confirm)
        self._recording = True
    
    def addMacroStep(self, name=None, inputs=None):
        data = {"Name": name, "Step": self.current_step, "Inputs": inputs}
        self.current_step += 1
        self.macro_steps.append(data)

    filterOptionsPanel = None

    def saveOptions(self):
        if self.filterOptionsPanel and not self.usingMacro:
            self.savedOptions[self.selectedFilterName] = self.filterOptionsPanel.options


class FilterOperation(Operation):
    def __init__(self, editor, level, box, filter, options, panel):
        super(FilterOperation, self).__init__(editor, level)
        self.box = box
        self.filter = filter
        self.options = options
        self.canUndo = False
        self.panel = panel
        self.wasMacroOperation = False

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self.box)
        
        if not self.panel._recording:
            self.filter.perform(self.level, BoundingBox(self.box), self.options)
        else:
            self.panel.addMacroStep(name=self.panel.filterSelect.selectedChoice, inputs=self.options)
            self.wasMacroOperation = True

        self.canUndo = True
        pass

    def dirtyBox(self):
        return self.box


class FilterTool(EditorTool):
    tooltipText = "Filter"
    toolIconName = "filter"

    def __init__(self, editor):
        EditorTool.__init__(self, editor)

        self.filterModules = {}

        self.updatePanel = Panel()
        updateButton = Button("Update Filters", action=self.updateFilters)
        self.updatePanel.add(updateButton)
        self.updatePanel.shrink_wrap()

        self.updatePanel.bottomleft = self.editor.viewportContainer.bottomleft

        self.panel = FilterToolPanel(self)

    @property
    def statusText(self):
        return "Choose a filter, then click Filter or press Enter to apply it."

    def toolEnabled(self):
        return not (self.selectionBox() is None)

    def toolSelected(self):
        self.showPanel()

    @alertException
    def showPanel(self):
        if self.panel.parent:
            self.editor.remove(self.panel)

        self.updatePanel.bottomleft = self.editor.viewportContainer.bottomleft
        self.editor.add(self.updatePanel)
        self.reloadFilters()

        self.panel.reload()

        self.panel.midleft = self.editor.midleft

        self.editor.add(self.panel)

    def hidePanel(self):
        if not self.panel.usingMacro:
            self.panel.saveOptions()
        if self.panel.parent:
            self.panel.parent.remove(self.panel)
            self.updatePanel.parent.remove(self.updatePanel)

    def updateFilters(self):
        totalFilters = 0
        updatedFilters = 0
        filtersDir = directories.getFiltersDir()
        try:
            os.mkdir(os.path.join(filtersDir, "updates"))
        except OSError:
            pass
        for module in self.filterModules.values():
            totalFilters += 1
            if hasattr(module, "UPDATE_URL") and hasattr(module, "VERSION"):
                if isinstance(module.UPDATE_URL, (str, unicode)) and isinstance(module.VERSION, (str, unicode)):
                    versionJSON = json.loads(urllib2.urlopen(module.UPDATE_URL).read())
                    if module.VERSION != versionJSON["Version"]:
                        urllib.urlretrieve(versionJSON["Download-URL"],
                                           os.path.join(filtersDir, "updates", versionJSON["Name"]))
                        updatedFilters += 1
        for f in os.listdir(os.path.join(filtersDir, "updates")):
            shutil.copy(os.path.join(filtersDir, "updates", f), filtersDir)
        shutil.rmtree(os.path.join(filtersDir, "updates"))
        self.finishedUpdatingWidget = Widget()
        lbl = Label("Updated %s filter(s) out of %s"%(updatedFilters, totalFilters))
        closeBTN = Button("Close this message", action=self.closeFinishedUpdatingWidget)
        col = Column((lbl, closeBTN))
        self.finishedUpdatingWidget.bg_color = (0.0, 0.0, 0.6)
        self.finishedUpdatingWidget.add(col)
        self.finishedUpdatingWidget.shrink_wrap()
        self.finishedUpdatingWidget.present()

    def closeFinishedUpdatingWidget(self):
        self.finishedUpdatingWidget.dismiss()

    def reloadFilters(self):
        if self.filterModules:
            for k, m in self.filterModules.iteritems():
                del m
            mceutils.compareMD5Hashes(directories.getAllOfAFile(directories.filtersDir, ".py"))

        def tryImport(name):
            try:
                m = __import__(name)
                listdir = os.listdir(os.path.join(directories.getDataDir(), "stock-filters"))
                if name + ".py" not in listdir or name + ".pyc" not in listdir or name + ".pyo" not in listdir:
                    if "albow.translate" in sys.modules.keys():
                        del sys.modules["albow.translate"]
                    if "trn" in sys.modules.keys():
                        del sys.modules["trn"]
                    import albow.translate as trn
                    trn_path = os.path.join(directories.getFiltersDir(), name)
                    if os.path.exists(trn_path):
                        trn.setLangPath(trn_path)
                        trn.buildTranslation(config.settings.langCode.get())
                    m.trn = trn
                return m
            except Exception, e:
                print traceback.format_exc()
                alert(_(u"Exception while importing filter module {}. See console for details.\n\n{}").format(name, e))
                return object()

        filterModules = (tryImport(x[:-3]) for x in filter(lambda x: x.endswith(".py"), os.listdir(directories.getFiltersDir())))
        filterModules = filter(lambda module: hasattr(module, "perform"), filterModules)
        self.filterModules = collections.OrderedDict(sorted((self.moduleDisplayName(x), x) for x in filterModules))
        for n, m in self.filterModules.iteritems():
            try:
                reload(m)
            except Exception, e:
                print traceback.format_exc()
                alert(
                    _(u"Exception while reloading filter module {}. Using previously loaded module. See console for details.\n\n{}").format(
                        m.__file__, e))

    @property
    def filterNames(self):
        return [self.moduleDisplayName(module) for module in self.filterModules.itervalues()]

    @staticmethod
    def moduleDisplayName(module):
        if hasattr(module, "displayName"):
            if hasattr(module, "trn"):
                return module.trn._(module.displayName)
            else:
                return module.displayName
        else:
            return module.__name__.capitalize()

    @alertFilterException
    def confirm(self):

        with setWindowCaption("APPLYING FILTER - "):
            filterModule = self.filterModules[self.panel.filterSelect.selectedChoice]

            op = FilterOperation(self.editor, self.editor.level, self.selectionBox(), filterModule,
                                 self.panel.filterOptionsPanel.options, self.panel)

            self.editor.level.showProgress = showProgress
            
            self.editor.addOperation(op)
            if not op.wasMacroOperation:
                if op.canUndo:
                    self.editor.addUnsavedEdit()

                self.editor.invalidateBox(self.selectionBox())
            
    @alertFilterException
    def run_macro(self, macro_steps):
        
        with setWindowCaption("APPYLING FILTER MACRO - "):
            for step in sorted(macro_steps.keys()):
                if step != "Number of steps":
                    modul = self.filterModules[macro_steps[step]["Name"]]
                    for minput in macro_steps[step]["Inputs"].keys():
                        if isinstance(macro_steps[step]["Inputs"][minput], (str, unicode)):
                            if macro_steps[step]["Inputs"][minput].startswith("block-"):
                                toFind = macro_steps[step]["Inputs"][minput].replace("block-","").split(":")
                                for possible in pymclevel.alphaMaterials.allBlocks:
                                    if possible.ID == int(toFind[0]) and possible.blockData == int(toFind[1]):
                                        macro_steps[step]["Inputs"][minput] = possible
                    op = FilterOperation(self.editor, self.editor.level, self.selectionBox(), modul,
                                         macro_steps[step]["Inputs"], self.panel)
                    
                    self.editor.level.showProgress = showProgress
                    
                    self.editor.addOperation(op)
                    self.editor.addUnsavedEdit()
                    self.editor.invalidateBox(self.selectionBox())
