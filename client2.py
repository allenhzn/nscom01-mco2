import argparse

from sdp import Codec
from sip_server import Server

CODECS = ["PCMA", "PCMU", "L16_STEREO", "L16_MONO"]

parser = argparse.ArgumentParser(
    description="Receive a .wav file over RTP or enable real-time microphone capture"
)

subparsers = parser.add_subparsers(dest="command")
file = subparsers.add_parser("file", help="Receive a .wav file")

file.add_argument(
    "codec",
    metavar="codec",
    help=f"Target audio codec. Options are: {CODECS}",
    choices=CODECS,
)

mic = subparsers.add_parser("mic", help="Enable real-time microphone capture")
args = parser.parse_args()

if args.command == "file":
    codec = Codec.from_str(args.codec)

    sip_server = Server("0.0.0.0", 5080, target_codec=codec.payload_type)
    sip_server.start()
else:
    sip_server = Server("0.0.0.0", 5080, target_codec=Codec.L16_MONO.payload_type)
    # Force this codec to work with the mic's high sample rate

    sip_server.start()