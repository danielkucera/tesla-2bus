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
dedup.append([oldc, cc])

frames = []
frame = ""
for c,cc in dedup:
    if c == '-':
        if cc > 20:
            if len(frame) > 0:
                frames.append(frame)
            frame = ""
    elif cc > 1:
        if c in ["0", "1"]:
            frame += c

frames.append(frame)

#print(result)
#print(dedup)

def b2d(string):
    e = 0
    res = 0
    for c in string:
        res += int(c)*2**e
        e += 1
    return res

def decode_frame(frame):
    to_subsn = frame[0:2]
    to_sn = frame[2:12]
    to_gk = frame[12:16]
    from_subsn = frame[16:18]
    from_sn = frame[18:28]
    from_gk = frame[28:32]
    cmd = frame[32:40]
    fcs = frame[40:48]

    print(to_subsn, to_sn, to_gk, from_subsn, from_sn, from_gk, cmd, fcs)
    dframe = {}
    dframe["from_sn"] = b2d(from_sn), b2d(from_subsn), b2d(from_gk) == 0
    dframe["to_sn"] = b2d(to_sn), b2d(to_subsn), b2d(to_gk) == 0
    dframe["cmd"] = b2d(cmd)
    bs = b2d(frame[0:8]) + b2d(frame[8:16]) + b2d(frame[16:24]) + b2d(frame[24:32]) + \
        b2d(frame[32:40])
    cs = (~(bs % 0x100)+1)&0xff
    dframe["fcs"] = b2d(frame[40:48])
    #print(cs, dframe["fcs"], )
    if cs != dframe["fcs"]:
        print("Checksum FAIL!")
    return dframe


for frame in frames:
    #print(frame)
    print(decode_frame(frame))

wf.write(result)
f.close()
wf.close()

