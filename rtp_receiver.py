import audioop
import queue
import socket
import threading
import time
from queue import PriorityQueue

import pyaudio

from rtp_packet import RtpPacket
from sdp import Codec
from rtcp_packet import RtcpRrPacket, RtcpSrPacket


class Receiver:
    def __init__(self, codec: Codec, port: int, dest_ip: str, dest_port: int):
        self.CODEC = codec

        self.CHUNK_SIZE = 0.020
        self.samples_per_chunk = int(self.CHUNK_SIZE * self.CODEC.ar)

        self.bytes_per_packet = (
            self.samples_per_chunk * self.CODEC.ac * self.CODEC.bytes_per_sample
        )
        # 20 ms chunks, ar is the sampling rate (44100/8000 hz)
        # Multiply by the number of audio channels and the codec bytes per sample

        self.buffer = PriorityQueue()
        self.BUFFER_SIZE = 3

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", port))
        self.socket.settimeout(0.5)

        self.stop_flag = threading.Event()
        self.recv_thread = threading.Thread(target=self.recv_loop, daemon=True)
        self.stream = None
        self.playback = pyaudio.PyAudio()

        self.received_pkt_count = 0
        self.packets_lost = 0
        self.from_sender_count = 0
        self.rtcp_sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtcp_sckt.bind(("0.0.0.0", port + 1))
        self.rtcp_dest = (dest_ip, dest_port + 1)
        self.rtcp_recv_thread = threading.Thread(
            target=self.rtcp_receiver_receive_loop, daemon=True
        )

    def start(self):
        self.recv_thread.start()
        self.rtcp_recv_thread.start()

        while self.buffer.qsize() < self.BUFFER_SIZE:
            time.sleep(0.001)
        # At the start wait for the buffer to fill to X packets before starting playback
        # Ideally this makes playback more consistent

        self.stream = self.playback.open(
            **self.CODEC.pyaudio_args,
            frames_per_buffer=self.samples_per_chunk,
            stream_callback=self.pyaudio_callback,
        )

    def recv_loop(self):
        latest_seq = None
        latest_timestamp = None
        last_rtcp_send_time = time.time()

        while not self.stop_flag.is_set():
            if time.time() - last_rtcp_send_time >= 5.0:
                self.receiver_report_send()
                last_rtcp_send_time = time.time()

            try:
                data, _ = self.socket.recvfrom(12 + self.bytes_per_packet)
                # 12 byte header + data bytes

                packet = RtpPacket.from_bytes(data)

                if packet.payload_type != self.CODEC.payload_type:
                    continue
                # Skip unexpected packets

                # increment received packet
                self.received_pkt_count += 1

                if (
                    latest_seq is not None
                    and packet.seq_num != (latest_seq + 1) % 2**16
                ):
                    missing_seq = (latest_seq + 1) % 2**16
                    missing_timestamp = (
                        latest_timestamp + self.samples_per_chunk
                    ) % 2**32

                    while missing_seq != packet.seq_num:
                        self.packets_lost += 1
                        self.buffer.put((missing_seq, missing_timestamp, None))
                        missing_seq = (missing_seq + 1) % 2**16
                        missing_timestamp = (
                            missing_timestamp + self.samples_per_chunk
                        ) % 2**32
                # Fill missing packets with None markers so they get replaced with silence

                latest_seq = packet.seq_num
                latest_timestamp = packet.timestamp
                self.buffer.put(
                    (latest_seq, latest_timestamp, self.to_little_endian(packet.data))
                )
            except socket.timeout:
                continue
            except OSError:
                break

    def receiver_report_send(self):
        packet = RtcpRrPacket(0, self.packets_lost)
        self.rtcp_sckt.sendto(packet.as_bytes, self.rtcp_dest)

    def rtcp_receiver_receive(self) -> RtcpSrPacket:
        # receive data
        data, addr = self.rtcp_sckt.recvfrom(4096)
        print("TRACE --> client received something")
        return RtcpSrPacket.from_bytes(data)

    def rtcp_receiver_receive_loop(self):
        while True:
            try:
                packet = self.rtcp_receiver_receive()
                self.from_sender_count = packet.packet_count
                print("Sender Report:")
                print(f"[{self.from_sender_count}] packets sent")
                print(f"[{self.packets_lost}] packets lost")

            except socket.timeout:
                continue
            except OSError:
                break

    def pyaudio_callback(self, in_data, frame_count, time_info, status):
        try:
            seq, timestamp, audio = self.buffer.get_nowait()
            if audio is None:
                audio = self.loss_concealment(frame_count)
            elif self.CODEC == Codec.PCMA:
                audio = audioop.alaw2lin(audio, 2)
            elif self.CODEC == Codec.PCMU:
                audio = audioop.ulaw2lin(audio, 2)
        except queue.Empty:
            audio = self.loss_concealment(frame_count)
        return audio, pyaudio.paContinue

    def loss_concealment(self, frame_count):
        return b"\x00" * frame_count * self.CODEC.ac * self.CODEC.bytes_per_sample
    # Empty bytes just means silence in case of lost packets

    def to_little_endian(self, data: bytes):
        if self.CODEC.bytes_per_sample == 1:
            return data
        return audioop.byteswap(data, self.CODEC.bytes_per_sample)

    def stop(self):
        self.stop_flag.set()

        if self.recv_thread.is_alive():
            self.recv_thread.join()

        if self.stream is not None and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()

        self.playback.terminate()

        self.socket.close()
        self.rtcp_sckt.close()