import ftputil
import os
import shutil

class FTPClient:
    
    def download(self):
        for root, directory, files in self._host.walk(self._host.curdir):
            try:
                os.makedirs(os.path.join('ftp', self._worldname, root[2:]))
            except OSError:
                pass
            for f in files:
                self._host.download(self._host.path.join(root, f), os.path.join('ftp', self._worldname, root, f))
                
                
    def upload(self):
        for root, directory, files in os.walk(os.path.join('ftp', self._worldname)):
            for f in files:
                if self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, "").startswith("\\"):
                    target = self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, "").replace("\\", "", 1)
                else :
                    target = self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, "")
                    
                if "\\" in target:
                    target = target.replace("\\", "/")
                #self._host.upload(os.path.join(root, f), self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, ""))
                self._host.upload(os.path.join(root, f), target)
                
        #self._host.upload(os.path.join('ftp', 'upload_test.txt'), 'upload_test.txt')
        
    def cleanup(self):
        if hasattr(self, '_host'):
            self._host.close()
        shutil.rmtree('ftp')
        
    def safe_download(self):
        old_dir = self._host.curdir
        self._host.chdir(self._worldname)
        self.download()
        self._host.chdir(old_dir)
            
    def get_level_path(self):
        return os.path.join('ftp', self._worldname)
                
    def __init__(self, ip, username='anonymous', password=''):
        try:
            os.mkdir("ftp")
        except OSError:
            pass
        self._host = ftputil.FTPHost(ip, username, password)
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
            raise Exception("Could not find the server.properties file! The FTP client will not be able to download the world unless the server.properties file is in the default FTP directory")
        if self._worldname in self._host.listdir(self._host.curdir):
            try:
                os.mkdir(os.path.join('ftp', self._worldname))
            except OSError:
                pass
        else:
            raise Exception("Could not find the world folder from the server.properties file")

      
