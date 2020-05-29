#!/usr/bin/python

import socket
import time
from struct import unpack

TCP_IP = 'esp-2bus.local'
TCP_PORT = 22222
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

message = ""

while True:

    while True:
        s.settimeout(1)
        try:
            data = s.recv(BUFFER_SIZE)
        except socket.timeout:
            #print("no data")
            if len(message) > 0:
                filename = "%f.bin" % (time.time())
                print(filename)
                f = open(filename, "w")
                f.write(message)
                f.close()
                message = ""
            continue
        print("got data",len(data))
        message += data
#TODO:
    try:
        s.sendall("s")
    except:
        # recreate the socket and reconnect
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(TCP_IP, TCP_PORT)
        time.sleep(1)

s.close()

