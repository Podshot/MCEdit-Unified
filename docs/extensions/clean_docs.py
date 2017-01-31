import glob
import os

def setup(app):
    app.connect('build-finished', clean)
    
def clean(app, exc):
    files = glob.glob(app.builder.outdir + os.path.sep + "*.html")
    for f in files:
        lines = []
        fp_1 = open(f, 'rb')
        for line in fp_1.readlines():
            lines.append(line.replace("_modules", "modules"))
        fp_1.close()
        fp_2 = open(f, 'wb')
        fp_2.writelines(lines)
        fp_2.close()
        
    js_lines = []
    fpr = open(os.path.join(app.builder.outdir, "static", "searchtools.js"), 'rb')
    for line in fpr.readlines():
        js_lines.append(line.replace("'_sources/'", "'sources/'"))
    fpr.close()
    
    fpw = open(os.path.join(app.builder.outdir, "static", "searchtools.js"), 'wb')
    fpw.writelines(js_lines)
    fpw.close()
