import audioop
import os
import random
import subprocess
import unittest

import ffmpeg
import imageio_ffmpeg
import numpy as np
import pyaudio

from sdp import Codec

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
# Contains an ffmpeg binary so it works regardless if user has ffmpeg on the system
# I can't believe this is real

os.environ["PATH"] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ["PATH"]
# Patch the path into the os env so ffmpeg-python can use it

# CODECS to support
# L16 44.1 kHz mono - PT 11, L16 44.1 kHz stereo - PT 10

# G.711 (referred to as PCMA for a-law and PCMU for u-law in RFC 3551)
# In RFC 3551 the sampling rates are both 8 kHz
# PCMU - PT 0, PCMA - PT 8.

# ONLY USE G.711 FOR PURE VOICE AUDIO


def convert_codec(file_path: str, target: Codec):
    output, _ = (
        ffmpeg.input(file_path)
        .output("pipe:", target.ffmpeg_args)
        .run(capture_stdout=True, capture_stderr=True)
    )

    samples_per_chunk = int(0.02 * target.ar)
    # 20 ms chunks, formula is 20 ms * target codec sampling rate

    return output, samples_per_chunk
    # Converts any .wav file to the target format so it can be sent using the protocol
    # Also returns the calculated samples per chunk for use in the protocol
    # The samples per chunk is the value we increase the timestamp by
    # TODO test with run_async if the conversion time is noticeable startup delay
    # This fully converts the file with ffmpeg before beginning to send


"""
SDP includes:
    o The type of media (video, audio, etc)
    o The transport protocol (RTP/UDP/IP, H.320, etc)
    o The format of the media (H.261 video, MPEG video, etc)

For an IP unicast session, the following are conveyed:
    o Remote address for media
    o Transport port for contact address
"""


class TestSender(unittest.TestCase):
    def test_play_L16_2(self):
        test_codec = Codec.L16_STEREO
        process = (
            ffmpeg.input("test.wav")
            .output("pipe:", **test_codec.ffmpeg_args)
            .global_args("-nostdin")
            .global_args("-loglevel", "error")
            .run_async(pipe_stdout=True)
        )

        p = pyaudio.PyAudio()
        stream = p.open(**test_codec.pyaudio_args)
        chunk_size = int(0.02 * 44100) * test_codec.bytes_per_sample

        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break

            big_endian = np.frombuffer(chunk, dtype="<i2").byteswap().tobytes()
            # Converts it to big endian (should be big endian when sent over the protocol)

            little_endian = np.frombuffer(big_endian, dtype=">i2").byteswap().tobytes()
            # Converts to little endian (the receiver should convert to little endian for proper playback)
            stream.write(little_endian)

        process.wait()
        stream.stop_stream()
        stream.close()
        p.terminate()

    def test_play_PCMA(self):
        test_codec = Codec.PCMA
        process = (
            ffmpeg.input("test_s.wav")
            .output("pipe:", **test_codec.ffmpeg_args)
            .global_args("-nostdin")
            .global_args("-loglevel", "error")
            .run_async(pipe_stdout=True)
        )

        p = pyaudio.PyAudio()
        stream = p.open(**test_codec.pyaudio_args)
        chunk_size = int(0.02 * 8000) * test_codec.bytes_per_sample

        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            converted = audioop.alaw2lin(chunk, 2)
            # PYAUDIO ONLY SUPPORTS PCM, WE GOTTA CONVERT G.711 USING AUDIOOP FOR PROPER PLAYBACK
            # alaw2lin for PCMA, ulaw2lin for PCMU
            stream.write(converted)

        process.wait()
        stream.stop_stream()
        stream.close()
        p.terminate()
