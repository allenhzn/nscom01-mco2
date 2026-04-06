import argparse
import time

from rtp_receiver import Receiver
from sdp import Codec

parser = argparse.ArgumentParser(
    description="Receive a .wav file over RTP or enable real-time microphone capture"
)

CODECS = ["PCMA", "PCMU", "L16_STEREO", "L16_MONO"]

parser.add_argument("--port", help="Port to receive on", type=int, default=6011)
subparsers = parser.add_subparsers(dest="command")
file = subparsers.add_parser("file", help="Receive a .wav file")

file.add_argument(
    "codec",
    metavar="codec",
    help=f"The audio codec for the .wav file. Options are: {CODECS}",
    choices=CODECS,
)

args = parser.parse_args()
CODEC = Codec.from_str(args.codec)

if args.command == "file":
    receiver = Receiver(codec=CODEC, port=6011)
    receiver.start()

    while True:
        time.sleep(0.1)