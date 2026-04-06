import argparse

import ffmpeg

from rtp_sender import Sender
from sdp import Codec

CODECS = ["PCMA", "PCMU", "L16_STEREO", "L16_MONO"]

parser = argparse.ArgumentParser(
    description="Send a .wav file or activate real-time microphone capture."
)

parser.add_argument("--ip", help="Destination IP address", default="127.0.0.1")
parser.add_argument("--port", help="Destination port", type=int, default=6011)

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
    data, _ = (
        ffmpeg.input(args.path)
        .output("pipe:", **CODEC.ffmpeg_args)
        .global_args("-nostdin")
        .global_args("-loglevel", "error")
        .run(capture_stdout=True)
    )

    sender = Sender(
        codec=CODEC, port=6001, dest_ip=args.ip, dest_port=args.port
    )

    sender.send(data)