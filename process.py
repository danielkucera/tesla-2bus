#!/usr/bin/python3

import socket
from struct import unpack
import sys
import time

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
    cmd_name = ""
    if dframe["cmd"] == 0:
        cmd_name = "OK"
    elif dframe["cmd"] == 8:
        cmd_name = "overtake_accepted"
    elif dframe["cmd"] == 10:
        cmd_name = "call_from_eg"
    elif dframe["cmd"] == 12:
        cmd_name = "accepted_call_from_eg"
    elif dframe["cmd"] == 14:
        cmd_name = "open_lock"
    elif dframe["cmd"] == 16:
        cmd_name = "hangup_from_eg"
    elif dframe["cmd"] == 18:
        cmd_name = "ping_phone"
    elif dframe["cmd"] == 22:
        cmd_name = "request_line"
    elif dframe["cmd"] == 24:
        cmd_name = "invite_from_phone"
    elif dframe["cmd"] == 26:
        cmd_name = "accepted_call_from_phone"
    elif dframe["cmd"] == 30:
        cmd_name = "hangup"
    elif dframe["cmd"] == 35:
        cmd_name = "overtake_call"
    elif dframe["cmd"] == 54:
        cmd_name = "open_audio"
    elif dframe["cmd"] == 64:
        cmd_name = "ping"
    elif dframe["cmd"] == 225:
        cmd_name = "configure_as_slave_1"
    elif dframe["cmd"] == 226:
        cmd_name = "configure_as_slave_2"
    elif dframe["cmd"] == 227:
        cmd_name = "configure_as_slave_3"
    dframe["cmd_name"] = cmd_name
    #print(cs, dframe["fcs"], )
    if cs != dframe["fcs"]:
        print("Checksum FAIL!")
    return dframe


for filename in sys.argv[1:]:
    with open(filename, "br") as file:
        raw = file.read()
        name_parts = filename.split(".")
        ts = time.ctime(int(name_parts[0]))
        print("Opening", filename, ts, "length", len(raw))
        symbols = symbol_from_raw(raw)
        dedup = deduplicate(symbols)
        frames = get_frames(dedup)
        for frame in frames:
            print(decode_frame(frame))

        if False:
            wfile = rfile + ".raw"
            wf = open(wfile, "w")
            wf.write(result)
            wf.close()

