import ftputil
import os
import shutil
from ftputil.error import PermanentError

class CouldNotFindPropertiesException(Exception):
    '''
    An Exception that is raised when the 'server.properties' file could not be found at the default directory of the FTP Server
    '''
    pass

class CouldNotFindWorldFolderException(Exception):
    '''
    An Exception that is raised when the world directory that is specified in the the 'server.properties' cannot be found
    '''
    pass

class InvalidCreditdentialsException(Exception):
    '''
    An Exception that is raised when the supplied Username/Password is denied by the FTP Server
    '''
    pass

class FTPClient:
    '''
    Wrapper client to download and upload worlds to a FTP Server
    '''
    
    def download(self):
        '''
        Downloads all files in the current FTP directory with their corresponding paths
        '''
        for root, directory, files in self._host.walk(self._host.curdir):
            try:
                os.makedirs(os.path.join('ftp', self._worldname, root[2:]))
            except OSError:
                pass
            for f in files:
                self._host.download(self._host.path.join(root, f), os.path.join('ftp', self._worldname, root, f))
                
    def upload_new_world(self, world):
        '''
        Uploads a new world to the current FTP server connection
        
        :param world: The InfiniteWorld object for the world to upload
        :type world: InfiniteWorld
        '''
        path = world.worldFolder.getFilePath("level.dat")[:-10]
        world_name = path.split(os.path.sep)[-1]
        if not self._host.path.exists(world_name):
            self._host.mkdir(world_name)
        self._host.chdir(world_name)
        for root, directory, files in os.walk(world.worldFolder.getFilePath("level.dat")[:-10]):
            for folder in directory:
                target = self._host.path.join(root.replace(path, ""), folder).replace("\\", "", 1).replace("\\", "/")
                print "Target: "+target
                if not "##MCEDIT.TEMP##" in target:
                    if not self._host.path.exists(target):
                        self._host.makedirs(target)
        for root, directory, files in os.walk(world.worldFolder.getFilePath("level.dat")[:-10]):
            for f in files:
                target = self._host.path.join(root.replace(path, ""), f).replace("\\", "", 1).replace("\\", "/")
                print target
                try:
                    self._host.upload(os.path.join(root, f), target)
                except Exception as e:
                    if "226" in e.message:
                        pass
                    else:
                        print "Error: {0}".format(e.message)
                
    def upload(self):
        '''
        Uploads an edited world to the current FTP server connection
        '''
        for root, directory, files in os.walk(os.path.join('ftp', self._worldname)):
            for folder in directory:
                target = self._host.path.join(root, folder).replace("ftp"+os.path.sep+self._worldname+"/", "").replace("\\", "", 1).replace("\\", "/")
                target = target.replace("ftp"+self._worldname, "")
                if not "##MCEDIT.TEMP##" in target:
                    if not self._host.path.exists(target):
                        self._host.makedirs(target)
        for root, directory, files in os.walk(os.path.join('ftp', self._worldname)):
            for f in files:
                if self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, "").startswith("\\"):
                    target = self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, "").replace("\\", "", 1)
                else :
                    target = self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, "")
                    
                if "\\" in target:
                    target = target.replace("\\", "/")
                try:
                    self._host.upload(os.path.join(root, f), target)
                except Exception as e:
                    if "226" in e.message:
                        pass
        
    def cleanup(self):
        '''
        Closes the FTP connection and removes all leftover files from the 'ftp' directory
        '''
        if hasattr(self, '_host'):
            self._host.close()
        shutil.rmtree('ftp')
        
    def safe_download(self):
        '''
        Changes the FTP client's working directory, downloads the world, then switches back to the original working directory
        '''
        old_dir = self._host.curdir
        self._host.chdir(self._worldname)
        self.download()
        self._host.chdir(old_dir)
            
    def get_level_path(self):
        '''
        Gets the local path to the downloaded FTP world
        '''
        return os.path.join('ftp', self._worldname)
                
    def __init__(self, ip, username='anonymous', password=''):
        '''
        Initializes an FTP client to handle uploading and downloading of a Minecraft world via FTP
        
        :param ip: The IP of the FTP Server
        :type ip: str
        :param username: The Username to use to log into the server
        :type username: str
        :param password: The Password that accompanies the supplied Username
        :type password: str
        '''
        try:
            os.mkdir("ftp")
        except OSError:
            pass
        try:
            self._host = ftputil.FTPHost(ip, username, password)
        except PermanentError:
            raise InvalidCreditdentialsException("Incorrect username or password")
            return
            
        self._worldname = None
        if 'server.properties' in self._host.listdir(self._host.curdir):
            self._host.download('server.properties', os.path.join('ftp', 'server.properties'))
            with open(os.path.join('ftp', 'server.properties'), 'r') as props:
                content = props.readlines()
                if len(content) > 1:
                    for prop in content:
                        if prop.startswith("level-name"):
                            self._worldname = str(prop.split("=")[1:][0]).rstrip("\n")
                else:
                    for prop in content[0].split('\r'):
                        if prop.startswith("level-name"):
                            self._worldname = str(prop.split("=")[1:][0]).rstrip("\r")
        else:
            raise CouldNotFindPropertiesException("Could not find the server.properties file! The FTP client will not be able to download the world unless the server.properties file is in the default FTP directory")
        if self._worldname in self._host.listdir(self._host.curdir):
            try:
                os.mkdir(os.path.join('ftp', self._worldname))
            except OSError:
                pass
        else:
            raise CouldNotFindWorldFolderException("Could not find the world folder from the server.properties file")

      
