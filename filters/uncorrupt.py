    # Filter by WolfieMario
    # You may modify and distribute this filter however you wish.

displayName = "Uncorrupt 14w26a+b"
inputs = (
    ("14w26a/b world-repairing filter by WolfieMario\n", "label"),
    ("This filter will fix world corruptions caused by snapshots 14w26a and 14w26b. Do not use it on modded worlds. After repairing the world, you can play it on 14w26c or later.", "label"),
)
     
def perform(level, box, options):
    for (chunk, slices, point) in level.getChunkSlices(box):
        blocks = chunk.Blocks[slices]
        blocks[:] = blocks[:] & 255
        chunk.chunkChanged()

