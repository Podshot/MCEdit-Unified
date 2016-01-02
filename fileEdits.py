from albow import alert
from editortools.operation import Operation
import itertools
from albow import alert

class fileEdit():
    def __init__(self, filename, timeChanged, box, editor, level):
        self.filename = filename
        self.timeChanged = timeChanged
        self.box = box
        self.editor = editor
        self.level = level
        self.order = []

    def makeChanges(self):
        try:
            file = open(self.filename, 'rb')
        except:
            alert("Couldn't open the file")
            return
        lines = []
        for line in file.readlines():
            line = line.replace("\r", "")
            if line != "\n":
                lines.append(line.replace("\n", ""))
        file.close()

        tileEntities = []
        for (x,y,z) in self.order:
            blockAtXYZ = self.level.blockAt(x, y, z)
            if blockAtXYZ == 137 or blockAtXYZ == 210 or blockAtXYZ == 211:
                tileEntities.append(self.level.tileEntityAt(x, y, z))
            else:
                alert("The blocks are different now!")
                return

        if len(lines) != len(tileEntities):
            alert("You have %d lines and %d command blocks, it should be the same." % (len(lines), len(tileEntities)))
            return

        op = FileEditsOperation(self.editor, self.level, self.box, lines, tileEntities)
        self.editor.addOperation(op)
        if op.canUndo:
            self.editor.addUnsavedEdit()

    def writeCommandInFile(self, first, space, (x,y,z), fileTemp, skip, chain, done, order):
        block = self.editor.level.tileEntityAt(x, y, z)
        if chain:
            if not block or (x, y, z) in done:
                return
        if not first:
            if space:
                fileTemp.write("\n\n")
            else:
                fileTemp.write("\n")
        text = block["Command"].value
        if text == "":
            text = "\"\""
        order.append((x,y,z))
        fileTemp.write(text.encode('utf-8'))

        if chain:
            done.append((x, y, z))
            blockData =  self.editor.level.blockDataAt(x, y, z)
            if blockData == 0 and self.level.blockAt(x, y-1, z) == 211:
                skip.append((x,y-1,z))
                self.writeCommandInFile(False, space, (x, y-1, z), fileTemp, skip, True, done, order)
            elif blockData == 1 and self.level.blockAt(x, y+1, z) == 211:
                skip.append((x,y+1,z))
                self.writeCommandInFile(False, space, (x, y+1, z), fileTemp, skip, True, done, order)
            elif blockData == 2 and self.level.blockAt(x, y, z-1) == 211:
                skip.append((x,y,z-1))
                self.writeCommandInFile(False, space, (x, y, z-1), fileTemp, skip, True, done, order)
            elif blockData == 3 and self.level.blockAt(x, y, z+1) == 211:
                skip.append((x,y,z+1))
                self.writeCommandInFile(False, space, (x, y, z+1), fileTemp, skip, True, done, order)
            elif blockData == 4 and self.level.blockAt(x-1, y, z) == 211:
                skip.append((x-1,y,z))
                self.writeCommandInFile(False, space, (x-1, y, z), fileTemp, skip, True, done, order)
            elif blockData == 5 and self.level.blockAt(x+1, y, z) == 211:
                skip.append((x+1,y,z))
                self.writeCommandInFile(False, space, (x+1, y, z), fileTemp, skip, True, done, order)


class FileEditsOperation(Operation):
    def __init__(self, editor, level, box, lines, tileEntities):
        self.editor = editor
        self.level = level
        self.box = box
        self.lines = lines
        self.tileEntities = tileEntities
        self.undoLevel = None
        self.canUndo = False

    def perform(self, recordUndo=True):
        if self.level.saving:
            alert("Cannot perform action while saving is taking place")
            return
        if recordUndo:
            self.undoLevel = self.extractUndo(self.level, self.box)

        for i, line in enumerate(self.lines):
            tileEntity = self.tileEntities[i]
            line = line.decode('utf-8')
            line = line.replace(u"\u201c\u202a", "\"")
            line = line.replace(u"\u201d\u202c", "\"")
            if line == "\"\"":
                line = ""
            if tileEntity["Command"].value != line:
                tileEntity["Command"].value = line
                self.level.addTileEntity(tileEntity)
                if not self.canUndo and recordUndo:
                    self.canUndo = True

    def dirtyBox(self):
        return self.box


def GetSort(box, sorting):
    if sorting == "xz" or sorting == "chain":
        return itertools.product(
            xrange(box.minx, box.maxx),
            xrange(box.miny, box.maxy),
            xrange(box.minz, box.maxz)
        )
    else:
        return itertools.product(
            xrange(box.minz, box.maxz),
            xrange(box.miny, box.maxy),
            xrange(box.minx, box.maxx)
        )
