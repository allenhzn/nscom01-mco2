import argparse

import ffmpeg

from sdp import Codec
from sip_client import Client

CODECS = ["PCMA", "PCMU", "L16_STEREO", "L16_MONO"]

parser = argparse.ArgumentParser(
    description="Send a .wav file or activate real-time microphone capture."
)

subparsers = parser.add_subparsers(dest="command")
file = subparsers.add_parser("file", help="Send a .wav file")

file.add_argument(
    "path",
    metavar="path",
    help="The file path for the .wav file to send (relative to current directory)",
)

file.add_argument(
    "codec",
    metavar="codec",
    help=f"The audio codec for the .wav file. Options are: {CODECS}",
    choices=CODECS,
)

mic = subparsers.add_parser("mic", help="Enable real-time microphone capture")
args = parser.parse_args()
CODEC = Codec.from_str(args.codec)

if args.command == "file":
    sip_client = Client("0.0.0.0", 5060, file_path=args.path)
    sip_client.start()
else:
    sip_client = Client("0.0.0.0", 5060)