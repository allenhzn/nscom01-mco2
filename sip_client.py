import socket
from sip_messages import Invite, Message, Ack, Bye, Sip_Ack
from sdp import Codec
import time

class Client:
    def __init__(self, client_socket: socket, client_addr: str, client_port: int):
        self.client_socket = client_socket
        self.CLIENT_ADDR = client_addr
        self.CLIENT_PORT = client_port
        self.SERVER_ADDR = None
        self.SERVER_PORT = None
        self.CODEC_CHOICE = None
        self.CODEC_CHOICES = [Codec.PCMU.payload_type, Codec.PCMA.payload_type, Codec.L16_MONO.payload_type, Codec.L16_STEREO.payload_type]
        # how many hops it can do
        self.MAX_FORWARDS = 1
        # the ID of the entire SIP dialog, I chose some random string + client IP
        self.CALL_ID = f'bgtrts@{client_addr}'
        # who were sending to
        self.TO = 'sip:bob@domain.com'
        # who its from
        self.FRM = 'sip:alice@hereway.com'
        # information about the sender and a branch ID to identify a specific part of the SIP dialog
        self.VIA_PREFIX = f'SIP/2.0/UDP {client_addr}:{str(client_port)};branch=z9hG4bK'
        self.cseq = 1
        
        try:
            # bind to addr and port
            self.client_socket.bind((self.CLIENT_ADDR, self.CLIENT_PORT))
            print('TRACE --> binding client socket')
            
            print('TRACE --> client sending invite')
            self.send_message(
                                Invite(self.CLIENT_ADDR, self.CLIENT_PORT, self.CODEC_CHOICES,
                                    self.MAX_FORWARDS, self.CALL_ID, self.TO,
                                    self.FRM, self.VIA_PREFIX + 'invite', self.cseq).to_string(),
                                ('127.0.0.1', 60001)
                            )
            # accept messages 
            print('TRACE --> client entering receive loop')
            self.receive_loop()

            # wait for some time then close
            time.sleep(3)
            print('TRACE --> client socket closing')
            self.close()
            
        except Exception as e:
            print(f'ERROR --> {e}')

    # sends the message and retransmits if an ack was not received
    def send_message(self, message: str, addr: tuple[str, int]):

        # check what to expect
        temp = Message.to_dict(message)
        cseq_basis = int(temp['cseq'])

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

                    if rec_dict['type'].strip() == 'ACK' and int(rec_dict['cseq']) == cseq_basis:
                        self.client_socket.settimeout(None)
                        print('TRACE --> client successfully sent something')
                        return True
                    
            except socket.timeout:
                # This is where retransmission happens
                attempts += 1
                print(f'Timeout. Retry {attempts}')
                continue 
            except Exception as e:
                print(f'Unexpected error: {e}')
                break

    # sends an ack
    def send_ack(self, sequence_num: int, addr: tuple[str, int]):
        ack = Ack(1, self.CALL_ID, self.TO,
                  self.FRM, self.VIA_PREFIX + 'ack', sequence_num).to_string().encode()
        self.client_socket.sendto(ack, addr)

    # method to receive data being sent to server, make it a dict, and send an ack
    def receive(self) -> dict:
        # receive data
        data, addr = self.client_socket.recvfrom(4096)

        # decode data
        rec_str = data.decode()

        print('TRACE --> client received something')
        print(rec_str)

        rec_dict = Message.to_dict(rec_str)

        self.send_ack(int(rec_dict['cseq']), addr)

        return rec_dict
    
    def close(self):
        self.client_socket.close()

    def receive_loop(self):

        is_receiving = True
        while is_receiving:
            try:
                rec_dict = self.receive()
                print('TRACE --> client inside receive loop')

                match rec_dict['type'].strip():

                    case '200_OK':

                        print('TRACE --> client inside 200_OK')

                        if 'invite' in rec_dict['via']:

                            print('TRACE --> client inside ok inv')
                            # check cseq
                            # check max_forwards
                            if (int(rec_dict['cseq']) == self.cseq and
                                int(rec_dict['max_forwards']) > 0):

                                print('TRACE --> client received ok inv')
                                print('TRACE --> client printing ok inv')
                                print(rec_dict)

                                # store server addr and port
                                temp = Message.to_dict(rec_dict['sdp'].strip())
                                self.SERVER_ADDR = temp['server_addr'].strip()
                                self.SERVER_PORT = int(temp['server_port'])

                                # store codec choice
                                self.CODEC_CHOICE = int(temp['codec_choice'])

                                print('TRACE --> client sending sip ack')

                                # send ack
                                self.send_message(
                                                    Sip_Ack(self.MAX_FORWARDS, self.CALL_ID, self.TO,
                                                    self.FRM, self.VIA_PREFIX + 'sipack', self.cseq).to_string(),
                                                    (self.SERVER_ADDR, self.SERVER_PORT)
                                                )
                                self.cseq += 1
                                print()
                                print('TRACE --> what we got from SIP')
                                print(f'server addr: {self.SERVER_ADDR}')
                                print(f'server port: {self.SERVER_PORT}')
                                print(f'codec choice: {self.CODEC_CHOICE}')

                                # TODO: code where we start sending the audio
                                
                                # send the Bye after audio sending is complete
                                self.send_message(
                                                    Bye(self.MAX_FORWARDS, self.CALL_ID, self.TO,
                                                    self.FRM, self.VIA_PREFIX + 'bye', self.cseq).to_string(),
                                                    (self.SERVER_ADDR, self.SERVER_PORT)
                                                )
                                
                                
                        elif 'bye' in rec_dict['via']:
                            
                            print('TRACE --> client inside ok bye')
                            # check cseq
                            # check max_forwards
                            if (int(rec_dict['cseq']) == self.cseq and
                                int(rec_dict['max_forwards']) > 0):
                                print('TRACE --> client received ok bye')
                                print('TRACE --> client printing ok bye')
                                print(rec_dict)

                                print('TRACE --> client closing socket')

                                # exit the receive loop
                                is_receiving = False
                        else:
                            print('TRACE --> client inside else')
                            print(rec_dict)

                    case _:
                        print('TRACE --> client match triggered')

            except Exception as e:
                print(f'ERROR --> {e}')



if __name__=='__main__':
    ADDRESS = '127.0.0.1'
    PORT = 60000
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client = Client(sock, ADDRESS, PORT)