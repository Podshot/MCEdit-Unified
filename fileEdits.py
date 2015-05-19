from albow import alert
from editortools.operation import Operation
import itertools

class fileEdit():
    def __init__(self, filename, timeChanged, box, sorting, editor, level):
        self.filename = filename
        self.timeChanged = timeChanged
        self.box = box
        self.sorting = sorting
        self.editor = editor
        self.level = level

    def makeChanges(self):
        file = open(self.filename, 'rb')
        lines = []
        for line in file.readlines():
            if line != "\n":
                lines.append(line.replace("\n", ""))
        file.close()

        tileEntities = []
        for coords in GetSort(self.box, self.sorting):
            if self.sorting == "xz":
                (x, y, z) = coords
            else:
                (z, y, x) = coords
            if self.level.blockAt(x, y, z) == 137:
                tileEntities.append(self.level.tileEntityAt(x, y, z))

        if len(lines) != len(tileEntities):
            alert("You have %d lines and %d command blocks, it should be the same." % (len(lines), len(tileEntities)))
            return

        op = FileEditsOperation(self.editor, self.level, self.box, lines, tileEntities)
        self.editor.addOperation(op)
        if op.canUndo:
            self.editor.addUnsavedEdit()


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
    if sorting == "xz":
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
