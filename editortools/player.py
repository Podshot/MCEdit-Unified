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
#-# Modifiedby D.C.-G. for translation purpose
from OpenGL import GL
import numpy
import os
from albow import TableView, TableColumn, Label, Button, Column, CheckBox, AttrRef, Row, ask, alert, input_text_buttons, TabPanel
from albow.table_view import TableRowView
from albow.translate import _
from config import config
from editortools.editortool import EditorTool
from editortools.tooloptions import ToolOptions
from glbackground import Panel
from glutils import DisplayList
from mceutils import loadPNGTexture, alertException, drawTerrainCuttingWire, drawCube
from operation import Operation
import pymclevel
from pymclevel.box import BoundingBox, FloatBox
from pymclevel import nbt
import logging
from version_utils import PlayerCache
from nbtexplorer import loadFile, saveFile, NBTExplorerToolPanel
import pygame

log = logging.getLogger(__name__)

class PlayerRemoveOperation(Operation):
    undoTag = None

    def __init__(self, tool, player="Player (Single Player)"):
        super(PlayerRemoveOperation, self).__init__(tool.editor, tool.editor.level)
        self.tool = tool
        self.player = player
        self.level = self.tool.editor.level
        self.canUndo = False
        self.playercache = PlayerCache()

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return

        if self.player == "Player (Single Player)":
            answer = ask(_("Are you sure you want to delete the default player?"), ["Yes", "Cancel"])
            if answer == "Cancel":
                return
            self.player = "Player"

        if recordUndo:
            self.undoTag = self.level.getPlayerTag(self.player)

        self.level.players.remove(self.player)
        if self.tool.panel:
            if self.player != "Player":
                #self.tool.panel.players.remove(version_utils.getPlayerNameFromUUID(self.player))
                #self.tool.panel.players.remove(self.playercache.getPlayerInfo(self.player)[0])
                str()
            else:
                self.tool.panel.players.remove("Player (Single Player)")

            while self.tool.panel.table.index >= len(self.tool.panel.players):
                self.tool.panel.table.index -= 1
            #if len(self.tool.panel.players) == 0:
            #    self.tool.hidePanel()
            #    self.tool.showPanel()
            self.tool.hidePanel()
            self.tool.showPanel()
        self.tool.markerList.invalidate()
        self.tool.movingPlayer = None

        pos = self.tool.revPlayerPos[self.editor.level.dimNo][self.player]
        del self.tool.playerPos[self.editor.level.dimNo][pos]
        if self.player != "Player":
            del self.tool.playerTexture[self.player]
        else:
            del self.level.root_tag["Data"]["Player"]
        del self.tool.revPlayerPos[self.editor.level.dimNo][self.player]
        self.canUndo = True

    def undo(self):
        if not (self.undoTag is None):
            if self.player != "Player":
                self.level.playerTagCache[self.level.getPlayerPath(self.player)] = self.undoTag
            else:
                self.level.root_tag["Data"]["Player"] = self.undoTag

            self.level.players.append(self.player)
            if self.tool.panel:
                #if self.player != "Player":
                #    self.tool.panel.players.append(self.playercache.getPlayerInfo(self.player)[0])
                #else:
                #    self.tool.panel.players.append("Player (Single Player)")

                if "[No players]" in self.tool.panel.players:
                    self.tool.panel.players.remove("[No players]")
                self.tool.hidePanel()
                self.tool.showPanel()

        self.tool.markerList.invalidate()

    def redo(self):
        self.perform()


class PlayerAddOperation(Operation):
    playerTag = None

    def __init__(self, tool):
        super(PlayerAddOperation, self).__init__(tool.editor, tool.editor.level)
        self.tool = tool
        self.level = self.tool.editor.level
        self.canUndo = False
        self.playercache = PlayerCache()

    def perform(self, recordUndo=True):
        initial = ""
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
        while True:
            self.player = input_text_buttons("Enter a Player Name: ", 160, initial=initial, allowed_chars=allowed_chars)
            if self.player is None:
                return
            elif len(self.player) > 16:
                alert("Name too long. Maximum name length is 16.")
                initial = self.player
            elif len(self.player) < 1:
                alert("Name too short. Minimum name length is 1.")
                initial = self.player
            else:
                break
            
        data = self.playercache.getPlayerInfo(self.player)
        if "<Unknown UUID>" not in data:
            self.uuid = data[0]
            self.player = data[1]
        else:
            action = ask("Could not get {}'s UUID. Please make sure that you are connected to the internet and that the player \"{}\" exists.".format(self.player, self.player), ["Enter UUID manually", "Cancel"])
            if action != "Enter UUID manually":
                return
            self.uuid = input_text_buttons("Enter a Player UUID: ", 160)
            if not self.uuid:
                return
            self.player = self.playercache.getPlayerFromUUID(self.uuid)
            if self.player == self.uuid.replace("-", ""):
                if ask("UUID was not found. Continue anyways?") == "Cancel":
                    return
        if self.uuid in self.level.players:
            alert("Player already exists in this World.")
            return

        self.playerTag = self.newPlayer()

        #if self.tool.panel:
        #    self.tool.panel.players.append(self.player)

        if self.level.oldPlayerFolderFormat:
            self.level.playerTagCache[self.level.getPlayerPath(self.player)] = self.playerTag
            
            self.level.players.append(self.player)
            #if self.tool.panel:
                #self.tool.panel.player_UUID[self.player] = self.player

        else:
            self.level.playerTagCache[self.level.getPlayerPath(self.uuid)] = self.playerTag
            
            self.level.players.append(self.uuid)
            if self.tool.panel:
                self.tool.panel.player_UUID["UUID"].append(self.uuid)
                self.tool.panel.player_UUID["Name"].append(self.player)

        self.tool.playerPos[self.editor.level.dimNo][(0,0,0)] = self.uuid
        self.tool.revPlayerPos[self.editor.level.dimNo][self.uuid] = (0,0,0)
        self.tool.playerTexture[self.uuid] = loadPNGTexture(self.playercache.getPlayerSkin(self.uuid, force_download=False))
        self.tool.markerList.invalidate()
        self.tool.recordMove = False
        self.tool.movingPlayer = self.uuid
        if self.tool.panel:
            self.tool.hidePanel()
            self.tool.showPanel()
        self.canUndo = True
        self.playerTag.save(self.level.getPlayerPath(self.uuid))
        self.tool.nonSavedPlayers.append(self.level.getPlayerPath(self.uuid))
        self.tool.inOtherDimension[self.editor.level.dimNo].append(self.uuid)

    def newPlayer(self):
        playerTag = nbt.TAG_Compound()

        playerTag['Air'] = nbt.TAG_Short(300)
        playerTag['AttackTime'] = nbt.TAG_Short(0)
        playerTag['DeathTime'] = nbt.TAG_Short(0)
        playerTag['Fire'] = nbt.TAG_Short(-20)
        playerTag['Health'] = nbt.TAG_Short(20)
        playerTag['HurtTime'] = nbt.TAG_Short(0)
        playerTag['Score'] = nbt.TAG_Int(0)
        playerTag['FallDistance'] = nbt.TAG_Float(0)
        playerTag['OnGround'] = nbt.TAG_Byte(0)
        playerTag['Dimension'] = nbt.TAG_Int(self.editor.level.dimNo)

        playerTag["Inventory"] = nbt.TAG_List()

        playerTag['Motion'] = nbt.TAG_List([nbt.TAG_Double(0) for i in range(3)])
        spawn = self.level.playerSpawnPosition()
        spawnX = spawn[0]
        spawnZ = spawn[2]
        blocks = [self.level.blockAt(spawnX, i, spawnZ) for i in range(self.level.Height)]
        i = self.level.Height
        done = False
        for index, b in enumerate(reversed(blocks)):
            if b != 0 and not done:
                i = index
                done = True
        spawnY = self.level.Height - i
        playerTag['Pos'] = nbt.TAG_List([nbt.TAG_Double([spawnX, spawnY, spawnZ][i]) for i in range(3)])
        playerTag['Rotation'] = nbt.TAG_List([nbt.TAG_Float(0), nbt.TAG_Float(0)])

        return playerTag

    def undo(self):
        self.level.players.remove(self.uuid)
        self.tool.movingPlayer = None
        if self.tool.panel:
            #self.tool.panel.players.remove(self.player)
            self.tool.panel.player_UUID["UUID"].remove(self.uuid)
            self.tool.panel.player_UUID["Name"].remove(self.player)
            self.tool.hidePanel()
            self.tool.showPanel()
        if self.tool.movingPlayer is None:
            del self.tool.playerPos[self.tool.revPlayerPos[self.uuid]]
        else:
            del self.tool.playerPos[(0,0,0)]
        del self.tool.revPlayerPos[self.uuid]
        del self.tool.playerTexture[self.uuid]
        os.remove(self.level.getPlayerPath(self.uuid))
        if self.level.getPlayerPath(self.uuid) in self.tool.nonSavedPlayers:
            self.tool.nonSavedPlayers.remove(self.level.getPlayerPath(self.uuid))

        self.tool.markerList.invalidate()

    def redo(self):
        if not (self.playerTag is None):
            self.level.playerTagCache[self.level.getPlayerPath(self.uuid)] = self.playerTag

            self.level.players.append(self.uuid)
            if self.tool.panel:
                #self.tool.panel.players.append(self.uuid)
                #self.tool.panel.player_UUID[self.player] = self.uuid
                self.tool.panel.player_UUID["UUID"].append(self.uuid)
                self.tool.panel.player_UUID["Name"].append(self.player)
            self.tool.playerTexture[self.uuid] = loadPNGTexture(self.playercache.getPlayerSkin(self.uuid))
            self.tool.playerPos[(0,0,0)] = self.uuid
            self.tool.revPlayerPos[self.uuid] = (0,0,0)
            self.playerTag.save(self.level.getPlayerPath(self.uuid))
            self.tool.nonSavedPlayers.append(self.level.getPlayerPath(self.uuid))

        self.tool.markerList.invalidate()


class PlayerMoveOperation(Operation):
    undoPos = None
    redoPos = None

    def __init__(self, tool, pos, player="Player", yp=(None, None)):
        super(PlayerMoveOperation, self).__init__(tool.editor, tool.editor.level)
        self.tool = tool
        self.canUndo = False
        self.pos = pos
        self.player = player
        self.yp = yp

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return
        try:
            level = self.tool.editor.level
            try:
                self.undoPos = level.getPlayerPosition(self.player)
                self.undoDim = level.getPlayerDimension(self.player)
                self.undoYP = level.getPlayerOrientation(self.player)
            except Exception, e:
                log.info(_("Couldn't get player position! ({0!r})").format(e))

            yaw, pitch = self.yp
            if yaw is not None and pitch is not None:
                level.setPlayerOrientation((yaw, pitch), self.player)
            level.setPlayerPosition(self.pos, self.player)
            level.setPlayerDimension(level.dimNo, self.player)
            self.tool.playerPos[tuple(self.pos)] = self.player
            self.tool.revPlayerPos[self.player] = self.pos
            self.tool.markerList.invalidate()
            self.canUndo = True

        except pymclevel.PlayerNotFound, e:
            print "Player move failed: ", e

    def undo(self):
        if not (self.undoPos is None):
            level = self.tool.editor.level
            try:
                self.redoPos = level.getPlayerPosition(self.player)
                self.redoDim = level.getPlayerDimension(self.player)
                self.redoYP = level.getPlayerOrientation(self.player)
            except Exception, e:
                log.info(_("Couldn't get player position! ({0!r})").format(e))
            level.setPlayerPosition(self.undoPos, self.player)
            level.setPlayerDimension(self.undoDim, self.player)
            level.setPlayerOrientation(self.undoYP, self.player)
            self.tool.markerList.invalidate()

    def redo(self):
        if not (self.redoPos is None):
            level = self.tool.editor.level
            try:
                self.undoPos = level.getPlayerPosition(self.player)
                self.undoDim = level.getPlayerDimension(self.player)
                self.undoYP = level.getPlayerOrientation(self.player)
            except Exception, e:
                log.info(_("Couldn't get player position! ({0!r})").format(e))
            level.setPlayerPosition(self.redoPos, self.player)
            level.setPlayerDimension(self.redoDim, self.player)
            level.setPlayerOrientation(self.redoYP, self.player)
            self.tool.markerList.invalidate()

    @staticmethod
    def bufferSize():
        return 20


class SpawnPositionInvalid(Exception):
    pass


def okayAt63(level, pos):
    """blocks 63 or 64 must be occupied"""
    # return level.blockAt(pos[0], 63, pos[2]) != 0 or level.blockAt(pos[0], 64, pos[2]) != 0
    return True


def okayAboveSpawn(level, pos):
    """3 blocks above spawn must be open"""
    return not any([level.blockAt(pos[0], pos[1] + i, pos[2]) for i in range(1, 4)])


def positionValid(level, pos):
    try:
        return okayAt63(level, pos) and okayAboveSpawn(level, pos)
    except EnvironmentError:
        return False


class PlayerSpawnMoveOperation(Operation):
    undoPos = None
    redoPos = None

    def __init__(self, tool, pos):
        super(PlayerSpawnMoveOperation, self).__init__(tool.editor, tool.editor.level)
        self.tool, self.pos = tool, pos
        self.canUndo = False

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert(_("Cannot perform action while saving is taking place"))
            return
        level = self.tool.editor.level
        '''
        if isinstance(level, pymclevel.MCInfdevOldLevel):
            if not positionValid(level, self.pos):
                if config.spawn.spawnProtection.get():
                    raise SpawnPositionInvalid(
                        "You cannot have two air blocks at Y=63 and Y=64 in your spawn point's column. Additionally, you cannot have a solid block in the three blocks above your spawn point. It's weird, I know.")
        '''

        self.undoPos = level.playerSpawnPosition()
        level.setPlayerSpawnPosition(self.pos)
        self.tool.markerList.invalidate()
        self.canUndo = True

    def undo(self):
        if self.undoPos is not None:
            level = self.tool.editor.level
            self.redoPos = level.playerSpawnPosition()
            level.setPlayerSpawnPosition(self.undoPos)
            self.tool.markerList.invalidate()

    def redo(self):
        if self.redoPos is not None:
            level = self.tool.editor.level
            self.undoPos = level.playerSpawnPosition()
            level.setPlayerSpawnPosition(self.redoPos)
            self.tool.markerList.invalidate()


class PlayerPositionPanel(Panel):
    def __init__(self, tool):
        Panel.__init__(self, name='Panel.PlayerPositionPanel')
        self.tool = tool
        self.player_UUID = {"UUID": [], "Name": []}
        self.level = tool.editor.level
        self.playercache = PlayerCache()
        
        if hasattr(self.level, 'players'):
            players = self.level.players or ["[No players]"]
            if not self.level.oldPlayerFolderFormat:
                for player in players:
                    if player != "Player" and player != "[No players]":
                        if len(player) > 4 and player[4] == "-":
                            os.rename(os.path.join(self.level.worldFolder.getFolderPath("playerdata"), player+".dat"), os.path.join(self.level.worldFolder.getFolderPath("playerdata"), player.replace("-", "", 1)+".dat"))
                            player = player.replace("-", "", 1)
                        data = self.playercache.getPlayerInfo(player, use_old_data=True)
                        #self.player_UUID[data[0]] = data[1]
                        self.player_UUID["UUID"].append(data[0])
                        self.player_UUID["Name"].append(data[1])
                        #self.player_UUID[player] = data
                if "Player" in players:
                    #self.player_UUID["Player (Single Player)"] = "Player"
                    self.player_UUID["UUID"].append("Player")
                    self.player_UUID["Name"].append("Player (Single Player)")
                if "[No players]" not in players:
                    self.player_names = sorted(self.player_UUID.values(), key=lambda x: False if x == "Player (Single Player)" else x)
                else:
                    self.player_UUID["UUID"].append("[No players]")
                    self.player_UUID["Name"].append("[No players]")

        else:
            players = ["Player (Single Player)"]
        self.players = players

        self.pages = TabPanel()
        tab_height = self.pages.tab_height

        max_height = tab_height + self.tool.editor.mainViewport.height - self.tool.editor.toolbar.height - self.tool.editor.subwidgets[0].height - self.pages.margin * 2
        #-# Uncomment the following line to have a maximum height for this panel.
        # max_height = min(max_height, 500)

        self.editNBTDataButton = Button("Edit NBT", action=self.editNBTData, tooltipText="Open the NBT Explorer to edit player's attributes and inventory")
        addButton = Button("Add", action=self.tool.addPlayer)
        removeButton = Button("Remove", action=self.tool.removePlayer)
        gotoButton = Button("Goto", action=self.tool.gotoPlayer)
        gotoCameraButton = Button("Goto View", action=self.tool.gotoPlayerCamera)
        moveButton = Button("Move", action=self.tool.movePlayer)
        moveToCameraButton = Button("Align to Camera", action=self.tool.movePlayerToCamera)
        reloadSkin = Button("Reload Skins", action=self.tool.reloadSkins, tooltipText="This pulls skins from the online server, so this may take a while")

        btns = [self.editNBTDataButton]
        if not isinstance(self.level, pymclevel.leveldbpocket.PocketLeveldbWorld):
            btns.extend([addButton, removeButton])
        btns.extend([gotoButton, gotoCameraButton, moveButton, moveToCameraButton, reloadSkin])
        btns = Column(btns, margin=0, spacing=2)
        h = max_height - btns.height - self.pages.margin * 2 - 2 - self.font.get_linesize() * 2

        col = Label('')

        def close():
            self.pages.show_page(col)
        self.nbttree = NBTExplorerToolPanel(self.tool.editor, nbtObject={}, height=max_height, \
                                            close_text="Go Back", no_header=True, close_action=close,
                                            load_text=None)
        self.nbttree.shrink_wrap()

        self.nbtpage = Column([self.nbttree])
        self.nbtpage.shrink_wrap()
        self.pages.add_page("NBT Data", self.nbtpage)
        self.pages.set_rect(map(lambda x:x+self.margin, self.nbttree._rect))

        tableview = TableView(nrows=(h - (self.font.get_linesize() * 2.5)) / self.font.get_linesize(),
                              header_height=self.font.get_linesize(),
                              columns=[TableColumn("Player Name(s):", (self.nbttree.width - (self.margin * 3)) / 3),
                                       TableColumn("Player UUID(s):", (self.nbttree.width - (self.margin * 3)))],
                              )
        tableview.index = 0
        tableview.num_rows = lambda: len(self.player_UUID["UUID"])
        tableview.row_data = lambda i: (self.player_UUID["Name"][i],self.player_UUID["UUID"][i])
        tableview.row_is_selected = lambda x: x == tableview.index
        tableview.zebra_color = (0, 0, 0, 48)

        def selectTableRow(i, evt):
            tableview.index = i

        tableview.click_row = selectTableRow

        def mouse_down(e):
            if e.button == 1 and e.num_clicks > 1:
                self.editNBTData()
            TableRowView.mouse_down(tableview.rows, e)

        tableview.rows.mouse_down = mouse_down

        tableview.rows.tooltipText = "Double-click or use the button below to edit the NBT Data."

        self.table = tableview

        col.set_parent(None)
        self.col = col = Column([tableview, btns], spacing=2)

        self.pages.add_page("Players", col, 0)

        self.pages.shrink_wrap()
        self.pages.show_page(col)
        self.add(self.pages)
        self.shrink_wrap()
        self.max_height = max_height

    def editNBTData(self):
        player = self.selectedPlayer
        if player == 'Player (Single Player)':
            alert("Not yet implemented.\nUse the NBT Explorer to edit this player.")
        elif player == '[No players]':
            return
        else:
            player = self.level.getPlayerTag(self.selectedPlayer)
            if player is not None:
                self.pages.remove_page(self.nbtpage)

                def close():
                    self.pages.show_page(self.col)

                self.nbttree = NBTExplorerToolPanel(self.tool.editor, nbtObject=player, fileName=None,
                                              savePolicy=-1, dataKeyName=None,
                                              height=self.max_height, no_header=True, close_text="Go Back",
                                              close_action=close, load_text=None,
                                              copy_data=False)

                self.nbtpage = Column([self.nbttree,])
                self.nbtpage.shrink_wrap()
                self.pages.add_page("NBT Data", self.nbtpage)
                self.pages.show_page(self.nbtpage)
            else:
                alert(_("Unable to load player %s" % self.selectedPlayer()))

    @property
    def selectedPlayer(self):
        if not self.level.oldPlayerFolderFormat:
            player = self.players[self.table.index]
            if player != "Player (Single Player)" and player != "[No players]":
                return self.player_UUID["UUID"][self.table.index]
            else:
                return player
        else:
            return self.players[self.table.index]

    def key_down(self, evt):
        self.dispatch_key('key_down', evt)

    def dispatch_key(self, name, evt):
        if not hasattr(evt, 'key'):
            return
        if name == "key_down":
            keyname = self.root.getKey(evt)
            if self.pages.current_page == self.col:
                if keyname == "Up" and self.table.index > 0:
                    self.table.index -= 1
                    self.table.rows.scroll_to_item(self.table.index)
                elif keyname == "Down" and self.table.index < len(self.players) - 1:
                    self.table.index += 1
                    self.table.rows.scroll_to_item(self.table.index)
                elif keyname == 'Page down':
                    self.table.index = min(len(self.players) - 1, self.table.index + self.table.rows.num_rows())
                elif keyname == 'Page up':
                    self.table.index = max(0, self.table.index - self.table.rows.num_rows())
                elif keyname == 'Return':
                    if self.selectedPlayer != None:
                        self.editNBTData()
                if self.table.rows.cell_to_item_no(0, 0) + self.table.rows.num_rows() -1 > self.table.index or self.table.rows.cell_to_item_no(0, 0) + self.table.rows.num_rows() -1 < self.table.index:
                    self.table.rows.scroll_to_item(self.table.index)
            elif self.pages.current_page == self.nbtpage:
                self.nbttree.dispatch_key(name, evt)


class PlayerPositionTool(EditorTool):
    surfaceBuild = True
    toolIconName = "player"
    tooltipText = "Players"
    movingPlayer = None
    recordMove = True

    def reloadTextures(self):
        self.charTex = loadPNGTexture('char.png')

    @alertException
    def addPlayer(self):
        op = PlayerAddOperation(self)

        self.editor.addOperation(op)
        if op.canUndo:
            self.editor.addUnsavedEdit()

    @alertException
    def removePlayer(self):
        player = self.panel.selectedPlayer

        if player != "[No players]":
            op = PlayerRemoveOperation(self, player)

            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    @alertException
    def movePlayer(self):
        if self.panel.selectedPlayer != "[No players]":
            self.movingPlayer = self.panel.selectedPlayer
            if self.movingPlayer == "Player (Single Player)":
                self.movingPlayer = "Player"

    @alertException
    def movePlayerToCamera(self):
        player = self.panel.selectedPlayer
        if player == "Player (Single Player)":
            player = "Player"
        if player != "[No players]":
            pos = self.editor.mainViewport.cameraPosition
            y = self.editor.mainViewport.yaw
            p = self.editor.mainViewport.pitch

            op = PlayerMoveOperation(self, pos, player, (y, p))
            self.movingPlayer = None
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()

    def delete_skin(self, uuid):
        del self.playerTexture[uuid]
        self.playerTexture[uuid] = self.charTex

    @alertException
    def reloadSkins(self):
        #result = ask("This pulls skins from the online server, so this may take a while", ["Ok", "Cancel"])
        #if result == "Ok":
        try:
            for player in self.editor.level.players:
                if player != "Player" and player in self.playerTexture.keys():
                    del self.playerTexture[player]
                    self.playerTexture[player] = loadPNGTexture(self.playercache.getPlayerSkin(player, force_download=True, instance=self))
            #self.markerList.call(self._drawToolMarkers)
        except:
            raise Exception("Could not connect to the skins server, please check your Internet connection and try again.")

    def gotoPlayerCamera(self):
        player = self.panel.selectedPlayer
        if player == "Player (Single Player)":
            player = "Player"

        try:
            pos = self.editor.level.getPlayerPosition(player)
            y, p = self.editor.level.getPlayerOrientation(player)
            self.editor.gotoDimension(self.editor.level.getPlayerDimension(player))

            self.editor.mainViewport.cameraPosition = pos
            self.editor.mainViewport.yaw = y
            self.editor.mainViewport.pitch = p
            self.editor.mainViewport.stopMoving()
            self.editor.mainViewport.invalidate()
        except pymclevel.PlayerNotFound:
            pass

    def gotoPlayer(self):
        player = self.panel.selectedPlayer
        if player == "Player (Single Player)":
            player = "Player"

        try:
            if self.editor.mainViewport.pitch < 0:
                self.editor.mainViewport.pitch = -self.editor.mainViewport.pitch
                self.editor.mainViewport.cameraVector = self.editor.mainViewport._cameraVector()
            cv = self.editor.mainViewport.cameraVector

            pos = self.editor.level.getPlayerPosition(player)
            pos = map(lambda p, c: p - c * 5, pos, cv)
            self.editor.gotoDimension(self.editor.level.getPlayerDimension(player))

            self.editor.mainViewport.cameraPosition = pos
            self.editor.mainViewport.stopMoving()
        except pymclevel.PlayerNotFound:
            pass

    def __init__(self, *args):
        EditorTool.__init__(self, *args)
        self.reloadTextures()
        self.nonSavedPlayers = []

        textureVerticesHead = numpy.array(
            (
                # Backside of Head
                24, 16, # Bottom Left
                24, 8, # Top Left
                32, 8, # Top Right
                32, 16, # Bottom Right

                # Front of Head
                8, 16,
                8, 8,
                16, 8,
                16, 16,

                #
                24, 0,
                16, 0,
                16, 8,
                24, 8,

                #
                16, 0,
                8, 0,
                8, 8,
                16, 8,

                #
                8, 8,
                0, 8,
                0, 16,
                8, 16,

                16, 16,
                24, 16,
                24, 8,
                16, 8,

            ), dtype='f4')
        
        textureVerticesHat = numpy.array(
            (
                56, 16,
                56, 8,
                64, 8,
                64, 16,
                
                48, 16,
                48, 8,
                40, 8,
                40, 16,
                
                56, 0,
                48, 0,
                48, 8,
                56, 8,
                
                48, 0,
                40, 0,
                40, 8,
                48, 8,
                
                40, 8,
                32, 8,
                32, 16,
                40, 16,
                
                48, 16,
                56, 16,
                56, 8,
                48, 8,
                
            ), dtype='f4')
        

        textureVerticesHead.shape = (24, 2)
        textureVerticesHat.shape = (24, 2)

        textureVerticesHead *= 4
        textureVerticesHead[:, 1] *= 2
        
        textureVerticesHat *= 4
        textureVerticesHat[:, 1] *= 2

        self.texVerts = (textureVerticesHead, textureVerticesHat) 

        self.playerPos = {0:{}, -1:{}, 1:{}}
        self.playerTexture = {}
        self.revPlayerPos = {0:{}, -1:{}, 1:{}}
        self.inOtherDimension = {0: [], 1: [], -1: []}
        self.playercache = PlayerCache()

        self.markerList = DisplayList()

    panel = None

    def showPanel(self):
        if not self.panel:
            self.panel = PlayerPositionPanel(self)

        self.panel.centery = (self.editor.mainViewport.height - self.editor.toolbar.height) / 2 + self.editor.subwidgets[0].height
        self.panel.left = self.editor.left

        self.editor.add(self.panel)

    def hidePanel(self):
        if self.panel and self.panel.parent:
            self.panel.parent.remove(self.panel)
        self.panel = None

    def drawToolReticle(self):
        if self.movingPlayer is None:
            return

        pos, direction = self.editor.blockFaceUnderCursor
        dim = self.editor.level.getPlayerDimension(self.movingPlayer)
        pos = (pos[0], pos[1] + 2, pos[2])

        x, y, z = pos

        # x,y,z=map(lambda p,d: p+d, pos, direction)
        GL.glEnable(GL.GL_BLEND)
        GL.glColor(1.0, 1.0, 1.0, 0.5)
        self.drawCharacterHead(x + 0.5, y + 0.75, z + 0.5, self.revPlayerPos[dim][self.movingPlayer], dim)
        GL.glDisable(GL.GL_BLEND)

        GL.glEnable(GL.GL_DEPTH_TEST)
        self.drawCharacterHead(x + 0.5, y + 0.75, z + 0.5, self.revPlayerPos[dim][self.movingPlayer], dim)
        drawTerrainCuttingWire(BoundingBox((x, y, z), (1, 1, 1)))
        drawTerrainCuttingWire(BoundingBox((x, y - 1, z), (1, 1, 1)))
        #drawTerrainCuttingWire( BoundingBox((x,y-2,z), (1,1,1)) )
        GL.glDisable(GL.GL_DEPTH_TEST)

    markerLevel = None

    def drawToolMarkers(self):
        if not config.settings.drawPlayerHeads.get():
            return
        if self.markerLevel != self.editor.level:
            self.markerList.invalidate()
            self.markerLevel = self.editor.level
        self.markerList.call(self._drawToolMarkers)

    def _drawToolMarkers(self):
        GL.glColor(1.0, 1.0, 1.0, 0.5)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        for player in self.editor.level.players:
            try:
                pos = self.editor.level.getPlayerPosition(player)
                yaw, pitch = self.editor.level.getPlayerOrientation(player)
                dim = self.editor.level.getPlayerDimension(player)
                
                self.inOtherDimension[dim].append(player)
                self.playerPos[dim][pos] = player
                self.revPlayerPos[dim][player] = pos
                
                if player != "Player" and config.settings.downloadPlayerSkins.get():
                    self.playerTexture[player] = loadPNGTexture(self.playercache.getPlayerSkin(player, force_download=False))
                else:
                    self.playerTexture[player] = self.charTex
                    
                if dim != self.editor.level.dimNo:
                    continue

                x, y, z = pos
                GL.glPushMatrix()
                GL.glTranslate(x, y, z)
                GL.glRotate(-yaw, 0, 1, 0)
                GL.glRotate(pitch, 1, 0, 0)
                GL.glColor(1, 1, 1, 1)
                self.drawCharacterHead(0, 0, 0, (x,y,z), self.editor.level.dimNo)
                GL.glPopMatrix()
                # GL.glEnable(GL.GL_BLEND)
                drawTerrainCuttingWire(FloatBox((x - .5, y - .5, z - .5), (1, 1, 1)),
                                       c0=(0.3, 0.9, 0.7, 1.0),
                                       c1=(0, 0, 0, 0),
                )

                #GL.glDisable(GL.GL_BLEND)

            except Exception, e:
                print repr(e)
                continue

        GL.glDisable(GL.GL_DEPTH_TEST)

    def drawCharacterHead(self, x, y, z, realCoords=None, dim=0):
        GL.glEnable(GL.GL_CULL_FACE)
        origin = (x - 0.25, y - 0.25, z - 0.25)
        size = (0.5, 0.5, 0.5)
        box = FloatBox(origin, size)
        
        hat_origin = (x - 0.275, y - 0.275, z - 0.275)
        hat_size = (0.55, 0.55, 0.55)
        hat_box = FloatBox(hat_origin, hat_size)

        if realCoords is not None and self.playerPos[dim][realCoords] != "Player" and config.settings.downloadPlayerSkins.get():
            drawCube(box,
                     texture=self.playerTexture[self.playerPos[dim][realCoords]], textureVertices=self.texVerts[0])
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            drawCube(hat_box,
                     texture=self.playerTexture[self.playerPos[dim][realCoords]], textureVertices=self.texVerts[1])
            GL.glDisable(GL.GL_BLEND)
        else:
            drawCube(box,
                     texture=self.charTex, textureVertices=self.texVerts[0])
        GL.glDisable(GL.GL_CULL_FACE)

    #@property
    #def statusText(self):
    #    if not self.panel:
    #        return ""
    #    player = self.panel.selectedPlayer
    #    if player == "Player":
    #        return "Click to move the player"
#
    #    return _("Click to move the player \"{0}\"").format(player)

    @alertException
    def mouseDown(self, evt, pos, direction):
        if self.movingPlayer is None:
            return

        pos = (pos[0] + 0.5, pos[1] + 2.75, pos[2] + 0.5)

        op = PlayerMoveOperation(self, pos, self.movingPlayer)
        self.movingPlayer = None

        if self.recordMove:
            self.editor.addOperation(op)
            addingMoving = False
        else:
            self.editor.performWithRetry(op)  #Prevent recording of Undo when adding player
            self.recordMove = True
            addingMoving = True
        if op.canUndo and not addingMoving:
            self.editor.addUnsavedEdit()

    def keyDown(self, evt):
        keyname = evt.dict.get('keyname', None) or self.editor.get_root().getKey(evt)
        if not self.recordMove:
            if not pygame.key.get_focused():
                return

            if keyname == "Escape":
                self.recordMove = True
        if self.panel and self.panel.__class__ == PlayerPositionPanel:
            self.panel.key_down(evt)

    def keyUp(self, evt):
        pass

    def levelChanged(self):
        self.markerList.invalidate()

    @alertException
    def toolSelected(self):
        self.showPanel()
        self.movingPlayer = None

    @alertException
    def toolReselected(self):
        if self.panel:
            self.gotoPlayer()


class PlayerSpawnPositionOptions(ToolOptions):
    def __init__(self, tool):
        ToolOptions.__init__(self, name='Panel.PlayerSpawnPositionOptions')
        self.tool = tool
        self.spawnProtectionCheckBox = CheckBox(ref=AttrRef(tool, "spawnProtection"))
        self.spawnProtectionLabel = Label("Spawn Position Safety")
        self.spawnProtectionLabel.mouse_down = self.spawnProtectionCheckBox.mouse_down

        tooltipText = "Minecraft will randomly move your spawn point if you try to respawn in a column where there are no blocks at Y=63 and Y=64. Only uncheck this box if Minecraft is changed."
        self.spawnProtectionLabel.tooltipText = self.spawnProtectionCheckBox.tooltipText = tooltipText

        row = Row((self.spawnProtectionCheckBox, self.spawnProtectionLabel))
        col = Column((Label("Spawn Point Options"), row, Button("OK", action=self.dismiss)))

        self.add(col)
        self.shrink_wrap()


class PlayerSpawnPositionTool(PlayerPositionTool):
    surfaceBuild = True
    toolIconName = "playerspawn"
    tooltipText = "Move Spawn Point\nRight-click for options"

    def __init__(self, *args):
        PlayerPositionTool.__init__(self, *args)
        self.optionsPanel = PlayerSpawnPositionOptions(self)

    def toolEnabled(self):
        return self.editor.level.dimNo == 0

    def showPanel(self):
        self.panel = Panel(name='Panel.PlayerSpawnPositionTool')
        button = Button("Goto Spawn", action=self.gotoSpawn)
        self.panel.add(button)
        self.panel.shrink_wrap()

        self.panel.left = self.editor.left
        self.panel.centery = self.editor.centery
        self.editor.add(self.panel)

    def gotoSpawn(self):
        cv = self.editor.mainViewport.cameraVector

        pos = self.editor.level.playerSpawnPosition()
        pos = map(lambda p, c: p - c * 5, pos, cv)

        self.editor.mainViewport.cameraPosition = pos
        self.editor.mainViewport.stopMoving()

    @property
    def statusText(self):
        return "Click to set the spawn position."

    spawnProtection = config.spawn.spawnProtection.property()

    def drawToolReticle(self):
        pos, direction = self.editor.blockFaceUnderCursor
        x, y, z = map(lambda p, d: p + d, pos, direction)

        color = (1.0, 1.0, 1.0, 0.5)
        if isinstance(self.editor.level, pymclevel.MCInfdevOldLevel) and self.spawnProtection:
            if not positionValid(self.editor.level, (x, y, z)):
                color = (1.0, 0.0, 0.0, 0.5)

        GL.glColor(*color)
        GL.glEnable(GL.GL_BLEND)
        self.drawCage(x, y, z)
        self.drawCharacterHead(x + 0.5, y + 0.5, z + 0.5)
        GL.glDisable(GL.GL_BLEND)

        GL.glEnable(GL.GL_DEPTH_TEST)
        self.drawCage(x, y, z)
        self.drawCharacterHead(x + 0.5, y + 0.5, z + 0.5)
        color2 = map(lambda a: a * 0.4, color)
        drawTerrainCuttingWire(BoundingBox((x, y, z), (1, 1, 1)), color2, color)
        GL.glDisable(GL.GL_DEPTH_TEST)

    def _drawToolMarkers(self):
        x, y, z = self.editor.level.playerSpawnPosition()
        
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA);
        GL.glEnable(GL.GL_BLEND);
        
        color = config.selectionColors.black.get() + (0.35,)
        GL.glColor(*color)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
        GL.glLineWidth(2.0)
        drawCube(FloatBox((x, y, z), (1, 1, 1)))
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        drawCube(FloatBox((x, y, z), (1, 1, 1)))
        GL.glDisable(GL.GL_BLEND)
        
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glColor(1.0, 1.0, 1.0, 1.0)
        self.drawCage(x, y, z)
        self.drawCharacterHead(x + 0.5, y + 0.5 + 0.125 * numpy.sin(self.editor.frames * 0.05), z + 0.5)
        GL.glDisable(GL.GL_DEPTH_TEST)

    def drawCage(self, x, y, z):
        cageTexVerts = numpy.array(pymclevel.MCInfdevOldLevel.materials.blockTextures[52, 0])

        pixelScale = 0.5 if self.editor.level.materials.name in ("Pocket", "Alpha") else 1.0
        texSize = 16 * pixelScale
        cageTexVerts = cageTexVerts.astype(float) * pixelScale

        cageTexVerts = numpy.array(
            [((tx, ty), (tx + texSize, ty), (tx + texSize, ty + texSize), (tx, ty + texSize)) for (tx, ty) in
             cageTexVerts], dtype='float32')
        GL.glEnable(GL.GL_ALPHA_TEST)

        drawCube(BoundingBox((x, y, z), (1, 1, 1)), texture=pymclevel.alphaMaterials.terrainTexture,
                 textureVertices=cageTexVerts)
        GL.glDisable(GL.GL_ALPHA_TEST)

    @alertException
    def mouseDown(self, evt, pos, direction):
        pos = map(lambda p, d: p + d, pos, direction)
        op = PlayerSpawnMoveOperation(self, pos)
        try:
            self.editor.addOperation(op)
            if op.canUndo:
                self.editor.addUnsavedEdit()
            self.markerList.invalidate()

        except SpawnPositionInvalid, e:
            if "Okay" != ask(str(e), responses=["Okay", "Fix it for me!"]):
                level = self.editor.level
                status = ""
                if not okayAt63(level, pos):
                    level.setBlockAt(pos[0], 63, pos[2], 1)
                    status += _("Block added at y=63.\n")

                if 59 < pos[1] < 63:
                    pos[1] = 63
                    status += _("Spawn point moved upward to y=63.\n")

                if not okayAboveSpawn(level, pos):
                    if pos[1] > 63 or pos[1] < 59:
                        lpos = (pos[0], pos[1] - 1, pos[2])
                        if level.blockAt(*pos) == 0 and level.blockAt(*lpos) != 0 and okayAboveSpawn(level, lpos):
                            pos = lpos
                            status += _("Spawn point shifted down by one block.\n")
                    if not okayAboveSpawn(level, pos):
                        for i in range(1, 4):
                            level.setBlockAt(pos[0], pos[1] + i, pos[2], 0)

                            status += _("Blocks above spawn point cleared.\n")

                self.editor.invalidateChunks([(pos[0] // 16, pos[2] // 16)])
                op = PlayerSpawnMoveOperation(self, pos)
                try:
                    self.editor.addOperation(op)
                    if op.canUndo:
                        self.editor.addUnsavedEdit()
                    self.markerList.invalidate()
                except SpawnPositionInvalid, e:
                    alert(str(e))
                    return

                if len(status):
                    alert(_("Spawn point fixed. Changes: \n\n") + status)

    @alertException
    def toolReselected(self):
        self.gotoSpawn()
