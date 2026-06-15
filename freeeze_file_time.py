import os, time
now = time.time(); [time.utime('/' + f, (now, now)) for f in os.listdir('/') if os.stat('/' + f)[0] & 0x4000 == 0]