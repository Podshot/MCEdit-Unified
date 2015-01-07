This file is to note down what needs to be fixed, and anything that badly needs an upgrade. Although this document was written to just keep things straightened out, any help is appreciated. 

- [ ] Reimplement automatic updating
	- Because I build using pyinstaller instead of py2exe, mcedit will need to be changed from esky to updater4pyi.
	- File: mcedit.py
- [ ] Fix erode tool
	- Currently doesn't take damage values into account, not a problem for most blocks but causes stained clay to always erode into white stained clay.
- [ ] Fix fence renderer
	- As is the fence renderer can't handle more than one texture without the arrays ceasing to work, rewrite as needed and combine the netherbrick renderer into it.
	- File: renderer.py
- [ ] Add sign, button, and lever renderer
	- Signs and buttons currently lack a renderer, levers are piggybacking off the torch renderer with some wierd effects. Might be best off copying the snow and or laddar renderers and tweaking them to purpose.
	- File: renderer.py
- [ ] Add block rotate function
	- Currently I've been just adding all the different block rotations to minecraft.yaml, which while it is functional it is clunky at best. I would like to add a key that when pressed increments the damage value of a block within a specified range, preferrably defined using a new attribute in minecraft.yaml. Such as rotation: [2, 3, 4, 5] for chests, allowing us to remove the directional entries from the block list and just use the key to rotate blocks.
	- Files: minecraft.yaml, config.py, brush.py, possibly renderer.py
- [ ] Add Pocket Edition 0.9.0 Format Compatibility
	- Currently completely broken, to fix you need mojang's leveldb libraries from their github and a python wrapper, I've included a self-contained wrapper that should work, see leveldb.py. Feel free to break old pocket compatibility if needed.
	- Files: pocket.py, leveleditor.py, possibly others
- [ ] Update Pocket Edition materials
	- While pocket.yaml may be up to date, the mappings aren't so much. Might be important down the line as the renderer does call these mappings.
	- File: materials.py
- [ ] Add compatibility for 1.8 block name system
	- Although the item system was relatively straightforward to convert, mcedit internally uses the block ids all over the place, easiest way to implement would likely to be to pull the block name and other neccisary data then use materials.py to map them to ids, with a fallback for older versions. May require creative use of damage values down the line if we run out of IDs. A full convert is possible but quite involved and will break pocket, classic, and any pre 1.7 compatibility.
	- Files: like half of MCedit
- [ ] Cleanup minecraft.yaml
Lots of outdated information and variables that don't do anything as many renderers handle which blocks they use directly, and in some cases the renderers being referenced don't even exist.
- [ ] Optimization
	- There are multiple instances of inefficiencies in the code, some of it from my lack of experience, some has just always been there, if you see something that can be sped up, feel free.
