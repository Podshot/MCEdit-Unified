# Feel free to modify and use this filter however you wish. If you do,
# please give credit to SethBling.
# http://youtube.com/SethBling

from MCWorldLibrary import TAG_Compound
from MCWorldLibrary import TAG_Int
from MCWorldLibrary import TAG_Short
from MCWorldLibrary import TAG_Byte
from MCWorldLibrary import TAG_String
from MCWorldLibrary import TAG_Float
from MCWorldLibrary import TAG_Double
from MCWorldLibrary import TAG_List
from MCWorldLibrary import TileEntity

displayName = "Create Spawners"

inputs = (
("Include position data", False),
)


def perform(level, box, options):
    includePos = options["Include position data"]
    entitiesToRemove = []

    for (chunk, slices, point) in level.getChunkSlices(box):

        for entity in chunk.Entities:
            x = int(entity["Pos"][0].value)
            y = int(entity["Pos"][1].value)
            z = int(entity["Pos"][2].value)

            if box.minx <= x < box.maxx and box.miny <= y < box.maxy and box.minz <= z < box.maxz:
                entitiesToRemove.append((chunk, entity))

                level.setBlockAt(x, y, z, 52)
                level.setBlockDataAt(x, y, z, 0)

                spawner = TileEntity.Create("MobSpawner")
                TileEntity.setpos(spawner, (x, y, z))
                spawner["Delay"] = TAG_Short(120)
                spawner["SpawnData"] = entity
                if not includePos:
                    del spawner["SpawnData"]["Pos"]
                spawner["EntityId"] = entity["id"]

                chunk.TileEntities.append(spawner)

    for (chunk, entity) in entitiesToRemove:
        chunk.Entities.remove(entity)
