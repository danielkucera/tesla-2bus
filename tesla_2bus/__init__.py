from threading import Thread

class Device:
    def __init__(self, sn, mn=0, is_gk=False):
        self.sn = sn
        self.mn = mn
        self.is_gk = is_gk

    @classmethod
    def from_bytes(cls, bs):
        mn = bs[0] & 0b11
        sn = (bs[0] >> 2) + ((bs[1] & 0b1111) << 6)
        is_gk = (bs[1] & 0b11110000) == 0
        return cls(sn, mn, is_gk)

    def to_bytes(self):
        b0 = (self.mn & 0b11) + ((self.sn << 2) & 0b11111100)
        b1 = ((self.sn >> 6) & 0b1111) + ((not self.is_gk) * 0b10000)
        return bytearray([b0, b1])

    def __str__(self):
        return "sn:%d mn:%d is_gk:%d" % (self.sn, self.mn, self.is_gk)

    def __eq__(self, other):
        return ((self.sn, self.mn, self.is_gk) == (other.sn, other.mn, other.is_gk))

    def __ne__(self, other):
        return not (self == other)

# define bus master
Master = Device(0, 1, True)

class Cmd:

    cmd_map = {
            0b00000000: "OK",
            0b00001000: "overtake_accepted?line_busy?FAIL",
            0b00001010: "call_from_eg",
            0b00001100: "accepted_call_from_eg",
            0b00001110: "open_lock",
            0b00010000: "hangup_from_eg",
            0b00010010: "ping_phone",
            0b00010110: "request_line",
            0b00011000: "invite_from_phone",
            0b00011010: "accepted_call_from_phone",
            0b00011110: "hangup",
            0b00100011: "overtake_call",
            0b00110110: "open_audio",
            0b01000000: "ping",
            0b11100001: "configure_as_slave_1",
            0b11100010: "configure_as_slave_2",
            0b11100011: "configure_as_slave_3"
            }

    def __init__(self, cmd):
        self.cmd = cmd

    def to_bytes(self):
        return bytes([self.cmd])

    @classmethod
    def from_bytes(cls, bs):
        return cls(bs)

    @classmethod
    def from_name(cls, cmd_name):
        for cmd_nr in cls.cmd_map:
            if cmd_name == cls.cmd_map[cmd_nr]:
                return cls(cmd_nr)
        return None


    def __str__(self):
        cmd_name = "UNKNOWN"
        if self.cmd in self.cmd_map:
            cmd_name = self.cmd_map[self.cmd]
        return "%s(%d)" % (cmd_name, self.cmd)

class Frame:
    def __init__(self, src, dst, cmd):
        self.dst = dst
        self.src = src
        self.cmd = cmd

    def to_bytes_nocs(self):
        return self.dst.to_bytes() + self.src.to_bytes() + self.cmd.to_bytes()

    def checksum(self):
        bs = self.to_bytes_nocs()
        bsum = sum(bs)
        cs = (~(bsum % 0x100)+1)&0xff
        return cs

    def to_bytes(self):
        bs = self.to_bytes_nocs()
        return bs+bytes([self.checksum()])

    @classmethod
    def from_bytes(cls, bs):
        dst = Device.from_bytes(bs[0:2])
        src = Device.from_bytes(bs[2:4])
        cmd = Cmd.from_bytes(bs[4])
        return cls(src, dst, cmd)
        
    def __str__(self):
        return "src:{%s} dst:{%s} cmd:%s cs:%d" % (self.src, self.dst, self.cmd, self.checksum() )

class Bus(Thread):
    def __init__(self, port, callback=None):
        self.port = port
        self.buffer = []
        self.to_send = []
        self.callback = callback
        super().__init__()

    def symbol_from_pulse(self, val):
        if val > 56 and val < 87:
            return "1"
        elif val > 86 and val < 113:
            return "-"
        elif val > 112 and val < 138:
            return "0"
        else:
            return "?"

    def read_pulse(self):
        data = self.port.read(1)
        if len(data) != 1:
            return None
        val = ord(data)
        if val == 0xff:
            data = self.port.read(4)
            #TODO: decode
            return val
        else:
            return val

    def byte_from_symbols(self, symbols):
        b = 0
        for symbol in symbols[::-1]:
            b = b << 1
            if symbol[0] == "1":
                b += 1
        return bytearray([b])

    def bytes_from_symbols(self, symbols):
        byts = b""
        unstuff = []
        for symbol in symbols:
            if symbol[0] in ["0", "1"]:
                unstuff.append(symbol)
        for i in range(0, len(unstuff)//8):
            byts += self.byte_from_symbols(unstuff[8*i:8*(i+1)])
        return byts

    def identify_frame(self):
        idx = 0
        frame_sym_len = 6*8*2
        end = idx + frame_sym_len
        syms = self.buffer[idx:end]
        byts = self.bytes_from_symbols(syms)
        if len(byts) < 6:
            return
        frame = Frame.from_bytes(byts)
        #TODO: checksum check
        self.buffer = self.buffer[end:]
        if self.callback != None:
            self.callback(self, frame)
            print("callback finished")
        return

    def send_frame(self, frame):
        return self.port.write(frame.to_bytes())

    def run(self):
        last_symbol = None
        last_cnt = 0
        while True:
            #print("loop running", len(self.buffer))
            pulse = self.read_pulse()
            if not pulse:
                continue
            symbol = self.symbol_from_pulse(pulse)
            if symbol == last_symbol:
                last_cnt += 1
            else:
                if last_symbol == "-" and last_cnt > 40:
                    self.buffer = []
                self.buffer.append([last_symbol, last_cnt])
                last_symbol = symbol
                last_cnt = 1
                self.identify_frame()




