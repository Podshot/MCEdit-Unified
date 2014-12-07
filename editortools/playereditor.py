from albow import Label, TextField, Row, TableView, TableColumn, Column, Grid, Widget, Button, ButtonBase, AttrRef, theme
from glbackground import Panel
from albow.dialogs import Dialog
from albow import resource
from pymclevel.items import items
import thumbview
from blockview import BlockButton
from itemview import ItemButton
from glbackground import GLBackground


class Item(ButtonBase, Widget):
    is_gl_container = True

    _active = False

    def __init__(self, inv, slot, rect=None, **kwds):
        self.inv = inv
        self.slot = slot
        kwds['action'] = lambda x=self: inv.selectSlot(x)
        Widget.__init__(self, size=(48, 48), **kwds)

        background = GLBackground()
        #background.bg_color = [i / 255. for i in theme.root.Button.enabled_bg_color]
        background.anchor = "tlbr"
        background.size = self.size

        try:
            id_ = [[x["id"].value, x["Damage"].value] for x in inv.playerInv if x["Slot"].value == slot][0]
        except:
            id_ = ["minecraft:air", 0]

        id_[0] = items.getNewId(id_[0])

        self.thumb = thumbview.ItemThumbView(inv.materials, id_[0], id_[1], size=self.size)
        self.add(background)
        self.add(self.thumb)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, v):
        if v:
            self.select()
        else:
            self.deselect()
        #self.activate()
    

    def select(self):
        self._active = True
        self.thumb.bg_color = (255, 255, 0)
        if self.thumb.is_gl_container:
            self.thumb.setAsBlock() #Is there a better way to rerender?
    def deselect(self):
        self._active = False
        self.thumb.bg_color = theme.root.ItemThumbView.bg_color
        if self.thumb.is_gl_container:
            self.thumb.setAsBlock() #Is there a better way to rerender?

    def editslot(self, slot):
        if self.active:
            self.deselect()
        else:
            self.select()

class Inventory(Dialog):
    is_gl_container = True
    def __init__(self, player, playerTag, materials, *a, **kw):
        Dialog.__init__(self, *a, **kw)
        d_old = self.margin
        d = self.margin = 2

        totalRows = 9
        totalColumns = 9

        self.size = (totalColumns*(48+d) + 5*d, totalRows*(48+d)+ 5*d)
        self.playerTag = playerTag
        self.player = player
        self.materials = materials

        self.click_outside_response = 0


        self.playerInv = playerTag["Inventory"]
        self.inv = []
        self.hotbar = []
        self.armor = []
        for slot in range(9, 36):
            self.inv.insert(slot, Item(self, slot))

        self.inv  = zip(*[iter(self.inv)]*9)

        for slot in range(9):
            self.hotbar.insert(slot, Item(self, slot))

        for slot in range(103, 99, -1):
            self.armor.insert(slot, Item(self, slot))

        
        background = GLBackground()
        background.bg_color = [i / 255. for i in self.bg_color]
        background.anchor = "tlbr"
        background.size = self.size

        lbl = Label(self.player)

        armorbar = Column(self.armor, spacing=d, align='c')
        options = ItemButton(self.materials)

        top = Row([armorbar, options], spacing=d, align='c')

        invgrid = Grid(self.inv, row_spacing=d, column_spacing=d)
        #stat = Row([health, xp, hunger], spacing=d, align='c')
        #xpbar = None
        hotbarrow = Row(self.hotbar, spacing=d, align='c')

        #col = Column([lbl, top, invgrid, stat, xpbar, hotbarrow], spacing=d, align='c')
        col = Column([lbl, top, invgrid, hotbarrow], spacing=d, align='c')

        self.add(background)
        self.add(col)

        self.shrink_wrap()

    def selectSlot(self, selSlot):
        for row in self.inv:
            for slot in row:
                if slot.slot != selSlot.slot and slot.active:
                    slot.deselect()
        for slot in self.hotbar:
            if slot.slot != selSlot.slot and slot.active:
                slot.deselect()
        for slot in self.armor:
            if slot.slot != selSlot.slot and slot.active:
                slot.deselect()
        selSlot.select()
    

