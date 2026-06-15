import os
import time

now = time.localtime()
t = time.localtime()
ts = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
    t[0], t[1], t[2], t[3], t[4], t[5]
)
for fn in os.listdir():
    try:
        with open(fn, "a"):
            pass
        print("bearbeitet:", fn, ts)
    except OSError:
        pass