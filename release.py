import os.path
import subprocess
import directories
import json
import HTMLParser


def get_version():
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

    return v

def new_get_current_version():
    current = json.load(open(os.path.join(directories.dataDir, "RELEASE-VERSION-JSON"), 'rb'))
    return current["name"]

def new_get_current_commit():
    current = json.load(open(os.path.join(directories.dataDir, "RELEASE-VERSION-JSON"), 'rb'))
    return current["commit"]


def get_commit():
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

print new_get_current_version()
print new_get_current_commit()
release = get_version()
commit = get_commit()
