import urllib2
import json
import os
from logging import getLogger

def run():
    log = getLogger(__name__)
    num = False

    def download(_data):
        _download = False
        d, url = _data.split('||')
        dir_path = os.path.join(base, "mcver", d)
        file_path = os.path.join(dir_path, os.path.basename(url))
        if not (os.path.exists(dir_path) or os.path.isdir(dir_path)):
            os.mkdir(dir_path)
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
                log.info("Updated {}::{}".format(d, os.path.basename(file_path)))
                #print "Updated {}:{}".format(d, file_path)
                return True
        if _download:
            conn = urllib2.urlopen(url, timeout=7.5)
            fp = open(file_path, 'wb')
            fp.write(conn.read())
            conn.close()
            fp.close()
            log.info("Downloaded {}::{}".format(d, os.path.basename(file_path)))
            return True
        return False

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ver = []

    manifest = urllib2.urlopen("https://raw.githubusercontent.com/Khroki/MCEdit-Unified/gh-pages/mcver.json")
    data = json.loads(manifest.read())
    manifest.close()

    for version in data.iterkeys():
        for f in data[version]:
            ver.append("{}||{}".format(version, f))

    for ver_file in ver:
        if download(ver_file): num = True
    return num
