import socket
import time

from rtp_sender import Sender
from sdp import Codec, parse_sdp
from sip_messages import Ack, Bye, Invite, Message


class Client:
    def __init__(
        self,
        client_addr: str,
        client_port: int,
        data: bytes,
        rtp_port: int = 5004,
    ):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.CLIENT_ADDR = client_addr
        self.CLIENT_PORT = client_port
        self.CLIENT_RTP_PORT = rtp_port
        self.SERVER_ADDR = None
        self.SERVER_SIP_PORT = None
        self.SERVER_RTP_PORT = None
        self.CODEC_CHOICE = None
        self.CODEC_CHOICES = [
            Codec.PCMU.payload_type,
            Codec.PCMA.payload_type,
            Codec.L16_MONO.payload_type,
            Codec.L16_STEREO.payload_type,
        ]
        # how many hops it can do (70 as seen in the RFC)
        self.MAX_FORWARDS = 70
        # the ID of the entire SIP dialog, I chose some random string + client IP
        self.CALL_ID = f"bgtrts@{client_addr}"
        # who were sending to
        self.TO = "sip:bob@domain.com"
        # who its from
        self.FRM = "sip:alice@hereway.com"
        # information about the sender and a branch ID to identify a specific part of the SIP dialog
        self.VIA_PREFIX = f"SIP/2.0/UDP {client_addr}:{str(client_port)};branch=z9hG4bK"

        self.cseq = 1

        self.data = data

    def start(self):
        try:
            # bind to addr and port
            self.client_socket.bind((self.CLIENT_ADDR, self.CLIENT_PORT))
            print("TRACE --> binding client socket")

            print("TRACE --> client sending invite")
            self.send_message(
                Invite(
                    self.CLIENT_ADDR,
                    self.CLIENT_RTP_PORT,
                    self.CODEC_CHOICES,
                    self.MAX_FORWARDS,
                    self.CALL_ID,
                    self.TO,
                    self.FRM,
                    self.VIA_PREFIX + "invite",
                    self.cseq,
                ).to_string(),
                ("127.0.0.1", 5080),
            )
            # accept messages
            print("TRACE --> client entering receive loop")
            self.receive_loop()

            # wait for some time then close
            time.sleep(3)
            print("TRACE --> client socket closing")
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
        self.client_socket.settimeout(0.5)

        attempts = 0

        while attempts < 3:
            # send the message
            self.client_socket.sendto(message.encode(), addr)

            try:
                while True:
                    # receive data
                    data, a = self.client_socket.recvfrom(4096)
                    # decode data
                    rec_str = data.decode()
                    rec_dict = Message.to_dict(rec_str)

                    rec_cseq = int(rec_dict["CSeq"].split()[0])

                    if rec_dict.get("method") == "ACK" and rec_cseq == cseq_basis:
                        self.client_socket.settimeout(None)
                        print("TRACE --> client successfully sent something")
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
        self.client_socket.sendto(ack, addr)

    # method to receive data being sent to server, make it a dict, and send an ack
    def receive(self) -> tuple[dict, tuple[str, int]]:
        # receive data
        data, addr = self.client_socket.recvfrom(4096)

        # decode data
        rec_str = data.decode()

        print("TRACE --> client received something")
        print(rec_str)

        rec_dict = Message.to_dict(rec_str)

        self.send_ack(int(rec_dict["CSeq"].split()[0]), addr)

        return rec_dict, addr

    def close(self):
        self.client_socket.close()

    def receive_loop(self):
        is_receiving = True
        while is_receiving:
            try:
                rec_dict, sender_addr = self.receive()
                print("TRACE --> client inside receive loop")

                # Check if this is a response
                status_code = rec_dict.get("status_code")

                match status_code:
                    case 200:
                        print("TRACE --> client inside 200 OK")

                        via = rec_dict.get("Via", "")

                        if "invite" in via:
                            print("TRACE --> client inside ok inv")
                            cseq_num = int(rec_dict["CSeq"].split()[0])
                            max_fwd = int(rec_dict["Max-Forwards"])
                            # check cseq, max_forwards
                            if cseq_num == self.cseq and max_fwd > 0:
                                print("TRACE --> client received ok inv")
                                print("TRACE --> client printing ok inv")
                                print(rec_dict)

                                # server SIP address from the UDP source
                                self.SERVER_ADDR = sender_addr[0]
                                self.SERVER_SIP_PORT = sender_addr[1]

                                # RTP port and codec from SDP
                                sdp = parse_sdp(rec_dict["sdp"])
                                self.SERVER_RTP_PORT = sdp["rtp_port"]
                                self.CODEC_CHOICE = sdp["payload_types"][0]

                                print("TRACE --> client sending sip ack")

                                self.client_socket.sendto(
                                    Ack(
                                        self.MAX_FORWARDS,
                                        self.CALL_ID,
                                        self.TO,
                                        self.FRM,
                                        self.VIA_PREFIX + "sipack",
                                        self.cseq,
                                    ).to_string().encode(),
                                    (self.SERVER_ADDR, self.SERVER_SIP_PORT),
                                )
                                self.cseq += 1
                                print()
                                print("TRACE --> what we got from SIP")
                                print(f"server addr: {self.SERVER_ADDR}")
                                print(f"server sip port: {self.SERVER_SIP_PORT}")
                                print(f"server rtp port: {self.SERVER_RTP_PORT}")

                                codec = Codec.from_payload_type(self.CODEC_CHOICE)
                                print(f"codec choice: {codec}")

                                print("Initializing RTP sender...")
                                rtp_sender = Sender(
                                    codec,
                                    0,
                                    self.SERVER_ADDR,
                                    self.SERVER_RTP_PORT,
                                )
                                rtp_sender.send(self.data)
                                # TODO: code where we start sending the audio

                                # send the Bye after audio sending is complete
                                self.client_socket.sendto(
                                    Bye(
                                        self.MAX_FORWARDS,
                                        self.CALL_ID,
                                        self.TO,
                                        self.FRM,
                                        self.VIA_PREFIX + "bye",
                                        self.cseq,
                                    ).to_string().encode(),
                                    (self.SERVER_ADDR, self.SERVER_SIP_PORT),
                                )

                        elif "bye" in via:
                            print("TRACE --> client inside ok bye")
                            cseq_num = int(rec_dict["CSeq"].split()[0])
                            max_fwd = int(rec_dict["Max-Forwards"])
                            # check cseq, max_forwards
                            if cseq_num == self.cseq and max_fwd > 0:
                                print("TRACE --> client received ok bye")
                                print("TRACE --> client printing ok bye")
                                print(rec_dict)

                                print("TRACE --> client closing socket")

                                # exit the receive loop
                                is_receiving = False
                        else:
                            print("TRACE --> client inside else")
                            print(rec_dict)

                    case _:
                        print("TRACE --> client match triggered")

            except Exception as e:
                print(f"ERROR --> {e}")
