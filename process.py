#!/usr/bin/python3

import socket
from struct import unpack
import sys

rfile = sys.argv[1]
wfile = rfile + ".raw"

f = open(rfile, "br")
wf = open(wfile, "w")

last = 0

result = ""

while True:
    data = f.read(1)
    if not data:
        break
    val, = unpack('B', data)
    if val > 56 and val < 87:
        sym = "1"
    elif val > 86 and val < 113:
        sym = "-"
    elif val > 112 and val < 138:
        sym = "0"
    else:
        sym = "."
    result += sym

dedup = []
oldc = ""
cc = 0
for c in result:
    if c == oldc:
        cc += 1
    else:
        dedup.append([oldc, cc])
        oldc = c
        cc = 1

frames = []
frame = ""
for c,cc in dedup:
    if c == '-':
        if cc > 20:
            if len(frame) > 0:
                frames.append(frame)
            frame = ""
    elif cc > 2:
        if c in ["0", "1"]:
            frame += c

frames.append(frame)

#print(result)
#print(dedup)

for frame in frames:
    print(frame)

wf.write(result)
f.close()
wf.close()

