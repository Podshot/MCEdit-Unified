import urllib2
import json
import os


def run():
    num = False

    def download(_data):
        d, url = _data.split('||')
        dir_path = os.path.join(base, "mcver", d)
        file_path = os.path.join(dir_path, os.path.basename(url))
        if not (os.path.exists(dir_path) or os.path.isdir(dir_path)):
            os.mkdir(dir_path)
        if not os.path.exists(file_path):
            conn = urllib2.urlopen(url)
            fp = open(file_path, 'wb')
            fp.write(conn.read())
            conn.close()
            fp.close()
            return True

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ver = []

    manifest = urllib2.urlopen("http://127.0.0.1:8000/mcver.json")
    data = json.loads(manifest.read())
    manifest.close()

    for version in data.iterkeys():
        for f in data[version]:
            ver.append("{}||{}".format(version, f))

    for ver_file in ver:
        if download(ver_file): num = True
    return num
