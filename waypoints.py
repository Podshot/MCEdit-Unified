from pymclevel import nbt
import os
import logging
import inspect
import shutil

log = logging.getLogger(__name__)
DEBUG = False

class WaypointManager:
    '''
    Class for handling the API to load and save waypoints
    '''

    def __init__(self, worldDir=None, editor=None):
        self.worldDirectory = worldDir
        self.waypoints = {}
        self.waypoint_names = []
        self.editor = editor
        self.nbt_waypoints = nbt.TAG_Compound()
        self.nbt_waypoints["Waypoints"] = nbt.TAG_List()
        self.load()

    def build(self):
        '''
        Builds the raw NBT data from the 'mcedit_waypoints.dat' file to a readable dictionary, with the key being '<Name> (<X>,<Y>,<Z>)' and the values being a list of [<X>,<Y>,<Z>,<Yaw>,<Pitch>,<Dimension>]
        '''
        for point in self.nbt_waypoints["Waypoints"]:
            self.waypoint_names.append(point["Name"].value)
            self.waypoints["{0} ({1},{2},{3})".format(point["Name"].value, round(point["Coordinates"][0].value, 2), round(point["Coordinates"][1].value, 2), round(point["Coordinates"][2].value, 2))] = [
                                                                                                                                                                        point["Coordinates"][0].value, 
                                                                                                                                                                        point["Coordinates"][1].value, 
                                                                                                                                                                        point["Coordinates"][2].value,
                                                                                                                                                                        point["Rotation"][0].value,
                                                                                                                                                                        point["Rotation"][1].value,
                                                                                                                                                                        point["Dimension"].value
                                                                                                                                                                        ]

    def load(self):
        '''
        Loads the 'mcedit_waypoints.dat' file from the world directory if it exists. If it doesn't exist, it sets the 'Empty' waypoint
        '''
        if self.editor.level is None:
            return
        if not os.path.exists(os.path.join(self.worldDirectory, u"mcedit_waypoints.dat")):
            self.build()
        else:
            try:
                self.nbt_waypoints = nbt.load(os.path.join(self.worldDirectory, u"mcedit_waypoints.dat"))
            except nbt.NBTFormatError:
                shutil.move(os.path.join(self.worldDirectory, u"mcedit_waypoints.dat"), os.path.join(self.worldDirectory, u"mcedit_waypoints_backup.dat"))
                log.warning("Waypoint data file corrupted, ignoring...")
            finally:
                self.build()
        if not (len(self.waypoints) > 0):
            self.waypoints["Empty"] = [0,0,0,0,0,0]

        if "LastPosition" in self.nbt_waypoints:
            self.editor.gotoLastWaypoint(self.nbt_waypoints["LastPosition"])
            del self.nbt_waypoints["LastPosition"]

    def save(self):
        '''
        Saves all waypoint information to the 'mcedit_waypoints.dat' file in the world directory
        '''
        if DEBUG:
            current_frame = inspect.currentframe()
            outerframe = inspect.getouterframes(current_frame, 2)[1]
            print "Called by '" + str(outerframe[3]) + "()' in '" + str(outerframe[1].split("\\")[-1]) + "' at line " + str(outerframe[2])
        del self.nbt_waypoints["Waypoints"]
        self.nbt_waypoints["Waypoints"] = nbt.TAG_List()
        for waypoint in self.waypoints.keys():
            if waypoint.split()[0] == "Empty":
                continue
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
        self.nbt_waypoints.save(os.path.join(self.worldDirectory, u"mcedit_waypoints.dat"))
        
    def add_waypoint(self, name, coordinates, rotation, dimension):
        '''
        Adds a waypoint to the current dictionary of waypoints
        
        :param name: Name of the Waypoint
        :type name: str
        :param coordinates: The coordinates of the Waypoint (in X,Y,Z order)
        :type coordinates: tuple
        :param rotation: The rotation of the current camera viewport (in Yaw,Pitch order)
        :type rotation: tuple
        :param dimension: The current dimenstion the camera viewport is in
        :type dimension: int
        '''
        formatted_name = "{0} ({1},{2},{3})".format(name, coordinates[0], coordinates[1], coordinates[2])
        data = coordinates + rotation + (dimension,)
        self.waypoint_names.append(name)
        self.waypoints[formatted_name] = data

    def delete(self, choice):
        '''
        Deletes the specified waypoint name from the dictionary of waypoints
        
        :param choice: Name of the waypoint to delete
        :type choice: str
        '''
        del self.waypoints[choice]
        self.save()
        if not (len(self.waypoints) > 0):
            self.waypoints["Empty"] = [0,0,0,0,0,0]

    def saveLastPosition(self, mainViewport, dimension):
        '''
        Saves the final position of the camera viewport when the world is closed or MCEdit is exited
        
        :param mainViewport: The reference to viewport object
        :param dimension: The dimension the camera viewport is currently in
        :type dimension: int
        '''
        log.info('Saving last position.')
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
