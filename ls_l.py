import os
import time

def run():
    path="/"
    res = [(f, os.stat(path + f)[6], os.stat(path + f)[8])
           for f in os.listdir(path)]

    zeilen = []

    for f, g, s in sorted(res, key=lambda x: x[2], reverse=True):
        t = time.localtime(s)
        zeile = "{:22s} | {:6d} B | {:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(
            f, g, t[0], t[1], t[2], t[3], t[4]
        )
        
        if len(zeilen) < 10:  # Only show the first 10 lines
            print(zeile)
            zeilen.append(zeile)
        else:
            print("zeile",zeile,"not appended")  # Indicate that there are more files not shown    

    return "\n".join(zeilen) + "\n"


if __name__ == "__main__":
    run()