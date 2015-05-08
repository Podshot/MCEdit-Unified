from albow import alert

class fileEdit():
    def __init__(self, filename, timeChanged, box, editor, level):
        self.filename = filename
        self.timeChanged = timeChanged
        self.box = box
        self.editor = editor
        self.level = level

    def makeChanges(self):
        file = open(self.filename)
        lines = []
        for line in file.readlines():
            if line != "\n":
                lines.append(line.replace("\n", ""))
        file.close()

        blocks = []
        for (x, y, z) in self.box.positions:
            if self.level.blockAt(x, y, z) == 137:
                blocks.append((x, y, z))

        if len(lines) != len(blocks):
            alert("The amount of line does not match the amount of blocks")
            return

        changes = False
        for i, line in enumerate(lines):
            x ,y, z = blocks[i]
            tileEntity = self.level.tileEntityAt(x, y, z)
            if line == "\"\"":
                line = ""
            if tileEntity["Command"].value != line:
                tileEntity["Command"].value = line
                self.level.addTileEntity(tileEntity)
                changes = True

        if changes:
            self.editor.addUnsavedEdit()
