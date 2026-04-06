import wave
import ffmpeg

from rtp_sender import Sender
from sdp import Codec

def test():
    CODEC = Codec.PCMU

    sender = Sender(codec=CODEC, port=5005, dest_ip='127.0.0.1', dest_port=5004)

    data, _ = (
        ffmpeg.input("test.wav")
        .output("pipe:", **CODEC.ffmpeg_args)
        .global_args("-nostdin")
        .global_args("-loglevel", "error")
        .run(capture_stdout=True)
    )

    sender.send(data)


if __name__ == '__main__':
    test()