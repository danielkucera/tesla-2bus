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
me = bus.Device(sn=33, mn=1)
my_mp = bus.Device(sn=33, mn=0)
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

    def end_call(self):
        # TODO: check bus state and send hangup?
        self.hang()
        self.in_call = False
        self.call_pending = False
        if b.call_status == "IN_CALL":
            f = bus.Frame(me, frame.src, bus.Cmd.from_name("hangup"))
            b.send_frame(f)
            b.call_status = "IDLE"

    def handle_call_ended(self, reason):
        # called when call timeout or hangup
        self.end_call()

    def handle_call_rejected(self, number):
        self.end_call()

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
            b.call_status = "IN_CALL"
        elif b.call_status == "CALLING_MP":
            f = bus.Frame(me, my_mp, bus.Cmd.from_name("overtake_call"))
            b.send_frame(f)
            f = bus.Frame(me, frame.src, bus.Cmd.from_name("accepted_call_from_eg"))
            b.send_frame(f)
            b.call_status = "IN_CALL"
        self.in_call = True
        self.call_pending = False

sip = Caller(sip_user, sip_pass, sip_domain, block=False, debug=False)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(server_address)
sock.listen(1)

rec = None
rcvd_frames = []

log.info("2bus capture started")

def start_recording(frame):
    global rec
    stop_recording()
    date = str(time.time())
    filename = "/opt/tesla-2bus/recordings/%s-%d_%d-%d_%d.wav" % (date, frame.src.sn, frame.src.mn, frame.dst.sn, frame.dst.mn)
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

    if cmd in [ 10, 24 ]:
        if frame.dst == me:
            if b.call_status == "IDLE":
                log.info("call to me")
                f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
                b.send_frame(f)
                sip.call_phone(b, frame.src)
                b.call_status = "CALLING_ME"
            elif b.call_status == "CALLING_ME": # OK not seen
                f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
                b.send_frame(f)
            else:
                log.info("PROBLEM: calling me but bus not idle")
        elif frame.dst == my_mp:
            log.info("call to my MP")
            sip.call_phone(b, frame.src)
            b.call_status = "CALLING_MP"
        else:
            start_recording(frame)
            b.call_status = "RECORDING"

    if cmd == 12 and frame.src == my_mp : #MP picked-up
        if b.call_status != "IDLE":
            sip.end_call()
            b.call_status = "IDLE"

    # hangup, cancel
    if cmd in [ 16, 30 ]: 
        if b.call_status == "RECORDING":
            stop_recording()
        if frame.dst ==  me:
            log.info("hangup %s" % (frame.dst))
            f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
            b.send_frame(f)
            sip.end_call()
        b.call_status = "IDLE"

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
