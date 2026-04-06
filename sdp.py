from enum import Enum
import pyaudio

class Codec(Enum):
    PCMU  = ("mulaw", 8000,  1, 0,  1)
    PCMA  = ("alaw",  8000,  1, 8,  1)
    L16_MONO = ("s16le", 44100, 1, 11, 2)
    L16_STEREO = ("s16le", 44100, 2, 10, 2)

    def __init__(self, fmt, ar, ac, payload_type, bytes_per_sample):
        self.fmt = fmt
        self.ar = ar
        self.ac = ac
        self.payload_type = payload_type
        self.bytes_per_sample = bytes_per_sample

    @property
    def ffmpeg_args(self):
        return {"format": self.fmt, "ar": self.ar, "ac": self.ac}

    @property
    def pyaudio_args(self):
        return { "format": pyaudio.paInt16, "channels": self.ac, "rate": self.ar, "output": True }

    @classmethod
    def from_str(cls, string: str):
        return cls[string.upper()]

    @classmethod
    def from_payload_type(cls, payload_type: int):
        return next(c for c in cls if c.payload_type == payload_type)

    @property
    def codec_map(self):
        name_map = {
            "PCMU": "PCMU",
            "PCMA": "PCMA",
            "L16_MONO": "L16",
            "L16_STEREO": "L16",
        }
        encoding = name_map.get(self.name, self.name)
        if self.ac > 1:
            return f"{encoding}/{self.ar}/{self.ac}"
        return f"{encoding}/{self.ar}"
    # Returns the name/ar in SDP format


def create_sdp(addr: str, rtp_port: int, payload_types: list[int]) -> str:
    pts = " ".join(str(pt) for pt in payload_types)
    lines = [
        "v=0",
        f"o=- 0 0 IN IP4 {addr}",
        "s=-",
        f"c=IN IP4 {addr}",
        "t=0 0",
        f"m=audio {rtp_port} RTP/AVP {pts}",
    ]
    for pt in payload_types:
        codec = Codec.from_payload_type(pt)
        lines.append(f"a=rtpmap:{pt} {codec.codec_map}")

    return "\r\n".join(lines) + "\r\n"


def parse_sdp(sdp: str) -> dict:
    result = {"rtpmap": {}}
    for line in sdp.strip().splitlines():
        if line.startswith("c="):
            # c=IN IP4 127.0.0.1
            result["addr"] = line.split()[-1]
        elif line.startswith("m="):
            # m=audio 5004 RTP/AVP 0 8 11
            parts = line.split()
            result["rtp_port"] = int(parts[1])
            result["payload_types"] = [int(pt) for pt in parts[3:]]
        elif line.startswith("a=rtpmap:"):
            # a=rtpmap:0 PCMU/8000
            rest = line[len("a=rtpmap:"):]
            pt_str, encoding = rest.split(" ", 1)
            result["rtpmap"][int(pt_str)] = encoding.strip()
    return result