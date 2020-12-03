#!/usr/bin/python3 -u

import serial
import time
import tesla_2bus as bus
import os
import socket
import subprocess
from baresipy import BareSIP
import traceback

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.0001)
me = bus.Device(sn=3, mn=1)
my_mp = bus.Device(sn=3, mn=0)
server_address = ("127.0.0.1", 5972)

callee = os.environ['SIP_TARGET']
sip_domain = os.environ['SIP_DOMAIN']
sip_user = os.environ['SIP_USER']
sip_pass = os.environ['SIP_PASS']

to = callee+"@"+sip_domain

class Caller(BareSIP):

    def __init__(self, *args, **kwargs):
        self.in_call = False
        self.call_pending = False
        super(self.__class__, self).__init__(*args, **kwargs)

    def call_phone(self, b, src):
        if not sip.running:
            print("SIP not running")
            return False
        if self.in_call:
            print("Line not free")
            return False
        self.b = b
        self.src = src
        self.call_pending = True
        sip.call(to)
        while self.call_pending:
            print("calling", to)
            time.sleep(1)
            #TODO: handle timeout
        return self.in_call

    def handle_call_ended(self, reason):
        self.in_call = False
        f = bus.Frame(me, self.src, bus.Cmd.from_name("hangup"))
        self.b.send_frame(f)

    def handle_call_rejected(self, number):
        self.in_call = False
        self.call_pending = False

    def handle_incoming_call(self, number):
        print("Ignoring incomming PSTN call")
        # call eg
        #self.accept_call()

    def handle_login_failure(self):
        # workaround for sipgate nonce bug
        print("login failure")

    def handle_call_established(self):
        self.in_call = True
        self.call_pending = False

sip = Caller(sip_user, sip_pass, sip_domain, block=False, debug=False)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(server_address)
sock.listen(1)

rec = None
rcvd_frames = []

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

def frame_callback(b, frame):
    global rcvd_frames
    print("RCVD:", time.time(), frame)
    rcvd_frames.append(frame)

def frame_process(b, frame):
    print("PROCESS:", time.time(), frame)

    cmd = frame.cmd.cmd
    if cmd in [ 10, 24 ]:
        if frame.dst in [ me, my_mp ]:
            print("call to %s\n" % (frame.dst))
            if frame.dst == me:
                f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
                b.send_frame(f)
                time.sleep(0.3)
                if sip.call_phone(b, frame.src):
                    f = bus.Frame(me, frame.src, bus.Cmd.from_name("accepted_call_from_phone"))
                    b.send_frame(f)

            if frame.dst == my_mp:
                if sip.call_phone(b, frame.src):
                    f = bus.Frame(me, my_mp, bus.Cmd.from_name("overtake_call"))
                    b.send_frame(f)
                    time.sleep(0.3)
                    f = bus.Frame(me, frame.src, bus.Cmd.from_name("accepted_call_from_eg"))
                    b.send_frame(f)
        else:
            start_recording()
    elif cmd in [ 16, 30 ]:
        if frame.dst in [ me ]:
            print("hangup %s\n" % (frame.dst))
            f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
            b.send_frame(f)
            if sip.call_established:
                sip.hang()
        else:
            stop_recording()

b = bus.Bus(ser, frame_callback)
b.start()

#while True:
#    # Wait for a connection
#    print >>sys.stderr, 'waiting for a connection'
#    connection, client_address = sock.accept()


while True:
    if len(rcvd_frames) > 0:
        frame = rcvd_frames.pop()
        try:
            frame_process(b, frame)
        except Exception as e:
            print(e)
            traceback.print_exc()
    else:
        time.sleep(0.1)
