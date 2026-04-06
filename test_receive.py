import time
from rtp_receiver import Receiver
from sdp import Codec

def test():
    CODEC = Codec.L16_MONO
    PORT = 5004

    receiver = Receiver(codec=CODEC, port=PORT)
    receiver.start()

    while True:
            time.sleep(1)

if __name__ == '__main__':
    test()