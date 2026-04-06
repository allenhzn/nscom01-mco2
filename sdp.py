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