

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

# define bus master
Master = Device(0, 1, True)

class Cmd:

    cmd_map = {
            0b00000000: "OK",
            0b00001000: "overtake_accepted",
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
        return "dst:{%s} src:{%s} cmd:%s cs:%d" % (self.dst, self.src, self.cmd, self.checksum() )
