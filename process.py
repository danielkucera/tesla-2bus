#!/usr/bin/python

import socket
from struct import unpack
import sys

rfile = sys.argv[1]
wfile = rfile + ".raw"

f = open(rfile, "r")
wf = open(wfile, "w")

last = 0

while True:
    data = f.read(2)
    if not data:
        break
    for i in range(len(data)/2):
        ts, = unpack('H', data[i*2:i*2+2])
        wf.write((ts-last)*chr(ts%2))
        last = ts

f.close()
wf.close()

