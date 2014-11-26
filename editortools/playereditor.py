from albow import Label, TextField, Row, TableView, TableColumn, Column, Grid, Widget, Button, ButtonBase, AttrRef
from glbackground import Panel
from albow.dialogs import Dialog
from albow import resource
from pymclevel.items import items
import thumbview
from glbackground import GLBackground


class Item(ButtonBase, Widget):
    is_gl_container = True
    def __init__(self, inv, slot, rect=None, **kwds):
        self.inv = inv
        kwds['action'] = lambda x=slot: self.editslot(x)
        Widget.__init__(self, size=(48, 48), **kwds)
        try:
            id_ = [[x["id"].value, x["Damage"].value] for x in inv.playerInv if x["Slot"].value == slot][0]
        except:
            id_ = ["minecraft:air", 0]

        id_[0] = items.getNewId(id_[0])

        self.thumb = thumbview.ItemThumbView(inv.materials, id_[0], id_[1], size=(48, 48))
        self.thumb.size = (48, 48)
        self.add(self.thumb)

    def editslot(self, slot):
        print(slot)

class Inventory(Dialog):
    is_gl_container = True
    def __init__(self, player, playerTag, materials, *a, **kw):
        Dialog.__init__(self, *a, **kw)
        d = self.margin
        self.size = (9*48+9*d, 5*48+9*d)
        self.playerTag = playerTag
        self.player = player
        self.materials = materials

        d = self.margin

        self.click_outside_response = 0


        self.playerInv = playerTag["Inventory"]
        inv = []
        hotbar = []
        for slot in range(9, 36):
            inv.insert(slot, Item(self, slot))

        inv  = zip(*[iter(inv)]*9)

        for slot in range(9):
            hotbar.insert(slot, Item(self, slot))

        
        background = GLBackground()
        background.bg_color = [i / 255. for i in self.bg_color]
        background.anchor = "tlbr"
        background.size = self.size

        lbl = Label(self.player)

        #top = Row([armor], spacing=d, align='c')

        invgrid = Grid(inv, row_spacing=d, column_spacing=d)
        #stat = Row([health, xp, hunger], spacing=d, align='c')
        #xpbar = None
        hotbarrow = Row(hotbar, spacing=d, align='c')

        #col = Column([lbl, top, invgrid, stat, xpbar, hotbarrow], spacing=d, align='c')
        col = Column([lbl, invgrid, hotbarrow], spacing=d, align='c')

        self.add(background)
        self.add(col)

        self.shrink_wrap()

