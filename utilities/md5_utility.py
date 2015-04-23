import hashlib
import urllib2
import urllib
import json
import os
import time


class NotAModule(Exception):
    pass


def getMD5Hash(url, name):
    print "["+str(time.ctime())+"][MD5 Hasher] Downloading <"+name+">"
    urllib.urlretrieve(url, name)
    with open(name) as f:
        data = f.read()
        print "["+str(time.ctime())+"][MD5 Hasher] Finished downloading <"+name+">"
        return hashlib.md5(data).hexdigest()


def getMD5HashesForRelease():
    files = []
    flines = []
    release_api_response = json.loads(urllib2.urlopen("https://api.github.com/repos/Khroki/MCEdit-Unified/releases").read())
    print "["+str(time.ctime())+"][MD5 Hasher] Looping through collected assets"
    for asset in release_api_response[0]["assets"]:
        if "Win" in asset["name"]:
            if "32bit" in asset["name"]:
                print "["+str(time.ctime())+"][MD5 Hasher] Found <Windows 32bit asset>"
                name = "* Windows 32bit MD5 Hash - `"+str(getMD5Hash(asset["browser_download_url"], asset["name"]))+"` \n"
                flines.append(name)
                files.append(asset["name"])
                print "["+str(time.ctime())+"][MD5 Hasher] Finished getting MD5 hash for <Windows 32bit asset>"
            if "64bit" in asset["name"]:
                print "["+str(time.ctime())+"][MD5 Hasher] Found <Windows 64bit asset>"
                name = "* Windows 64bit MD5 Hash - `"+str(getMD5Hash(asset["browser_download_url"], asset["name"]))+"` \n"
                flines.append(name)
                files.append(asset["name"])
                print "["+str(time.ctime())+"][MD5 Hasher] Finished getting MD5 hash for <Windows 64bit asset>"
        if "OSX" in asset["name"]:
            if "64bit" in asset["name"]:
                print "["+str(time.ctime())+"][MD5 Hasher] Found <Mac OS X 64bit asset>"
                name = "* Mac OS X 64bit MD5 Hash - `"+str(getMD5Hash(asset["browser_download_url"], asset["name"]))+"` \n"
                flines.append(name)
                files.append(asset["name"])
                print "["+str(time.ctime())+"][MD5 Hasher] Finished getting MD5 hash for <Mac OS X 64bit asset>"
        if "Lin" in asset["name"]:
            if "64bit" in asset["name"]:
                print "["+str(time.ctime())+"][MD5 Hasher] Found <Linux 64bit asset>"
                name = "* Linux 64bit MD5 Hash - `"+str(getMD5Hash(asset["browser_download_url"], asset["name"]))+"` \n"
                flines.append(name)
                files.append(asset["name"])
                print "["+str(time.ctime())+"][MD5 Hasher] Finished getting MD5 hash for <Linux 64bit asset>"
    print "["+str(time.ctime())+"][MD5 Hasher] Cleaning up files"
    for z in files:
        os.remove(z)
    print "["+str(time.ctime())+"][MD5 Hasher] Writing md5_hashes.txt file"
    with open("md5_hashes.txt", 'wb') as hashes:
        hashes.writelines(flines)
    print "["+str(time.ctime())+"][MD5 Hasher] Finished writing MD5.txt file"
    print "["+str(time.ctime())+"][MD5 Hasher] Program will now exit"

if __name__ == "__main__":
    getMD5HashesForRelease()
else:
    raise NotAModule(str(__name__)+" is not a module!")
