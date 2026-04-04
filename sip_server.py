import socket
import ast
from sip_messages import Ok, Message, Ack
import time

class Server:
    def __init__(self, server_socket: socket, server_addr: str, server_port: int):
        """
            properties of server
        """
        self.server_socket = server_socket
        self.SERVER_ADDR = server_addr
        self.SERVER_PORT = server_port
        self.CLIENT_ADDR = None
        self.CLIENT_PORT = None
        # how many hops it can do
        self.MAX_FORWARDS = 1
        # the ID of the entire SIP dialog, which it gets from the client
        self.CALL_ID = None
        # who were sending to
        self.TO = 'sip:alice@hereway.com'
        # who its from
        self.FRM = 'sip:bob@domain.com'
        # information about the sender and a branch ID to identify a specific part of the SIP dialog
        self.VIA_PREFIX = f'SIP/2.0/UDP {server_addr}:{str(server_port)};branch=z9hG4bK'
        self.cseq = 1
        self.CODEC_CHOICE = None

        """
            methods when making server
        """

        try:
            # bind to addr and port
            self.server_socket.bind((self.SERVER_ADDR, self.SERVER_PORT))
            print('TRACE --> binding server socket')
            
            # accept messages 
            print('TRACE --> server entering receive loop')
            self.receive_loop()

            # wait for some time then close
            time.sleep(3)
            print('TRACE --> server socket closing')
            self.close()

        except Exception as e:
            print(f'ERROR --> {e}')

    # sends the message and retransmits if an ack was not received
    def send_message(self, message: str, addr: tuple[str, int]):

        # check what to expect
        temp = Message.to_dict(message)
        cseq_basis = int(temp['cseq'])

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

                    if rec_dict['type'].strip() == 'ACK' and int(rec_dict['cseq']) == cseq_basis:
                        self.server_socket.settimeout(None)
                        self.cseq += 1
                        print('TRACE --> server successfully sent something')
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
        self.server_socket.sendto(ack, addr)

    # method to receive data being sent to server, make it a dict, and send an ack
    def receive(self) -> dict:
        # receive data
        data, addr = self.server_socket.recvfrom(4096)

        # decode data
        rec_str = data.decode()

        print('TRACE --> server received something')
        print(rec_str)

        rec_dict = Message.to_dict(rec_str)

        self.send_ack(int(rec_dict['cseq']), addr)

        self.cseq = int(rec_dict['cseq'])

        return rec_dict
    
    def close(self):
        self.server_socket.close()

    # main flow of the protocol on the server side
    def receive_loop(self):

        is_receiving = True

        while is_receiving:
            try:
                rec_dict = self.receive()
                print('TRACE --> server inside receive loop')

                match rec_dict['type'].strip():

                    case 'INVITE':
                        print('TRACE --> server inside INVITE')
                        # check via
                        # check cseq
                        # check max_forwards
                        if ('invite' in rec_dict['via'] and
                             int(rec_dict['cseq']) == self.cseq and
                             int(rec_dict['max_forwards']) > 0):
                            
                            print('TRACE --> server received invite')
                            print('TRACE --> server printing invite')
                            print(rec_dict)
                            
                            # store call_id
                            self.CALL_ID = rec_dict['call_id'].strip()

                            # store client addr and port
                            temp = Message.to_dict(rec_dict['sdp'])
                            self.CLIENT_ADDR = temp['client_addr'].strip()
                            self.CLIENT_PORT = int(temp['client_port'])

                            # grab codec choices and turn them into a list
                            codec_choices = ast.literal_eval(temp['codec_choices']) 

                            print(f'TRACE --> actual list of choices: {codec_choices}')

                            # save the first item on the list as our codec choice
                            self.CODEC_CHOICE = codec_choices[0]

                            print('TRACE --> server sending ok')

                            # send Ok
                            self.send_message(
                                                Ok(self.SERVER_ADDR, self.SERVER_PORT, self.CODEC_CHOICE,
                                                self.MAX_FORWARDS, self.CALL_ID, self.TO, self.FRM,
                                                self.VIA_PREFIX + 'invite', self.cseq).to_string(),
                                                (self.CLIENT_ADDR, self.CLIENT_PORT)
                                            )



                    case 'SIP_ACK':
                        print('TRACE --> server inside SIP_ACK')
                        # check via
                        # check cseq
                        # check max_forwards
                        # check call_id
                        if ('sipack' in rec_dict['via'] and
                            int(rec_dict['cseq']) == self.cseq and
                            int(rec_dict['max_forwards']) > 0 and
                            rec_dict['call_id'].strip() == self.CALL_ID):
                            
                            print('TRACE --> server received sip ack')
                            print('TRACE --> server printing sip ack')
                            print(rec_dict)
                            print()
                            print('TRACE --> what we got from SIP')
                            print(f'client addr: {self.CLIENT_ADDR}')
                            print(f'client port: {self.CLIENT_PORT}')
                            print(f'codec choice: {self.CODEC_CHOICE}')



                    case 'BYE':
                        print('TRACE --> server inside BYE')
                        # check via
                        # check cseq
                        # check max_forwards
                        # check call_id
                        if ('bye' in rec_dict['via'] and
                            int(rec_dict['cseq']) == self.cseq and
                            int(rec_dict['max_forwards']) > 0 and
                            rec_dict['call_id'].strip() == self.CALL_ID):

                            print('TRACE --> server received bye')
                            print('TRACE --> server printing bye')
                            print(rec_dict)

                            print('TRACE --> server sending ok')
                            
                            # send Ok
                            self.send_message(
                                                Ok(self.SERVER_ADDR, self.SERVER_PORT, self.CODEC_CHOICE,
                                                self.MAX_FORWARDS, self.CALL_ID, self.TO, self.FRM,
                                                self.VIA_PREFIX + 'bye', self.cseq).to_string(),
                                                (self.CLIENT_ADDR, self.CLIENT_PORT)
                                            )

                            print('TRACE --> server closing socket')

                            # exit the receive loop
                            is_receiving = False
                    
                    case _:
                        print('TRACE --> server match triggered')

            except Exception as e:
                print(f'ERROR --> {e}')

if __name__=='__main__':
    ADDRESS = '127.0.0.1'
    PORT = 60001
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = Server(sock, ADDRESS, PORT)