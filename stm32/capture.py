#!/usr/bin/python3

import serial
import time

BUFFER_SIZE = 1024

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

message = b""

while True:

    while True:
        data = ser.read(BUFFER_SIZE)
        if len(data) < 1:
            print("no data")
            if len(message) > 0:
                filename = "%f.bin" % (time.time())
                print(filename)
                f = open(filename, "bw")
                f.write(message)
                f.close()
                message = ""
            continue
        print("got data",len(data))
        message += data

