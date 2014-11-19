from logging import getLogger
import json
import directories
import os
import shutil

logger = getLogger(__name__)


class ItemType(object):
    def __init__(self, id, name, maxdamage=0, damagevalue=0, stacksize=64):
        self.id = id
        self.name = name
        self.maxdamage = maxdamage
        self.damagevalue = damagevalue
        self.stacksize = stacksize

    def __repr__(self):
        return "ItemType({0}, '{1}')".format(self.id, self.name)

    def __str__(self):
        return "ItemType {0}: {1}".format(self.id, self.name)


class Items(object):

    items = {}

    def __init__(self, filename=None):
        itemsdir = os.path.join(directories.docsFolder, "Items")

        if not os.path.exists(itemsdir):
            if os.path.exists(os.path.join(directories.getDataDir(), "Items")):
                shutil.copytree(os.path.join(directories.getDataDir(), "Items"), itemsdir)
            else:
                raise Exception("Couldn't find Item Files. Please reinstall MCEdit!")

        for file_ in os.listdir(itemsdir):
            try:
                f = open(os.path.join(itemsdir, file_, "items.json"), 'r')
                itempack = json.load(f)

                itempacknew = {}

                for item in itempack:
                    itempacknew[file_ + ":" + item] = itempack.get(item)
                self.items.update(itempacknew)
            except:
                pass
            try:
                f = open(os.path.join(itemsdir, file_, "blocks.json"))
                itempack = json.load(f.read())

                itempacknew = {}

                for item in itempack:
                    itempacknew[file_ + ":" + item] = itempack.pop(item)
                self.items.update(itempacknew)
            except:
                pass
        

    def findItem(self, id=0, damage=None):
        try:
            item = self.items[id]
        except:
            item = [self.items[x] for x in self.items if self.items[x]["id"] == id][0]
        if damage <= item["maxdamage"]:
            if type(item["name"]) == str or type(item["name"]) == unicode:
                return ItemType(id, item["name"], item["maxdamage"], damage, item["stacksize"])
            else:
                if type(item["name"][damage]) == str or type(item["name"][damage]) == unicode:
                    return ItemType(id, item["name"][damage], item["maxdamage"], damage, item["stacksize"])
                else: 
                    raise ItemNotFound()
        else:
            raise ItemNotFound()

class ItemNotFound(KeyError):
    pass


items = Items()
