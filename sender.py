import audioop
import os
import random
import unittest

import ffmpeg
import imageio_ffmpeg
import numpy as np
import pyaudio

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

CODECS = {
    "PCMU": {
        "ffmpeg": {"format": "mulaw", "ar": 8000, "ac": 1},
        "payload_type": 0,
        "bytes_per_sample": 1,
    },
    "PCMA": {
        "ffmpeg": {"format": "alaw", "ar": 8000, "ac": 1},
        "payload_type": 0,
        "bytes_per_sample": 1,
    },
    "L16_1": {
        "ffmpeg": {"format": "s16le", "ar": 44100, "ac": 1},
        "payload_type": 11,
        "bytes_per_sample": 2,
    },
    "L16_2": {
        "ffmpeg": {"format": "s16le", "ar": 44100, "ac": 2},
        "payload_type": 10,
        "bytes_per_sample": 2,
    },
}

def convert_codec(file_path, codec):
    target = CODECS.get(codec, CODECS["L16_2"])
    ffmpeg_args = target["ffmpeg"]
    # Default to L16_2

    output, _ = (
        ffmpeg.input(file_path)
        .output("pipe:", ffmpeg_args)
        .run(capture_stdout=True, capture_stderr=True)
    )

    samples_per_chunk = int(0.02 * ffmpeg_args["ar"])
    # 20 ms chunks, formula is 20 ms * target codec sampling rate
    payload_type = target["payload_type"]

    return output, samples_per_chunk, payload_type
    # Converts any .wav file to the target format so it can be sent using the protocol
    # Also returns the calculated samples per chunk and payload type for use in the protocol
    # The samples per chunk is the value we increase the timestamp by
    # TODO test with run_async if the conversion time is noticeable startup delay
    # This fully converts the file with ffmpeg before beginning to send

class TestSender(unittest.TestCase):
    def test_play_L16_2(self):
        test_codec = "L16_2"
        process = (
            ffmpeg.input("test.wav")
            .output("pipe:", **CODECS[test_codec]["ffmpeg"])
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, output=True)
        CHUNK_SIZE = int(0.02 * 44100) * CODECS[test_codec]["bytes_per_sample"]
        while True:
            chunk = process.stdout.read(CHUNK_SIZE)
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
        test_codec = "PCMA"
        process = (
            ffmpeg.input("test_s.wav")
            .output("pipe:", **CODECS[test_codec]["ffmpeg"])
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=8000, output=True)
        CHUNK_SIZE = int(0.02 * 8000) * CODECS[test_codec]["bytes_per_sample"]
        while True:
            chunk = process.stdout.read(CHUNK_SIZE)
            if not chunk:
                break

            big_endian = np.frombuffer(chunk, dtype="<i2").byteswap().tobytes()
            # Converts it to big endian (should be big endian when sent over the protocol)

            little_endian = np.frombuffer(big_endian, dtype=">i2").byteswap().tobytes()
            # Converts to little endian (the receiver should convert to little endian for proper playback)

            converted = audioop.alaw2lin(little_endian, 2)
            # PYAUDIO ONLY SUPPORTS PCM, WE GOTTA CONVERT G.711 USING AUDIOOP FOR PROPER PLAYBACK
            # alaw2lin for PCMA, ulaw2lin for PCMU
            stream.write(converted)

        process.wait()
        stream.stop_stream()
        stream.close()
        p.terminate()
