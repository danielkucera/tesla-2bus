#!/usr/bin/python3 -u

import serial
import time

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

message = b""

print("2bus capture started")
while True:

    while True:
        data = ser.read(1)
        if len(data) < 1 or data == 0xff:
            if len(message) > 0:
                filename = "%f.bin" % (time.time())
                print(filename)
                f = open(filename, "bw")
                f.write(message)
                f.close()
                message = b""
            continue
        print("got data",len(data))
        message += data

