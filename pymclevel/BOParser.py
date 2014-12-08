import yaml
import ConfigParser
import os

class BO3:
    
    def __init__(self):
        pass
def parse_bo3(bo3_file):
    pass

def save_bo3(bo3_file):
    pass

class BO2:
    parser = ConfigParser.RawConfigParser()
    
    def __init__(self, filename=''):
        self.__meta = {}
        self.__rawBlocks = {}
        self.__fixedBlocks = {}
        self.__rawLocations = []
        self.__fixedLocation = []
        if filename != '':
            self.parser.read(filename)
            self.__version = self.parser.get('META', 'version')
            for item in self.parser.items("META"):
                self.__meta[item[0]] = item[1]
            for block in self.parser.items("DATA"):
                self.__blocks[block[0]] = block[1]
            for location in  self.__blocks.keys():
                location = location.split(",")
                self.__fixedLocation.append(location[1]+","+location[2]+","+location[0])
                # Format is Y,X,Z where 'Z' is elevation. WHO DECIDED THAT?!?
            print self.__blocks
        pass
    
    @property
    def meta(self):
        return self.__meta
    
    @property
    def blocks(self):
        return self.__blocks
    
def parse_bo2(bo2_file):
    pass

def save_bo2(bo2_file):
    pass

BO2(filename="test"+os.path.sep+'Asteroid1.BO2')
