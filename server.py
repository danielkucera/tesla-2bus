#!/usr/bin/python3 -u

import serial
import time
import tesla_2bus as bus
import socket
import subprocess

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)
me = bus.Device(sn=3, mn=1)
server_address = ("127.0.0.1", 5972)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(server_address)
sock.listen(1)

rec = None

print("2bus capture started")

def start_recording():
    global rec
    stop_recording()
    date = str(time.time())
    filename = "/opt/tesla-2bus/recordings/"+date+".wav"
    print("Starting recording %s", filename)
    rec = subprocess.Popen(["timeout","60", "arecord", "-f", "cd", "-c", "1", filename])

def stop_recording():
    global rec
    print("Stopping recording")
    if rec:
        print("Terminating...")
        rec.terminate()
        if not rec.wait(timeout=3):
            rec.kill()
            rec.wait()

def frame_callback(frame):
    print(time.time())
    print(frame)

    cmd = frame.cmd.cmd
    if cmd in [ 10, 24 ]:
        start_recording()
    elif cmd in [ 16, 30 ]:
        stop_recording()

b = bus.Bus(ser, frame_callback)

#while True:
#    # Wait for a connection
#    print >>sys.stderr, 'waiting for a connection'
#    connection, client_address = sock.accept()

f = bus.Frame(me, bus.Master, bus.Cmd.from_name("request_line"))

b.run()

