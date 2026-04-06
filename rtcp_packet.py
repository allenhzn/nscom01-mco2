import bitstruct

SR_HEADER_FORMAT = "u2b1u5u8u16"
SR_PAYLOAD_FORMAT = "u32u32u32u32u32u32"

class RtcpSrPacket:
    def __init__(self, ssrc: int, packet_count: int):
        self.version = 2
        self.padding = False
        self.rc = 0
        self.pt = 200
        self.length = 6
        self.ssrc = ssrc
        self.ntp_msw = 0
        self.ntp_lsw = 0
        self.rtp_ts = 0
        self.packet_count = packet_count
        self.octet_count = 0

    @property
    def as_bytes(self) -> bytes:
        header = bitstruct.pack(
            SR_HEADER_FORMAT,
            self.version,
            self.padding,
            self.rc,
            self.pt,
            self.length,
        )
        payload = bitstruct.pack(
            SR_PAYLOAD_FORMAT,
            self.ssrc,
            self.ntp_msw,
            self.ntp_lsw,
            self.rtp_ts,
            self.packet_count,
            self.octet_count,
        )
        return header + payload

    @staticmethod
    def from_bytes(data: bytes):
        _ = bitstruct.unpack_from(SR_HEADER_FORMAT, data[:4])
        payload_vals = bitstruct.unpack_from(SR_PAYLOAD_FORMAT, data[4:])
        return RtcpSrPacket(ssrc=payload_vals[0], packet_count=payload_vals[4])


RR_HEADER_FORMAT = "u2b1u5u8u16"
RR_PAYLOAD_FORMAT = "u32"
RR_BLOCK_FORMAT = "u32u8u24u32u32u32u32"


class RtcpRrPacket:
    def __init__(self, ssrc: int, packets_lost: int):
        self.version = 2
        self.padding = False
        self.rc = 1
        self.pt = 201
        self.length = 7
        self.ssrc = ssrc
        self.source_ssrc = 0
        self.fraction_lost = 0
        self.packets_lost = packets_lost
        self.ext_seq = 0
        self.jitter = 0
        self.lsr = 0
        self.dlsr = 0

    @property
    def as_bytes(self) -> bytes:
        header = bitstruct.pack(
            RR_HEADER_FORMAT,
            self.version,
            self.padding,
            self.rc,
            self.pt,
            self.length,
        )
        payload = bitstruct.pack(RR_PAYLOAD_FORMAT, self.ssrc)
        block = bitstruct.pack(
            RR_BLOCK_FORMAT,
            self.source_ssrc,
            self.fraction_lost,
            self.packets_lost,
            self.ext_seq,
            self.jitter,
            self.lsr,
            self.dlsr,
        )
        return header + payload + block

    @staticmethod
    def from_bytes(data: bytes):
        _ = bitstruct.unpack_from(RR_HEADER_FORMAT, data[:4])
        payload_vals = bitstruct.unpack_from(RR_PAYLOAD_FORMAT, data[4:8])
        block_vals = bitstruct.unpack_from(RR_BLOCK_FORMAT, data[8:])
        return RtcpRrPacket(ssrc=payload_vals[0], packets_lost=block_vals[2])
