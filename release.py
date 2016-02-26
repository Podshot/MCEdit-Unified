import os.path
import directories
import json
import urllib2
import sys
from sys import platform as _platform


def get_version():
    '''
    Gets the name of the current version
    '''
    try:
        with open(os.path.join(directories.getDataDir(), "RELEASE-VERSION.json"), 'rb') as jsonString:
            current = json.load(jsonString)
            return current["name"].replace("{tag_name}",current["tag_name"])
    except:
        raise


def get_release_tag():
    '''
    Gets the stage of development MCEdit-Unified is in
    '''
    try:
        with open(os.path.join(directories.getDataDir(), "RELEASE-VERSION.json"), 'rb') as jsonString:
            current = json.load(jsonString)
            return current["tag_name"]
    except:
        raise


def is_dev():
    '''
    Checks if MCEdit-Unified is in development mode
    '''
    try:
        with open(os.path.join(directories.getDataDir(), "RELEASE-VERSION.json"), 'rb') as jsonString:
            current = json.load(jsonString)
            return current["development"]
    except:
        raise


def fetch_new_version_info():
    return json.loads(urllib2.urlopen("https://api.github.com/repos/Khroki/MCEdit-Unified/releases").read())


def check_for_new_version(release_api_response):
    '''
    Checks for a new MCEdit-Unified version, if the current one is not in development mode
    '''
    try:
        if not is_dev():
            # release_api_response = json.loads(urllib2.urlopen("https://api.github.com/repos/Khroki/MCEdit-Unified/releases").read())
            version = release_api_response[0]
            if version["tag_name"] > get_release_tag():
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
        else:
            return False
    except:
        print "An error occurred checking for updates."
        return False
