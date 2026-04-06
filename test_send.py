import wave
from rtp_sender import Sender
from sdp import Codec

def test():
    CODEC = Codec.L16_STEREO

    sender = Sender(codec=CODEC, port=5005, dest_ip='127.0.0.1', dest_port=5004)

    with wave.open('test.wav', 'rb') as wav:
        raw = wav.readframes(wav.getnframes())

    sender.send(raw)
    print('done')

if __name__ == '__main__':
    test()