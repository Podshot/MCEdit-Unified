import yaml
import ConfigParser
import os
from pymclevel import schematic

class BO3:
    
    def __init__(self,filename=''):
        if filename != '':
            pass
        pass
def parse_bo3(bo3_file):
    pass

def save_bo3(bo3_file):
    pass

class BO2:
    _parser = ConfigParser.RawConfigParser()
    
    def __init__(self, filename=''):
        self.__meta = {}
        self.__blocks = {}
        # [0] is lowest point, [1] is highest point, [2] is the amount to shift by
        self._vertical_tracker = [0,0,0]
        self._horizontal_tracker_1 = [0,0,0]
        '''
        for slot in range(0,3):
            self._horizontal_tracker[slot] = 0
            self._vertical_tracker[slot] = 0
        '''
        if filename != '':
            self.__schem = schematic.MCSchematic(shape=(0,0,0))
            self._parser.read(filename)
            self.__version = self._parser.get('META', 'version')
            for item in self._parser.items("META"):
                self.__meta[item[0]] = item[1]
                
            for block in self._parser.items("DATA"):
                
                if int(block[0].split(",")[2]) < self._vertical_tracker[0]:
                    self._vertical_tracker[0] = int(block[0].split(",")[2])
                if int(block[0].split(",")[2]) > self._vertical_tracker[1]:
                    self._vertical_tracker[1] = int(block[0].split(",")[2])
                    
                    
                if int(block[0].split(",")[0]) < self._horizontal_tracker_1[0]:
                    self._horizontal_tracker_1[0] = int(block[0].split(",")[0])
                if int(block[0].split(",")[0]) > self._horizontal_tracker_1[1]:
                    self._horizontal_tracker_1[1] = int(block[0].split(",")[0])
                    
            if self._vertical_tracker[0] < 0:
                self._vertical_tracker[2] = abs(self._vertical_tracker[0])
                self._vertical_tracker[1] += abs(self._vertical_tracker[0])
                #self._vertical_tracker[0] = 0
                
            if self._horizontal_tracker_1[0] < 0:
                self._horizontal_tracker_1[2] = abs(self._horizontal_tracker_1[0])
                self._horizontal_tracker_1[1] += abs(self._horizontal_tracker_1[0])
                
                
                
            print "==== Vertical ===="
            print "Lowest: "+str(self._vertical_tracker[0])
            print "Highest: "+str(self._vertical_tracker[1])
            print "Shift: "+str(self._vertical_tracker[2])
            print "==== Horizontal X ===="
            print "Lowest: "+str(self._horizontal_tracker_1[0])
            print "Highest: "+str(self._horizontal_tracker_1[1])
            print "Shift: "+str(self._horizontal_tracker_1[2])
            self.__schem.height = self._vertical_tracker[1]
            '''
            for block in self._parser.items("DATA"):
                #self.__blocks[block[0]] = block[1]
                coords = block[0].split(",")
                x = int(coords[0])
                y = int(coords[1])
                z = int(coords[2])
                print x,y,z
                self.__schem.Blocks[x,y,z] = block[1]
                self.__schem._update_shape()
            print self.__schem.Blocks
            self.__schem.saveToFile(filename="test_bo2.schematic")
                
            # Format is Y,X,Z where 'Z' is elevation. WHO DECIDED THAT?!?
            print self.__blocks
            '''
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

BO2(filename="pymclevel"+os.path.sep+"test"+os.path.sep+'Asteroid1.BO2')
