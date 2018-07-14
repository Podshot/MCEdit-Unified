import urllib2
import json
import os
from logging import getLogger

def run():
    log = getLogger(__name__)
    num = False

    def download(_gamePlatform, _gameVersionNumber, url):
        _download = False
        dir_path = os.path.join(base, "mcver", _gamePlatform, _gameVersionNumber)
        file_path = os.path.join(dir_path, os.path.basename(url))
        if not (os.path.exists(dir_path) or os.path.isdir(dir_path)):
            os.makedirs(dir_path)
            _download = True
        if not os.path.exists(file_path):
            _download = True
        else:
            conn = urllib2.urlopen(url, timeout=7.5)
            new_data = conn.read().strip()
            current = open(file_path, 'rb')
            current_data = current.read().strip()

            conn.close()
            current.close()
            if new_data != current_data:
                fp = open(file_path, 'wb')
                fp.write(new_data.strip())
                fp.close()
                log.info("Updated {} {}::{}".format(_gamePlatform, _gameVersionNumber, os.path.basename(file_path)))
                return True
        if _download:
            conn = urllib2.urlopen(url, timeout=7.5)
            fp = open(file_path, 'wb')
            fp.write(conn.read())
            conn.close()
            fp.close()
            log.info("Downloaded {} {}::{}".format(_gamePlatform, _gameVersionNumber, os.path.basename(file_path)))
            return True
        return False

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ver = []

    try:
        manifest = urllib2.urlopen("https://raw.githubusercontent.com/Podshot/MCEdit-Unified/master/mcver/mcver.json")
        data = json.loads(manifest.read())
        manifest.close()
    except:
        return

    for gamePlatform in data.iterkeys():
        for gameVersionNumber in data[gamePlatform].iterkeys():
            for f in data[gamePlatform][gameVersionNumber]:
                if download(gamePlatform, gameVersionNumber, f):
                    num = True
    return num
