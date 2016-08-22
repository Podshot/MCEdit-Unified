# -*- coding: utf-8 -*-
#
# Albow - File Dialogs
#
#-# Modified by D.C.-G. for translation purpose

"""
TODO:

* Implement Windows support.
"""

import os, sys
from pygame import event, image
from pygame.transform import scale
from pygame.locals import *
from albow.widget import Widget
from albow.dialogs import Dialog, ask, alert
from albow.controls import Label, Button, Image
from albow.extended_widgets import ChoiceButton
from albow.fields import TextFieldWrapped
from albow.layout import Row, Column
from albow.palette_view import PaletteView # @Unused
from albow.scrollpanel import ScrollPanel
from albow.theme import ThemeProperty
from translate import _
from tree import Tree
import logging
log = logging.getLogger(__name__)


DEBUG = True

if DEBUG:
    from albow.resource import get_image

    def get_imgs():
        """Load an return the images used as file and folder icons."""
        print "*** MCEDIT DEBUG: file_dialog:", __file__
        print "*** MCEDIT DEBUG: directory:", os.path.dirname(__file__)
        print "*** MCEDIT DEBUG: current directory:", os.getcwd()
        try:
            file_image = get_image('file.png', prefix='')
            folder_image = get_image('folder.png', prefix='')
        except Exception, e:
            print "MCEDIT DEBUG: Could not load file dialog images."
            print e
            from pygame import draw, Surface
            from pygame.locals import SRCALPHA
            from math import pi
            file_image = Surface((16, 16), SRCALPHA)
            file_image.fill((0,0,0,0))
            draw.lines(file_image, (255, 255, 255, 255), False, [[3, 15], [3, 1], [13, 1]], 2)
            draw.line(file_image, (255, 255, 255, 255), [3, 7], [10, 7], 2)
            folder_image = Surface((16, 16), SRCALPHA)
            folder_image.fill((0,0,0,0))
            draw.line(folder_image, (255, 255, 255, 255), [3, 15], [3, 1], 2)
            draw.arc(folder_image, (255, 255, 255, 255), [0, 1, 13, 15], 0, pi/1.9, 2)
            draw.arc(folder_image, (255, 255, 255, 255), [0, 1, 13, 15], 3*pi/2, 2*pi, 2)
        return file_image, folder_image

else:
    from directories import getDataDir

    if sys.platform in ('darwin', 'linux2'):
        print "*** MCEDIT DEBUG: file_dialog:", __file__
        print "*** MCEDIT DEBUG: directory:", os.path.dirname(__file__)
        print "*** MCEDIT DEBUG: current directory:", os.getcwd()
        try:
            file_image = image.load('file.png')
            folder_image = image.load('folder.png')
        except Exception, e:
            print "MCEDIT DEBUG: Could not load file dialog images."
            print e
            from pygame import draw, Surface
            from pygame.locals import SRCALPHA
            from math import pi
            file_image = Surface((16, 16), SRCALPHA)
            file_image.fill((0,0,0,0))
            draw.lines(file_image, (255, 255, 255, 255), False, [[3, 15], [3, 1], [13, 1]], 2)
            draw.line(file_image, (255, 255, 255, 255), [3, 7], [10, 7], 2)
            folder_image = Surface((16, 16), SRCALPHA)
            folder_image.fill((0,0,0,0))
            draw.line(folder_image, (255, 255, 255, 255), [3, 15], [3, 1], 2)
            draw.arc(folder_image, (255, 255, 255, 255), [0, 1, 13, 15], 0, pi/1.9, 2)
            draw.arc(folder_image, (255, 255, 255, 255), [0, 1, 13, 15], 3*pi/2, 2*pi, 2)
    else: # windows
        file_image = image.load(os.path.join(getDataDir(), 'file.png'))
        folder_image = image.load(os.path.join(getDataDir(), 'folder.png'))

class DirPathView(Widget):
    def __init__(self, width, client, **kwds):
        Widget.__init__(self, **kwds)
        self.set_size_for_text(width)
        self.client = client

    def draw(self, surf):
        frame = self.get_margin_rect()
        image = self.font.render(self.client.directory, True, self.fg_color)
        tw = image.get_width()
        mw = frame.width
        if tw <= mw:
            x = 0
        else:
            x = mw - tw
        surf.blit(image, (frame.left + x, frame.top))


class FileListView(ScrollPanel):

    def __init__(self, width, client, **kwds):
        font = self.predict_font(kwds)
        h = font.get_linesize()
        d = 2 * self.predict(kwds, 'margin')
        kwds['align'] = kwds.get('align', 'l')
        ScrollPanel.__init__(self, inner_width=width, **kwds)

        if DEBUG:
            file_image, folder_image = get_imgs()

        self.icons = {True: scale(folder_image, (self.row_height, self.row_height)), False: scale(file_image, (self.row_height, self.row_height))}
        self.client = client
        self.names = []

    def update(self):
        client = self.client
        dir = client.directory

        def filter(name):
            path = os.path.join(dir, name)
            return os.path.isdir(path) or self.client.filter(path)

        try:
            content = os.walk(dir)
            for a, dirnames, filenames in content:
                dirnames.sort()
                filenames.sort()
                break
            try:
                self.names = [unicode(name, 'utf-8') for name in dirnames + filenames if filter(name)]
            except:
                self.names = [name for name in dirnames + filenames if filter(name)]
        except EnvironmentError, e:
            alert(u"%s: %s" % (dir, e))
            self.names = []
        self.rows = [Row([Image(self.icons[os.path.isdir(os.path.join(dir, a))]),
                          Label(a, margin=0)], margin=0, spacing=2) for a in self.names]
        self.selected_item_index = None
        self.scroll_to_item(0)

    def scroll_to_item(self, *args, **kwargs):
        self.scrollRow.scroll_to_item(*args, **kwargs)

    def num_items(self):
        return len(self.names)

    def click_item(self, item_no, e):
        self.selected_item_index = item_no
        ScrollPanel.click_item(self, item_no, e)
        if e.num_clicks == 2:
            self.client.dir_box_click(True)

    def item_is_selected(self, item_no):
        return item_no == self.selected_item_index

    def get_selected_name(self):
        sel = self.selected_item_index
        if sel is not None:
            return self.names[sel]
        else:
            return ""


def get_platform_root_dir():
    #-# Rework this in order to mimic the OSs file chooser behaviour.
    #-# Need platform/version specific code...
    return '/'


class FSTree(Tree):
    def __init__(self, client, *args, **kwargs):
        kwargs['draw_zebra'] = False
        self.client = client
        self.directory = get_platform_root_dir()
        self.content = content = os.walk(self.directory)
        if client is not None and hasattr(client, 'directory'):
            self.directory = client.directory
        self.directory = kwargs.pop('directory', self.directory)
        self.data = data = {}
        d = {}
        for dirpath, dirnames, filenames in content:
            for name in dirnames:
                d[name] = self.parse_path(name, os.path.join(dirpath, name))
            data[dirpath] = d
            break
        kwargs['data'] = data
        Tree.__init__(self, *args, **kwargs)
        del self.menu
        self.set_directory(self.directory)

    def show_menu(self, *args, **kwargs):
        return

    def set_directory(self, directory):
        self.diretory = directory
        self.deployed = []
        splitted_path = directory.split(os.sep)
        while '' in splitted_path:
            splitted_path.remove('')
        splitted_path.insert(0, '/')
        d = self.data
        path = ""
        while splitted_path:
            name = splitted_path.pop(0)
            path = os.path.join(path, name)
            d[name] = self.parse_path(name, path)
            rows = self.build_layout()
            i = 0
            for row in rows:
                if row[3] == name and self.get_item_path(row) in directory:
                    self.deployed.append(row[6])
                    self.clicked_item = row
                    rows[i + 1:] = self.build_layout()[i + 1:]
                    if directory == self.get_item_path(row):
                        self.treeRow.scroll_to_item(rows.index(row))
                        self.selected_item_index = rows.index(row)
                        self.selected_item = row
                        break
                i += 1
            d = d[name]

    def parse_path(self, name, path):
        #!# The log.debug() and print stuff in there are intended to fix some OSX issues.
        #!# Please do not strip them out. -- D.C.-G.
#        log.debug('FSTree.parse_path')
#        log.debug('    path: %s\n      length: %d'%(repr(path), len(path)))
#        print '    path: %s\n      length: %d'%(repr(path), len(path))
#        log.debug('    path: %s\n      length: %d'%(repr(path), len(path)))
#        if len(path) < 1: print '    ! ! ! ^ ^ ^ ! ! !'
#        if len(path) < 1: log.debug('    ! ! ! ^ ^ ^ ! ! !')
        content = os.walk(path)
        data = {}
        d = data
        for a, folders, b in content:
#            log.debug('    a: %s\n      length: %d'%(repr(a), len(a)))
#            print '    a: %s\n      length: %d'%(repr(a), len(a))
#            log.debug('    a: %s\n      length: %d'%(repr(a), len(a)))
#            if len(a) < 1: print '    ! ! ! ^ ^ ^ ! ! !'
#            if len(a) < 1: log.debug('    ! ! ! ^ ^ ^ ! ! !')
            d = {}
            for folder in folders:
#                log.debug('    folder: %s\n      length: %d'%(repr(folder), len(folder)))
#                print '    folder: %s\n      length: %d'%(repr(folder), len(folder))
#                log.debug('    folder: %s\n      length: %d'%(repr(folder), len(folder)))
#                if len(folder) < 1: print '    ! ! ! ^ ^ ^ ! ! !'
#                if len(folder) < 1: log.debug('    ! ! ! ^ ^ ^ ! ! !')
                if type(folder) == str:
                    folder = unicode(folder, 'utf-8')
                d[folder] = {}
                if type(a) == str:
                    a = unicode(a,'utf-8')
                cont = os.walk(os.path.join(a, folder))
                for _a, fs, _b in cont:
                    for f in fs:
#                        log.debug('    f: %s\n      length: %d'%(repr(f), len(f)))
#                        print '    f: %s\n      length: %d'%(repr(f), len(f))
#                        log.debug('    f: %s\n      length: %d'%(repr(f), len(f)))
#                        if len(f) < 1: print '    ! ! ! ^ ^ ^ ! ! !'
#                        if len(f) < 1: log.debug('    ! ! ! ^ ^ ^ ! ! !')
                        if type(f) == str:
                            d[folder][unicode(f, 'utf-8')] = {}
                        else:
                            d[folder][f] = {}
                    break
            break
        return d

    def get_item_path(self, item):
        path_list = []
        if item is not None:
            id = item[6]
            parents = [item]
            while id != 1:
                item = self.get_item_parent(parents[-1])
                if item is None:
                    break
                id = item[6]
                parents.append(item)
            parents.reverse()
            path_list = [a[3] for a in parents]
        path = '/'
        for name in path_list:
            path = os.path.join(path, name)
        return path

    def deploy(self, id):
        path = self.get_item_path(self.clicked_item)
        self.clicked_item[9] = self.parse_path(self.clicked_item[3], path)
        Tree.deploy(self, id)

    def select_item(self, n):
        Tree.select_item(self, n)
        self.client.directory = self.get_item_path(self.selected_item)

class FileDialog(Dialog):
    box_width = 450
    default_prompt = None
    up_button_text = ThemeProperty("up_button_text")

    def __init__(self, prompt=None, suffixes=None, **kwds):
        Dialog.__init__(self, **kwds)
        label = None
        d = self.margin
        self.suffixes = suffixes or ("",)
        self.file_type = self.suffixes[0]
        up_button = Button(self.up_button_text, action=self.go_up)
        dir_box = DirPathView(self.box_width + 250, self)
        self.dir_box = dir_box
        top_row = Row([dir_box, up_button])
        list_box = FileListView(self.box_width - 16, self)
        self.list_box = list_box
        tree = FSTree(self, inner_width=250, directory='/')
        self.tree = tree
        row = Row((tree, list_box), margin=0)
        ctrls = [top_row, row]
        prompt = prompt or self.default_prompt
        if prompt:
            label = Label(prompt)
        if suffixes:
            filetype_label = Label("File type", width=250)

            def set_file_type():
                self.file_type = self.filetype_button.get_value()
                self.list_box.update()

            filetype_button = ChoiceButton(choices=self.suffixes, width=250, choose=set_file_type)
            self.filetype_button = filetype_button
        if self.saving:
            filename_box = TextFieldWrapped(self.box_width)
            filename_box.change_action = self.update_filename
            filename_box._enter_action = filename_box.enter_action
            filename_box.enter_action = self.enter_action
            self.filename_box = filename_box
            if suffixes:
                ctrls.append(Row([Column([label, filename_box], align='l', spacing=0),
                                  Column([filetype_label, filetype_button], align='l', spacing=0)
                                  ],
                                 )
                             )
            else:
                ctrls.append(Column([label, filename_box], align='l', spacing=0))
        else:
            if label:
                ctrls.insert(0, label)
            if suffixes:
                ctrls.append(Column([filetype_label, filetype_button], align='l', spacing=0))
        ok_button = Button(self.ok_label, action=self.ok, enable=self.ok_enable)
        self.ok_button = ok_button
        cancel_button = Button("Cancel", action=self.cancel)
        vbox = Column(ctrls, align='l', spacing=d)
        vbox.topleft = (d, d)
        y = vbox.bottom + d
        ok_button.topleft = (vbox.left, y)
        cancel_button.topright = (vbox.right, y)
        self.add(vbox)
        self.add(ok_button)
        self.add(cancel_button)
        self.shrink_wrap()
        self._directory = None
        self.directory = os.getcwdu()
        #print "FileDialog: cwd =", repr(self.directory) ###
        if self.saving:
            filename_box.focus()

    def get_directory(self):
        return self._directory

    def set_directory(self, x):
        x = os.path.abspath(x)
        while not os.path.exists(x):
            y = os.path.dirname(x)
            if y == x:
                x = os.getcwdu()
                break
            x = y
        if self._directory != x:
            self._directory = x
            self.list_box.update()
            self.update()

    directory = property(get_directory, set_directory)

    def filter(self, path):
        if os.path.isdir(path) or path.endswith(self.file_type.lower()) or self.file_type == '.*':
            return True

    def update(self):
        self.tree.set_directory(self.directory)

    def update_filename(self):
        if self.filename_box.text in self.list_box.names:
            self.directory = os.path.join(self.directory, self.filename_box.text)

    def go_up(self):
        self.directory = os.path.dirname(self.directory)
        self.list_box.scroll_to_item(0)

    def dir_box_click(self, double):
        if double:
            name = self.list_box.get_selected_name()
            path = os.path.join(self.directory, name)
            suffix = os.path.splitext(name)[1]
            if suffix not in self.suffixes and os.path.isdir(path):
                self.directory = path
            else:
                self.double_click_file(name)
        self.update()

    def enter_action(self):
        self.filename_box._enter_action()
        self.ok()

    def ok(self):
        self.dir_box_click(True)
        #self.dismiss(True)

    def cancel(self):
        self.dismiss(False)

    def key_down(self, evt):
        k = evt.key
        if k == K_RETURN or k == K_KP_ENTER:
            self.dir_box_click(True)
        if k == K_ESCAPE:
            self.cancel()


class FileSaveDialog(FileDialog):
    saving = True
    default_prompt = "Save as:"
    ok_label = "Save"

    def get_filename(self):
        return self.filename_box.text

    def set_filename(self, x):
        dsuf = self.file_type
        if dsuf and x.endswith(dsuf):
            x = x[:-len(dsuf)]
        self.filename_box.text = x

    filename = property(get_filename, set_filename)

    def get_pathname(self):
        path = os.path.join(self.directory, self.filename_box.text)
        suff = self.file_type
        if suff and not path.endswith(suff):
            path = path + suff
        return path

    pathname = property(get_pathname)

    def double_click_file(self, name):
        self.filename_box.text = name

    def ok(self):
        path = self.pathname
        if os.path.exists(path):
            answer = ask(_("Replace existing '%s'?") % os.path.basename(path))
            if answer != "OK":
                return
        #FileDialog.ok(self)
        self.dismiss(True)

    def update(self):
        FileDialog.update(self)

    def ok_enable(self):
        return self.filename_box.text != ""


class FileOpenDialog(FileDialog):
    saving = False
    ok_label = "Open"

    def get_pathname(self):
        name = self.list_box.get_selected_name()
        if name:
            return os.path.join(self.directory, name)
        else:
            return None

    pathname = property(get_pathname)

    #def update(self):
    #    FileDialog.update(self)

    def ok_enable(self):
        path = self.pathname
        enabled = self.item_is_choosable(path)
        return enabled

    def item_is_choosable(self, path):
        return bool(path) and self.filter(path)

    def double_click_file(self, name):
        self.dismiss(True)


class LookForFileDialog(FileOpenDialog):
    target = None

    def __init__(self, target, **kwds):
        FileOpenDialog.__init__(self, **kwds)
        self.target = target

    def item_is_choosable(self, path):
        return path and os.path.basename(path) == self.target

    def filter(self, name):
        return name and os.path.basename(name) == self.target


def request_new_filename(prompt=None, suffix=None, extra_suffixes=None,
                         directory=None, filename=None, pathname=None):
    if pathname:
        directory, filename = os.path.split(pathname)
    if extra_suffixes:
        suffixes = extra_suffixes
    else:
        suffixes = []
    if suffix:
        suffixes = [suffix] + suffixes
    dlog = FileSaveDialog(prompt=prompt, suffixes=suffixes)
    if directory:
        dlog.directory = directory
    if filename:
        dlog.filename = filename
    if dlog.present():
        return dlog.pathname
    else:
        return None


def request_old_filename(suffixes=None, directory=None):
    dlog = FileOpenDialog(suffixes=suffixes)
    if directory:
        dlog.directory = directory
    if dlog.present():
        return dlog.pathname
    else:
        return None


def look_for_file_or_directory(target, prompt=None, directory=None):
    dlog = LookForFileDialog(target=target, prompt=prompt)
    if directory:
        dlog.directory = directory
    if dlog.present():
        return dlog.pathname
    else:
        return None
