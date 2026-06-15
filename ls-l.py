import os, time
res = [(f, os.stat('/'+f)[6], os.stat('/'+f)[8]) for f in os.listdir('/')]
for f, g, s in sorted(res, key=lambda x: x[2], reverse=True): t=time.localtime(s); print("{:22s} | {:6d} B | {:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(f, g, t[0], t[1], t[2], t[3], t[4]))