from albow import Label, TextField, Row, TableView, TableColumn, Column, Grid, Widget, Button, ImageButton, AttrRef
from albow.dialogs import Dialog
from albow import resource


class Item(ImageButton):
     def __init__(self, slot, item, image=None, rect=None, **kwds):
        kwds['action'] = lambda x=slot: self.editslot(x)
        Widget.__init__(self, rect, **kwds)
        if image:
            if isinstance(image, basestring):
                image = resource.get_image(image, prefix="")
            w, h = image.get_size()
            d = 2 * self.margin
            self.size = w + d, h + d
            self._image = image
            self.slot = slot

class Inventory(Dialog):

    def __init__(self, player, playerTag, *a, **kw):
        Dialog.__init__(self, *a, **kw)
        self.playerTag = playerTag
        self.player = player

        d = self.margin

        self.click_outside_response = 0

        playerInv = playerTag["Inventory"]
        inv = []
        hotbar = []
        for slot in range(27):
            try:
                inv.insert(slot, Item(slot, [x for x in playerInv if x["Slot"].value == slot][0], "../char.png"))
            except:
                inv.insert(slot, Item(slot, None, "char.png"))

        inv  = zip(*[iter(inv)]*9)

        for slot in range(9):
            try:
                hotbar.insert(slot, Item(slot, [x for x in playerInv if x["Slot"].value == slot][0], "../char.png"))
            except:
                hotbar.insert(slot, Item(slot, None, "char.png"))


        lbl = Label(self.player)

        #top = Row([armor, skin, options], spacing=d, align='c')
        invgrid = Grid(inv, row_spacing=d, column_spacing=d)
        #stat = Row([health, xp, hunger], spacing=d, align='c')
        #xpbar = None
        hotbarrow = Row(hotbar, spacing=d, align='c')

        #col = Column([lbl, top, invgrid, stat, xpbar, hotbarrow], spacing=d, align='c')
        col = Column([lbl, invgrid, hotbarrow], spacing=d, align='c')

        self.add(col)
        self.shrink_wrap()
