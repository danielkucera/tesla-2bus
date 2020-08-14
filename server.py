#!/usr/bin/python3 -u

import serial
import time
import tesla_2bus as bus
import os
import socket
import subprocess
from baresipy import BareSIP

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)
me = bus.Device(sn=3, mn=1)
my_mp = bus.Device(sn=3, mn=0)
server_address = ("127.0.0.1", 5972)

callee = os.environ['SIP_TARGET']
sip_domain = os.environ['SIP_DOMAIN']
sip_user = os.environ['SIP_USER']
sip_pass = os.environ['SIP_PASS']

to = callee+"@"+sip_domain

sip = BareSIP(sip_user, sip_pass, sip_domain, debug=True)

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

def call_phone():
    sip.call(to)
    while sip.running:
        time.sleep(0.5)
        if sip.call_established:
            return True
    return False

def frame_callback(b, frame):
    print(time.time())
    print(frame)

    cmd = frame.cmd.cmd
    if cmd in [ 10, 24 ]:
        if frame.dst in [ me, my_mp ]:
            print("calling %s\n" % (frame.dst))
            if frame.dst == me:
                f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
                b.send_frame(f)
                if call_phone():
                    f = bus.Frame(me, frame.src, bus.Cmd.from_name("accepted_call_from_phone"))
                    b.send_frame(f)
            if frame.dst == my_mp:
                if call_phone():
                    f = bus.Frame(me, my_mp, bus.Cmd.from_name("overtake_call"))
                    b.send_frame(f)
                    time.sleep(0.3)
                    f = bus.Frame(me, frame.src, bus.Cmd.from_name("accepted_call_from_eg"))
                    b.send_frame(f)
        else:
            start_recording()
    elif cmd in [ 16, 30 ]:
        if frame.dst in [ me, my_mp ]:
            print("hangup %s\n" % (frame.dst))
        else:
            stop_recording()

b = bus.Bus(ser, frame_callback)

#while True:
#    # Wait for a connection
#    print >>sys.stderr, 'waiting for a connection'
#    connection, client_address = sock.accept()


b.run()

