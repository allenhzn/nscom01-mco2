import socket
import time
from typing import Any

from rtp_receiver import Receiver
from sdp import Codec, parse_sdp
from sip_messages import Ack, Message, Ok


class Server:
    def __init__(
        self,
        server_addr: str,
        server_port: int,
        rtp_port: int = 5004,
        target_codec: int = None,
    ):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.SERVER_ADDR = server_addr
        self.SERVER_PORT = server_port
        self.SERVER_RTP_PORT = rtp_port
        self.CLIENT_ADDR = None
        self.CLIENT_PORT = None
        self.CLIENT_RTP_PORT = None
        # how many hops it can do
        self.MAX_FORWARDS = 70
        # the ID of the entire SIP dialog, which it gets from the client
        self.CALL_ID = None
        # who were sending to
        self.TO = "sip:alice@hereway.com"
        # who its from
        self.FRM = "sip:bob@domain.com"
        # information about the sender and a branch ID to identify a specific part of the SIP dialog
        self.VIA_PREFIX = f"SIP/2.0/UDP {server_addr}:{str(server_port)};branch=z9hG4bK"
        self.cseq = 1

        self.TARGET_CODEC = target_codec
        # Codec we're aiming for before handshake

        self.NEGOTIATED_CODEC = None
        # Codec after handshake with client

        self.rtp_receiver = None

    def start(self):
        try:
            # bind to addr and port
            self.server_socket.bind((self.SERVER_ADDR, self.SERVER_PORT))
            print("TRACE --> binding server socket")

            # accept messages
            print("TRACE --> server entering receive loop")
            self.receive_loop()

            # wait for some time then close
            time.sleep(3)
            print("TRACE --> server socket closing")
            self.close()

        except Exception as e:
            print(f"ERROR --> {e}")

    # sends the message and retransmits if an ack was not received
    def send_message(self, message: str, addr: tuple[str, int]):
        # check what to expect
        temp = Message.to_dict(message)
        cseq_line = temp["CSeq"]
        cseq_basis = int(cseq_line.split()[0])

        # set the timeout to half a second
        self.server_socket.settimeout(0.5)

        attempts = 0

        while attempts < 3:
            # send the message
            self.server_socket.sendto(message.encode(), addr)

            try:
                while True:
                    # receive data
                    data, a = self.server_socket.recvfrom(4096)
                    # decode data
                    rec_str = data.decode()
                    rec_dict = Message.to_dict(rec_str)

                    rec_cseq = int(rec_dict["CSeq"].split()[0])

                    if rec_dict.get("method") == "ACK" and rec_cseq == cseq_basis:
                        self.server_socket.settimeout(None)
                        self.cseq += 1
                        print("TRACE --> server successfully sent something")
                        return True

            except socket.timeout:
                # This is where retransmission happens
                attempts += 1
                print(f"Timeout. Retry {attempts}")
                continue
            except Exception as e:
                print(f"Unexpected error: {e}")
                break

    # sends an ack
    def send_ack(self, sequence_num: int, addr: tuple[str, int]):
        ack = (
            Ack(
                1,
                self.CALL_ID,
                self.TO,
                self.FRM,
                self.VIA_PREFIX + "ack",
                sequence_num,
            )
            .to_string()
            .encode()
        )
        self.server_socket.sendto(ack, addr)

    # method to receive data being sent to server, make it a dict, and send an ack
    def receive(self) -> tuple[dict, Any]:
        # receive data
        data, addr = self.server_socket.recvfrom(4096)

        # decode data
        rec_str = data.decode()
        print("TRACE --> server received something")
        print(rec_str)
        rec_dict = Message.to_dict(rec_str)
        self.cseq = int(rec_dict["CSeq"].split()[0])

        return rec_dict, addr

    def close(self):
        self.server_socket.close()

    def start_rtp_receive(self):
        codec = Codec.from_payload_type(self.NEGOTIATED_CODEC)
        self.rtp_receiver = Receiver(codec, self.CLIENT_RTP_PORT)
        self.rtp_receiver.start()

    # main flow of the protocol on the server side
    def receive_loop(self):
        is_receiving = True

        while is_receiving:
            try:
                rec_dict, addr = self.receive()
                print("TRACE --> server inside receive loop")

                method = rec_dict.get("method", "")

                match method:
                    case "INVITE":
                        print("TRACE --> server inside INVITE")
                        self.send_ack(int(rec_dict["CSeq"].split()[0]), addr)
                        via = rec_dict.get("Via", "")
                        cseq_num = int(rec_dict["CSeq"].split()[0])
                        max_fwd = int(rec_dict["Max-Forwards"])
                        # check via, cseq, max_forwards
                        if "invite" in via and cseq_num == self.cseq and max_fwd > 0:
                            print("TRACE --> server received invite")
                            print("TRACE --> server printing invite")
                            print(rec_dict)

                            # store call_id
                            self.CALL_ID = rec_dict["Call-ID"].strip()

                            # client SIP address from the UDP source
                            self.CLIENT_ADDR = addr[0]
                            self.CLIENT_PORT = addr[1]

                            # RTP port and codecs from SDP
                            sdp = parse_sdp(rec_dict["sdp"])
                            self.CLIENT_RTP_PORT = sdp["rtp_port"]
                            codec_choices = sdp["payload_types"]

                            print(f"TRACE --> actual list of choices: {codec_choices}")

                            if self.TARGET_CODEC is not None:
                                self.NEGOTIATED_CODEC = self.TARGET_CODEC
                            else:
                                self.NEGOTIATED_CODEC = codec_choices[0]
                            # Default to first codec

                            print("TRACE --> server sending ok")

                            # send Ok
                            self.send_message(
                                Ok(
                                    self.SERVER_ADDR,
                                    self.SERVER_RTP_PORT,
                                    self.NEGOTIATED_CODEC,
                                    self.MAX_FORWARDS,
                                    self.CALL_ID,
                                    self.TO,
                                    self.FRM,
                                    self.VIA_PREFIX + "invite",
                                    self.cseq,
                                    "INVITE",
                                ).to_string(),
                                (self.CLIENT_ADDR, self.CLIENT_PORT),
                            )

                    case "ACK":
                        print("TRACE --> server inside ACK")
                        via = rec_dict.get("Via", "")
                        cseq_num = int(rec_dict["CSeq"].split()[0])
                        max_fwd = int(rec_dict["Max-Forwards"])
                        call_id = rec_dict["Call-ID"].strip()
                        # check via, cseq, max_forwards, call_id
                        if (
                            "sipack" in via
                            and cseq_num == self.cseq
                            and max_fwd > 0
                            and call_id == self.CALL_ID
                        ):
                            print("TRACE --> server received sip ack")
                            print("TRACE --> server printing sip ack")
                            print(rec_dict)
                            print()
                            print("TRACE --> what we got from SIP")
                            print(f"client addr: {self.CLIENT_ADDR}")
                            print(f"client sip port: {self.CLIENT_PORT}")
                            print(f"client rtp port: {self.CLIENT_RTP_PORT}")
                            print(f"codec choice: {self.NEGOTIATED_CODEC}")

                            print("SIP details acquired, initializing RTP Receiver")
                            if not self.rtp_receiver:
                                self.start_rtp_receive()

                    case "BYE":
                        print("TRACE --> server inside BYE")
                        via = rec_dict.get("Via", "")
                        cseq_num = int(rec_dict["CSeq"].split()[0])
                        max_fwd = int(rec_dict["Max-Forwards"])
                        call_id = rec_dict["Call-ID"].strip()
                        # check via, cseq, max_forwards, call_id
                        if (
                            "bye" in via
                            and cseq_num == self.cseq
                            and max_fwd > 0
                            and call_id == self.CALL_ID
                        ):
                            print("TRACE --> server received bye")
                            print("TRACE --> server printing bye")
                            print(rec_dict)

                            print("TRACE --> server sending ok")

                            # send Ok
                            self.send_message(
                                Ok(
                                    self.SERVER_ADDR,
                                    self.SERVER_RTP_PORT,
                                    self.NEGOTIATED_CODEC,
                                    self.MAX_FORWARDS,
                                    self.CALL_ID,
                                    self.TO,
                                    self.FRM,
                                    self.VIA_PREFIX + "bye",
                                    self.cseq,
                                    "BYE",
                                ).to_string(),
                                (self.CLIENT_ADDR, self.CLIENT_PORT),
                            )

                            print("TRACE --> server closing socket")

                            # close RTP receiver
                            if self.rtp_receiver:
                                self.rtp_receiver.stop()

                            # exit the receive loop
                            is_receiving = False

                    case _:
                        print("TRACE --> server match triggered")

            except Exception as e:
                print(f"ERROR --> {e}")
