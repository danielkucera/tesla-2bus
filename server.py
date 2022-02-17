#!/usr/bin/python3 -u

import serial
import time
import tesla_2bus as bus
import os
import subprocess
from baresipy import BareSIP
import traceback
import logging as log

port = serial.Serial('/dev/ttyACM0', 115200, timeout=0.0001)
me = bus.Device(sn=33, mn=1)
my_mp = bus.Device(sn=33, mn=0)

callee = os.environ['SIP_TARGET']
sip_domain = os.environ['SIP_DOMAIN']
sip_user = os.environ['SIP_USER']
sip_pass = os.environ['SIP_PASS']

to = callee+"@"+sip_domain

class Caller(BareSIP):

    def __init__(self, bh, *args, **kwargs):
        self.in_call = False
        self.call_pending = False
        self.bh = bh
        super(self.__class__, self).__init__(*args, **kwargs)

    def call_phone(self):
        if not self.running:
            log.info("SIP not running")
            return False
        if self.in_call:
            log.info("Line not free")
            return False
        if self.call_pending:
            log.info("Call pending")
            return True
        self.call_pending = True
        self.call(to)
        return True

    def handle_call_status(self, status):
        log.info("NEW STATUS %s", status)

    def end_call(self):
        # TODO: check bus state and send hangup?
        self.hang()
        self.in_call = False
        self.call_pending = False
        self.bh.sip_call_end()

    def handle_call_ended(self, reason):
        # called when call timeout or hangup
        self.end_call()

    def handle_call_rejected(self, number):
        self.end_call()

    def handle_incoming_call(self, number):
        log.info("Incomming PSTN call")
        # call eg
        self.accept_call() # just for debug

    def handle_login_failure(self):
        # workaround for sipgate nonce bug
        log.warning("login failure")

    def handle_dtmf_received(self, symbol, duration):
        log.info("got dtmf {0}".format(symbol))
        if symbol == "#":
            log.info("opening door")
            self.bh.door_unlock()

    def handle_call_established(self):
        self.bh.sip_call_established()
        self.in_call = True
        self.call_pending = False


class Recorder():
    def __init__(self, *args, **kwargs):
        self.rec = None
        self.status = "IDLE"
        self.path = "/opt/tesla-2bus/recordings/"

    def start_recording(self, name):
        self.stop_recording()
        self.status = "RECORDING"
        filename = self.path + name 
        log.info("Starting recording %s", filename)
        self.rec = subprocess.Popen(["timeout","60", "arecord", "-f", "cd", "-c", "1", filename])
    
    def stop_recording(self):
        if self.status == "RECORDING":
            log.info("Stopping recording")
            self.status = "IDLE"
            if self.rec:
                log.info("Terminating...")
                self.rec.terminate()
                if not self.rec.wait(timeout=3):
                    self.rec.kill()
                    self.rec.wait()
    

class BusHandler():
    def __init__(self, *args, **kwargs):
        self.rcvd_frames = []
        self.recorder = Recorder()

        self.status = "IDLE"
        self.remote = None

        self.sip = Caller(self, sip_user, sip_pass, sip_domain, block=False, debug=False)

        self.b = bus.Bus(port, self.frame_callback)
        self.b.start()
    
        log.info("2bus handler started")

    def frame_callback(self, frame):
        log.debug("RCVD: %s" % frame)
        self.rcvd_frames.append(frame)
    
    def frame_process(self, frame):
        log.debug("STATUS: %s PROCESS: %s" % (self.status, frame))
        cmd = frame.cmd.cmd
    
        # call request
        if cmd in [ 10, 24 ]:
            self.remote = frame.src

            # call request to me
            if frame.dst == me:
                if self.status == "IDLE":
                    self.status = "CALLING_ME"
                    log.info("call to me")
                    f = bus.Frame(me, self.remote, bus.Cmd.from_name("OK"))
                    self.b.send_frame(f)
                    self.sip.call_phone()
                elif b.status == "CALLING_ME": # OK not seen
                    f = bus.Frame(me, self.remote, bus.Cmd.from_name("OK"))
                    self.b.send_frame(f)
                else:
                    log.info("PROBLEM: calling me but bus not idle")

            # call request to my mp
            elif frame.dst == my_mp:
                log.info("call to my MP")
                self.sip.call_phone()
                self.status = "CALLING_MP"

            # call request to someone else
            else:
                date = str(time.time())
                filename = "%s-%d_%d-%d_%d.wav".format(date, frame.src.sn, frame.src.mn, frame.dst.sn, frame.dst.mn)
                self.recorder.start_recording(filename)
                self.status = "RECORDING"
    
        # my mp picked-up
        if cmd == 12 and frame.src == my_mp :
            if self.status != "BUS_BUSY":
                self.sip.end_call()
                self.status = "BUS_BUSY"
    
        # hangup, cancel
        if cmd in [ 16, 30 ]: 
            self.recorder.stop_recording()
            if frame.dst ==  me:
                log.info("hangup %s" % (frame.dst))
                f = bus.Frame(me, frame.src, bus.Cmd.from_name("OK"))
                self.b.send_frame(f)
                self.sip.end_call()
            self.status = "IDLE"

    def sip_call_established(self):
        if self.status == "CALLING_ME":
            f = bus.Frame(me, self.remote, bus.Cmd.from_name("accepted_call_from_phone"))
            self.b.send_frame(f)
            self.status = "IN_CALL"
        elif self.status == "CALLING_MP":
            f = bus.Frame(me, my_mp, bus.Cmd.from_name("overtake_call"))
            self.b.send_frame(f)
            time.sleep(0.3)
            f = bus.Frame(me, self.remote, bus.Cmd.from_name("accepted_call_from_eg"))
            self.b.send_frame(f)
            self.status = "IN_CALL"

    def sip_call_end(self):
        if self.status == "IN_CALL":
            f = bus.Frame(me, self.remote, bus.Cmd.from_name("hangup"))
            self.b.send_frame(f)
            self.status = "IDLE"

    def door_unlock(self):
        if self.status == "IN_CALL":
            f = bus.Frame(me, self.remote, bus.Cmd.from_name("open_lock"))
            self.b.send_frame(f)

    def run(self):
        while True:
            if len(self.rcvd_frames) > 0:
                frame = self.rcvd_frames.pop()
                try:
                    self.frame_process(frame)
                except Exception as e:
                    log.error(e)
                    traceback.print_exc()
            else:
                time.sleep(0.0001)

bh = BusHandler()
bh.run()
