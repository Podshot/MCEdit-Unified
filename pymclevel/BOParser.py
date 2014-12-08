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
    _parser = ConfigParser.RawConfigParser()
    
    def __init__(self, filename=''):
        self.__meta = {}
        self.__rawBlocks = {}
        if filename != '':
            self._parser.read(filename)
            self.__version = self._parser.get('META', 'version')
            for item in self._parser.items("META"):
                self.__meta[item[0]] = item[1]
                
            for block in self._parser.items("DATA"):
                self.__rawBlocks[block[0]] = block[1]
                
            # Format is Y,X,Z where 'Z' is elevation. WHO DECIDED THAT?!?
            print self.__rawBlocks
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
