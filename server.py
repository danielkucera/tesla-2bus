#!/usr/bin/python3 -u

import serial
import time
import tesla_2bus as bus
import os
import socket
import subprocess
from baresipy import BareSIP
import traceback
import logging as log

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
            log.info("SIP not running")
            return False
        if self.in_call:
            log.info("Line not free")
            return False
        self.b = b
        self.src = src
        sip.call(to)
        return True

    def handle_call_status(self, status):
        log.info("NEW STATUS %s", status)

    def handle_call_ended(self, reason):
        # called when call timeout or hangup
        self.in_call = False
        self.call_pending = False

    def handle_call_rejected(self, number):
        self.in_call = False
        self.call_pending = False

    def handle_incoming_call(self, number):
        log.info("Ignoring incomming PSTN call")
        # call eg
        #self.accept_call()

    def handle_login_failure(self):
        # workaround for sipgate nonce bug
        log.warning("login failure")

    def handle_call_established(self):
        if b.call_status == "CALLING_ME":
            f = bus.Frame(me, frame.src, bus.Cmd.from_name("accepted_call_from_phone"))
            b.send_frame(f)
        elif b.call_status == "CALLING_MP":
            f = bus.Frame(me, my_mp, bus.Cmd.from_name("overtake_call"))
            b.send_frame(f)
            f = bus.Frame(me, frame.src, bus.Cmd.from_name("accepted_call_from_eg"))
            b.send_frame(f)
        self.in_call = True
        self.call_pending = False

sip = Caller(sip_user, sip_pass, sip_domain, block=False, debug=False)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(server_address)
sock.listen(1)

rec = None
rcvd_frames = []

log.info("2bus capture started")

def start_recording():
    global rec
    stop_recording()
    date = str(time.time())
    filename = "/opt/tesla-2bus/recordings/"+date+".wav"
    log.info("Starting recording %s", filename)
    rec = subprocess.Popen(["timeout","60", "arecord", "-f", "cd", "-c", "1", filename])

def stop_recording():
    global rec
    log.info("Stopping recording")
    if rec:
        log.info("Terminating...")
        rec.terminate()
        if not rec.wait(timeout=3):
            rec.kill()
            rec.wait()

def frame_callback(b, frame):
    global rcvd_frames
    log.debug("RCVD: %s" % frame)
    rcvd_frames.append(frame)

def frame_process(b, frame):
    log.debug("STATUS: %s PROCESS: %s" % (b.call_status, frame))
    cmd = frame.cmd.cmd

    if b.call_status == "IDLE":
        if cmd in [ 10, 24 ]:
            if frame.dst == me:
                log.info("call to me\n")
                b.call_status = "CALLING_ME"
                f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
                b.send_frame(f)
                sip.call_phone(b, frame.src)
            elif frame.dst == my_mp:
                log.info("call to my MP\n")
                b.call_status = "CALLING_MP"
                sip.call_phone(b, frame.src)
            else:
                b.call_status = "CALLING_OTHER"
                start_recording()
    elif b.call_status in "CALLING_ME":
        if cmd in [ 16, 30 ]:
            b.call_status = "IDLE"
            log.info("hangup %s\n" % (frame.dst))
            if frame.dst ==  me:
                f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
                b.send_frame(f)
            sip.hang()
        if cmd in [ 10, 24 ]: # OK not seen
            f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
            b.send_frame(f)
    elif b.call_status == "CALLING_MP":
        if cmd in [ 16, 30 ]:
            b.call_status = "IDLE"
            log.info("hangup %s\n" % (frame.dst))
            sip.hang()
    elif b.call_status == "CALLING_OTHER":
        if cmd in [ 16, 30 ]:
            b.call_status = "IDLE"
            stop_recording()

b = bus.Bus(ser, frame_callback)
b.call_status = "IDLE"
b.start()

while True:
    if len(rcvd_frames) > 0:
        frame = rcvd_frames.pop()
        try:
            frame_process(b, frame)
        except Exception as e:
            log.error(e)
            traceback.print_exc()
    else:
        time.sleep(0.0001)
