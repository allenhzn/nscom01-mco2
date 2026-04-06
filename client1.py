import argparse

import imageio_ffmpeg
import ffmpeg

from sdp import Codec
from sip_client import Client


ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

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
# TODO restructure so data is converted after codec is received from server
# So this codec arg is no longer necessary

mic = subparsers.add_parser("mic", help="Enable real-time microphone capture")
args = parser.parse_args()
CODEC = Codec.from_str(args.codec)

if args.command == "file":
    data, _ = (
        ffmpeg.input(args.path)
        .output("pipe:", **CODEC.ffmpeg_args)
        .global_args("-nostdin")
        .global_args("-loglevel", "error")
        .run(capture_stdout=True, cmd=ffmpeg_path)
    )

    sip_client = Client("0.0.0.0", 5060, data)
    sip_client.start()