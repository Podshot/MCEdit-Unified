import os.path
import subprocess
import directories
import json
import urllib2
import sys
from sys import platform as _platform


def get_version():
    '''
    """
    Loads the build version from the bundled version file, if available.
    """
    if not os.path.exists(os.path.join(directories.dataDir, 'RELEASE-VERSION')):
        try:
            return subprocess.check_output('git describe --tags --match=*.*.*'.split()).strip()
        except:
            return 'unknown'

    fin = open(os.path.join(directories.dataDir, 'RELEASE-VERSION'), 'rb')
    v = fin.read().strip()
    fin.close()
    '''

    return new_get_current_version()

def new_get_current_version():
    current = json.load(open(os.path.join(directories.dataDir, "RELEASE-VERSION"), 'rb'))
    return current["full name"]

def new_get_current_commit():
    current = json.load(open(os.path.join(directories.dataDir, "RELEASE-VERSION"), 'rb'))
    return current["commit"]

def new_get_current_release_tag():
    current = json.load(open(os.path.join(directories.dataDir, "RELEASE-VERSION"), 'rb'))
    return current["release tag"]
    

def check_for_new_version():
    release_api_response = json.loads(urllib2.urlopen("https://api.github.com/repos/Khroki/MCEdit-Unified/releases").read())
    first_entry = release_api_response[0]
    #print "Tag Name: " + first_entry["tag_name"]
    if first_entry["tag_name"] != new_get_current_release_tag():
        is_64bit = sys.maxsize > 2**32
        version = {}
        version["PreRelease"] = first_entry["prerelease"]
        version["full name"] = first_entry["name"]
        assets = first_entry["assets"]
        for asset in assets:
            if _platform == "win32":
                version["OS Target"] = "windows"
                if "Win" in asset["name"] and "Win" in asset["browser_download_url"]:
                    if is_64bit:
                        if "64bit" in asset["name"] and "64bit" in asset["browser_download_url"]:
                            version["download url"] = asset["browser_download_url"]
                            version["target arch"] = "64bit"
                    else:
                        if "32bit" in asset["name"] and "32bit" in asset["browser_download_url"]:
                            version["download url"] = asset["browser_download_url"]
                            version["target arch"] = "32bit"
            elif _platform == "darwin":
                version["OS Target"] = "osx"
                if "OSX" in asset["name"] and "OSX" in asset["browser_download_url"]:
                    version["download url"] = asset["browser_download_url"]
                    version["target arch"] = "64bit"
                
        return version
    return False
    


def get_commit():
    '''
    """
    Loads the git commit ID from the bundled version file, if available.
    """
    if not os.path.exists(os.path.join(directories.dataDir, 'GIT-COMMIT')):
        try:
            return subprocess.check_output('git rev-parse HEAD'.split()).strip()
        except:
            return 'unknown'

    fin = open(os.path.join(directories.dataDir, 'GIT-COMMIT'), 'rb')
    v = fin.read().strip()
    fin.close()

    return v
    '''
    return new_get_current_commit()

#print new_get_current_version()
#print new_get_current_commit()
#print check_for_new_version()
release = get_version()
commit = get_commit()
