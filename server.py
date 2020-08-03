#!/usr/bin/python3 -u

import serial
import time
import tesla_2bus as bus

ser = serial.Serial('/dev/ttyACM0', 115200)

message = b""

print("2bus capture started")

def frame_callback(frame):
    print(time.time())
    print(frame)

b = bus.Bus(ser, frame_callback)
b.run()

