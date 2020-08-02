#!/usr/bin/python3

import socket
from struct import unpack
import sys
import time
import tesla_2bus as bus

def symbol_from_raw(raw):
    result = ""
    for val in raw:
        if val > 56 and val < 87:
            sym = "1"
        elif val > 86 and val < 113:
            sym = "-"
        elif val > 112 and val < 138:
            sym = "0"
        else:
            sym = "."
        result += sym
    return result

def deduplicate(bit_stream):
    dedup = []
    oldc = ""
    cc = 0
    for c in bit_stream:
        if c == oldc:
            cc += 1
        else:
            dedup.append([oldc, cc])
            oldc = c
            cc = 1
    dedup.append([oldc, cc])
    return dedup

def get_frames(bit_dedup):
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
    return frames

def b2d(string):
    e = 0
    res = 0
    for c in string:
        res += int(c)*2**e
        e += 1
    return res

def decode_frame(frame):
    if len(frame) < 40:
        return None

    chunk_size = 8
    chunks = int(len(frame)/chunk_size)
    btes = []
    for i in range(0, chunks):
        btes.append(b2d(frame[i*chunk_size:(i+1)*chunk_size]))

    bf = bus.Frame.from_bytes(btes)

    if b2d(frame[40:48]) != bf.checksum():
        print("Checksum FAIL!")
    return bf


for filename in sys.argv[1:]:
    with open(filename, "br") as file:
        raw = file.read()
        name_parts = filename.split(".")
        ts = time.ctime(int(name_parts[0]))
        print("Opening", filename, ts, "length", len(raw))
        symbols = symbol_from_raw(raw)
        dedup = deduplicate(symbols)
        #print(dedup)
        frames = get_frames(dedup)
        for frame in frames:
            print(decode_frame(frame))

        if False:
            wfile = rfile + ".raw"
            wf = open(wfile, "w")
            wf.write(result)
            wf.close()

