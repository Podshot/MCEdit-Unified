import os.path
import subprocess
import directories
import json
import urllib2
import sys
from sys import platform as _platform


def get_version():
    try:
        with open(os.path.join(directories.dataDir, "RELEASE-VERSION"), 'rb') as jsonString:
            current = json.load(jsonString)
            return current["name"]
    except:
        raise

def get_release_tag():
    try:
        with open(os.path.join(directories.dataDir, "RELEASE-VERSION"), 'rb') as jsonString:
            current = json.load(jsonString)
            return current["tag_name"]
    except:
        raise

def check_for_new_version():
    try:
        release_api_response = json.loads(urllib2.urlopen("https://api.github.com/repos/Khroki/MCEdit-Unified/releases").read())
        version = release_api_response[0]
        if version["tag_name"] != get_release_tag():
            is_64bit = sys.maxsize > 2**32
            assets = version["assets"]
            for asset in assets:
                if _platform == "win32":
                    version["OS Target"] = "windows"
                    if "Win" in asset["name"]:
                        if is_64bit:
                            if "64bit" in asset["name"]:
                                version["asset"] = asset
                                version["target_arch"] = "64bit"
                        else:
                            if "32bit" in asset["name"]:
                                version["asset"] = asset
                                version["target_arch"] = "32bit"
                elif _platform == "darwin":
                    version["OS Target"] = "osx"
                    if "OSX" in asset["name"]:
                        version["asset"] = asset
                        version["target_arch"] = "64bit"
            return version
        return False
    except:
        print "An error occurred checking for updates."
        return False