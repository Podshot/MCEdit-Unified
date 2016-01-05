from pymclevel import nbt
import os


class WaypointManager:
    
    def __init__(self, worldDir=None, editor=None):
        self.worldDirectory = worldDir
        self.waypoints = {}
        self.editor = editor
        self.nbt_waypoints = nbt.TAG_Compound()
        self.nbt_waypoints["Waypoints"] = nbt.TAG_List()
        self.load()
        
    def build(self):
        for point in self.nbt_waypoints["Waypoints"]:
            self.waypoints["{0} ({1},{2},{3})".format(point["Name"].value, round(point["Coordinates"][0].value, 2), round(point["Coordinates"][1].value, 2), round(point["Coordinates"][2].value, 2))] = [
                                                                                                                                                                        point["Coordinates"][0].value, 
                                                                                                                                                                        point["Coordinates"][1].value, 
                                                                                                                                                                        point["Coordinates"][2].value,
                                                                                                                                                                        point["Rotation"][0].value,
                                                                                                                                                                        point["Rotation"][1].value,
                                                                                                                                                                        point["Dimension"].value
                                                                                                                                                                        ]
        
    def load(self):
        if self.editor.level is None:
            return
        if not os.path.exists(os.path.join(self.worldDirectory, u"mcedit_waypoints.dat")):
#            self.nbt_waypoints = nbt.TAG_Compound()
#            self.nbt_waypoints["Waypoints"] = nbt.TAG_List()
            self.build()
        else:
            self.nbt_waypoints = nbt.load(os.path.join(self.worldDirectory, u"mcedit_waypoints.dat"))
            self.build()
        if not (len(self.waypoints) > 0):
            self.waypoints["Empty"] = [0,0,0,0,0,0]
        
        if "LastPosition" in self.nbt_waypoints:
            self.editor.gotoLastWaypoint(self.nbt_waypoints["LastPosition"])
            del self.nbt_waypoints["LastPosition"]
            
    def save(self):
        del self.nbt_waypoints["Waypoints"]
        self.nbt_waypoints["Waypoints"] = nbt.TAG_List()
        for waypoint in self.waypoints.keys():
            way = nbt.TAG_Compound()
            way["Name"] = nbt.TAG_String(waypoint.split()[0])
            way["Dimension"] = nbt.TAG_Int(self.waypoints[waypoint][5])
            coords = nbt.TAG_List()
            coords.append(nbt.TAG_Float(self.waypoints[waypoint][0]))
            coords.append(nbt.TAG_Float(self.waypoints[waypoint][1]))
            coords.append(nbt.TAG_Float(self.waypoints[waypoint][2]))
            rot = nbt.TAG_List()
            rot.append(nbt.TAG_Float(self.waypoints[waypoint][3]))
            rot.append(nbt.TAG_Float(self.waypoints[waypoint][4]))
            way["Coordinates"] = coords
            way["Rotation"] = rot
            self.nbt_waypoints["Waypoints"].append(way)
        print self.worldDirectory
        self.nbt_waypoints.save(os.path.join(self.worldDirectory, u"mcedit_waypoints.dat"))
        
    def delete(self, choice):
        del self.waypoints[choice]
        self.save()
        if not (len(self.waypoints) > 0):
            self.waypoints["Empty"] = [0,0,0,0,0,0]
        
    def saveLastPosition(self, mainViewport, dimension):
        print 'Saving last position'
        if "LastPosition" in self.nbt_waypoints:
            del self.nbt_waypoints["LastPosition"]
        topTag = nbt.TAG_Compound()
        topTag["Dimension"] = nbt.TAG_Int(dimension)
        
        pos = nbt.TAG_List()
        pos.append(nbt.TAG_Float(mainViewport.cameraPosition[0]))
        pos.append(nbt.TAG_Float(mainViewport.cameraPosition[1]))
        pos.append(nbt.TAG_Float(mainViewport.cameraPosition[2]))
        topTag["Coordinates"] = pos
        
        rot = nbt.TAG_List()
        rot.append(nbt.TAG_Float(mainViewport.yaw))
        rot.append(nbt.TAG_Float(mainViewport.pitch))
        topTag["Rotation"] = rot
        
        self.nbt_waypoints["LastPosition"] = topTag
        self.save()
        