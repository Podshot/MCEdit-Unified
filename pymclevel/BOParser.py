import ConfigParser
from pymclevel import schematic, materials

class BO3:
    
    def __init__(self,filename=''):
        self._lines = []
        self._X_tracker = [0,0,0]
        self._Y_tracker = [0,0,0]
        self._Z_tracker = [0,0,0]
        self.block_data = []
        if filename != '':
            fp = open(filename)
            for line in fp.readlines():
                if line.startswith("Block("):
                    self._lines.append(line)
            fp.close()
            for block in self._lines:
                data = block.replace("Block(", "").replace(")","").strip().split(",")
                x = int(data[0])
                y = int(data[1])
                z = int(data[2])
                if "." in data[3]:
                    b_id = 0
                    value = data[3].split(".")[1]
                    for p_id, name in materials.block_map.items():
                        t_id = str(data[3].split(".")[0])
                        if name.replace("minecraft:", "") == t_id.lower():
                            b_id = p_id
                else:
                    b_id = 0
                    for p_id, name in materials.block_map.items():
                        t_id = str(data[3].split(":")[0])
                        if name.replace("minecraft:", "") == t_id.lower():
                            b_id = p_id
                    value = 0
                    
                if x < self._X_tracker[0]:
                    self._X_tracker[0] = x
                if x > self._X_tracker[1]:
                    self._X_tracker[1] = x
                
                if y < self._Y_tracker[0]:
                    self._Y_tracker[0] = y
                if y > self._Y_tracker[1]:
                    self._Y_tracker[1] = y
                    
                if z < self._Z_tracker[0]:
                    self._Z_tracker[0] = z
                if z > self._Z_tracker[1]:
                    self._Z_tracker[1] = z
                    
                self.block_data.append((x,y,z,b_id,value))
                
            if self._X_tracker[0] < 0:
                self._X_tracker[2] = abs(self._X_tracker[0])
                self._X_tracker[1] += abs(self._X_tracker[0])
                
            if self._Y_tracker[0] < 0:
                self._Y_tracker[2] = abs(self._Y_tracker[0])
                self._Y_tracker[1] += abs(self._Y_tracker[0])
                    
            if self._Z_tracker[0] < 0:
                self._Z_tracker[2] = abs(self._Z_tracker[0])
                self._Z_tracker[1] += abs(self._Z_tracker[0])
                   
            print "==== Vertical ===="
            print "Lowest: "+str(self._Y_tracker[0])
            print "Highest: "+str(self._Y_tracker[1])
            print "Shift: "+str(self._Y_tracker[2])
            print "==== Horizontal X ===="
            print "Lowest: "+str(self._X_tracker[0])
            print "Highest: "+str(self._X_tracker[1])
            print "Shift: "+str(self._X_tracker[2])
            print "==== Horizontal Z ===="
            print "Lowest: "+str(self._Z_tracker[0])
            print "Highest: "+str(self._Z_tracker[1])
            print "Shift: "+str(self._Z_tracker[2])
            
            self.__schem = schematic.MCSchematic(shape=(self._X_tracker[1]+1, self._Z_tracker[1]+1, self._Y_tracker[1]+1))
            print self.__schem.size
            for x, y, z, block, data in self.block_data:
                x += self._X_tracker[2]
                y += self._Y_tracker[2]
                z += self._Z_tracker[2]
                self.__schem.Blocks[x,y,z] = int(block)
                self.__schem.Data[x,y,z] = int(data)
            
        def getSchematic(self):
            return self.__schem

class BO2:
    _parser = ConfigParser.RawConfigParser()
    
    def __init__(self, filename=''):
        self.__meta = {}
        self.__blocks = {}
        # [0] is lowest point, [1] is highest point, [2] is the amount to shift by
        self._vertical_tracker = [0,0,0]
        self._horizontal_tracker_1 = [0,0,0]
        self._horizontal_tracker_2 = [0,0,0]
        if filename != '':
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
                    
                    
                if int(block[0].split(",")[1]) < self._horizontal_tracker_2[0]:
                    self._horizontal_tracker_2[0] = int(block[0].split(",")[1])
                if int(block[0].split(",")[1]) > self._horizontal_tracker_2[1]:
                    self._horizontal_tracker_2[1] = int(block[0].split(",")[1])
                    
            if self._vertical_tracker[0] < 0:
                self._vertical_tracker[2] = abs(self._vertical_tracker[0])
                self._vertical_tracker[1] += abs(self._vertical_tracker[0])
                
            if self._horizontal_tracker_1[0] < 0:
                self._horizontal_tracker_1[2] = abs(self._horizontal_tracker_1[0])
                self._horizontal_tracker_1[1] += abs(self._horizontal_tracker_1[0])
                
            if self._horizontal_tracker_2[0] < 0:
                self._horizontal_tracker_2[2] = abs(self._horizontal_tracker_2[0])
                self._horizontal_tracker_2[1] += abs(self._horizontal_tracker_2[0])
                
            self.__schem = schematic.MCSchematic(shape=(self._horizontal_tracker_2[1]+1, self._vertical_tracker[1]+1, self._horizontal_tracker_1[1]+1))
            for block in self._parser.items("DATA"):
                coords = block[0].split(",")
                x = int(coords[1])+self._horizontal_tracker_2[2]
                y = int(coords[0])+self._horizontal_tracker_1[2]
                z = int(coords[2])+self._vertical_tracker[2]
                self.__schem.Blocks[x,y,z] = block[1]
            
    def getSchematic(self):
        return self.__schem
    
    @property
    def meta(self):
        return self.__meta
    
    @property
    def blocks(self):
        return self.__blocks

#BO2(filename="pymclevel"+os.path.sep+"test"+os.path.sep+'Test.BO2')
#BO3(filename="C:\\Users\\Jonathan\\Python\\MCEdit\\Schematics\\chest.bo3")