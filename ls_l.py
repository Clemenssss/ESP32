import os
import time
def html_escape(text):
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
def run():
    path = "/"
    res = [(f, os.stat(path + f)[6], os.stat(path + f)[8])
           for f in os.listdir(path)]
    
    rows = ""
    alle = sorted(res, key=lambda x: x[2], reverse=True)
    for f, g, s in alle[:10]:
        t = time.localtime(s)
        datum = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4])
        rows += "<tr><td>{}</td><td style='text-align:right'>{} B</td><td>{}</td></tr>".format(
            html_escape(f), g, datum)   # ← nur der Dateiname wird escaped
    
    if len(alle) > 10:
        rows += "<tr><td colspan='3' style='color:#aaa;font-style:italic'>... {} weitere</td></tr>".format(len(alle) - 10)
    
    ergebnis = (
        "<table style='border-collapse:collapse;font-family:monospace;font-size:0.9rem'>"
        "<tr style='border-bottom:1px solid #aaa'>"
        "<th style='text-align:left;padding:4px 12px'>Datei</th>"
        "<th style='text-align:right;padding:4px 12px'>Größe</th>"
        "<th style='text-align:left;padding:4px 12px'>Datum</th>"
        "</tr>"
        + rows +
        "</table>"
        )   
    return ergebnis   # ← kein html_escape() mehr auf das Ganze

if __name__ == "__main__":
    run()