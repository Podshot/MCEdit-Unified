import ftputil
import os
import time

try:
    os.mkdir("ftp")
except OSError:
    pass

class FTPClient:
    
    def _download(self):
        for root, directory, files in self._host.walk(self._host.curdir):
            print "Root: "+root
            print "Directory: "+str(directory)
            print "Files: "+str(files)
            print '=============================='
            try:
                os.makedirs(os.path.join('ftp', self._worldname, root[2:]))
            except OSError:
                pass
            for f in files:
                print "++++++++++++++++++++++++++++++++++++"
                print "Host: "+self._host.path.join(root, f)
                print "Client: "+os.path.join('ftp', self._worldname, root[2:], f)
                print root[2:]
                print "++++++++++++++++++++++++++++++++++++"
                self._host.download(self._host.path.join(root, f), os.path.join('ftp', self._worldname, root, f))
                
                
    def _upload(self):
        for root, directory, files in os.walk(os.path.join('ftp', self._worldname)):
            print "Root: "+root
            print "Directory: "+str(directory)
            print "Files: "+str(files)
            print '=============================='
            for f in files:
                #print "Current directory: "+self._host.curdir
                #print "Source: "+os.path.join(root, f)
                #print "Target: "+self._host.path.join(f).replace("ftp"+os.path.sep, "")
                #print '++++++++++++++++++++++++++++++++++'
                self.upload_logging.append("Current directory: "+self._host.curdir+'\n')
                self.upload_logging.append("Source: "+os.path.join(root, f)+'\n')
                self.upload_logging.append("Target: "+self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, "")+'\n')
                self.upload_logging.append('++++++++++++++++++++++++++++++++++'+'\n')
                
                self._host.upload(os.path.join(root, f), self._host.path.join(root, f).replace("ftp"+os.path.sep+self._worldname, ""))
                
        #self._host.upload(os.path.join('ftp', 'upload_test.txt'), 'upload_test.txt')
                
    def __init__(self):
        self.upload_logging = []
        self._host = ftputil.FTPHost('192.168.200.29', 'anonymous', '')
        self._worldname = None
        if 'server.properties' in self._host.listdir(self._host.curdir):
            self._host.download('server.properties', os.path.join('ftp', 'server.properties'))
            with open(os.path.join('ftp', 'server.properties'), 'r') as props:
                content = props.readlines()
                for prop in content:
                    if prop.startswith("level-name"):
                        self._worldname = str(prop.split("=")[1:][0]).rstrip("\n")
        if self._worldname in self._host.listdir(self._host.curdir):
            try:
                os.mkdir(os.path.join('ftp', self._worldname))
            except OSError:
                pass
            old_dir = self._host.curdir
            self._host.chdir(self._worldname)
            self._download()
            self._host.chdir(old_dir)
        print ""
        print ""
        print ""
        print ""
        print ""
        print ""
        
        self._upload()
        for line in self.upload_logging:
            print line
        print self._host.getcwd()
        #with open('upload_logging.txt', 'wb') as f:
            #f.writelines(self.upload_logging)
                        
        '''
        for root, directory, files in self._host.walk(self._host.curdir):
            print "Root: "+root
            print "Directory: "+str(directory)
            print "Files: "+str(files)
            print '=============================='
            try:
                os.makedirs(os.path.join('ftp', root[2:]))
            except OSError:
                pass
            for f in files:
                print "++++++++++++++++++++++++++++++++++++"
                print "Host: "+self._host.path.join(root, f)
                print "Client: "+os.path.join('ftp', root[2:], f)
                print root[2:]
                print "++++++++++++++++++++++++++++++++++++"
                self._host.download(self._host.path.join(root, f), os.path.join('ftp', root, f))
        #self._host.chdir(oldDir)
        #print self._host.curdir
        '''
                
client = FTPClient()
            
