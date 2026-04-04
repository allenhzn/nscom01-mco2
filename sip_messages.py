class Message:
    def __init__(self, max_forwards: int, call_id: str, 
                 to: str, frm: str, via: str, cseq: int):
        self.max_forwards = max_forwards
        self.call_id = call_id
        self.to = to
        self.frm = frm
        self.via = via
        # sequence number
        self.cseq = cseq


    def to_string(self) -> str:

        temp_dict = self.__dict__

        result = ''

        # iterate through the key value pairs and add them to the string

        for k, v in temp_dict.items():

            result += f'{k}: {v}\n'

        return result
    
    @staticmethod
    def to_dict(message: str) -> dict:
        tempDict = {}
        
        if 'sdp:' in message:
            # split at 'sdp:'
            parts = message.split('sdp:', 1)
            # place everything before the sdp inside a temporary string
            header_section = parts[0]
            # make everything after the sdp correspond to 'sdp'
            tempDict['sdp'] = parts[1].strip() 
        else:
            header_section = message

        # go through the temporary string and split them at the \n
        for line in header_section.strip().splitlines():
            if ':' in line:
                # split each line at the ':'
                key, value = line.split(':', 1)
                tempDict[key.strip()] = value.strip()
                
        return tempDict

# class that makes the invite messages
class Invite(Message):
    def __init__(self, client_addr: str, client_port: int, codec_choices: list[int],
                    max_forwards: int, call_id: str, 
                    to: str, frm: str, via: str, cseq: int):
        super().__init__(max_forwards, call_id, to, frm, via, cseq)
        self.type = 'INVITE'
        self.sdp = f'client_addr: {client_addr}\nclient_port: {client_port}\ncodec_choices: {codec_choices}'

# class that makes the ok messages
class Ok(Message):
    def __init__(self,  server_addr: str, server_port: int, codec_choice: int,
                    max_forwards: int, call_id: str, 
                    to: str, frm: str, via: str, cseq: int):
        super().__init__(max_forwards, call_id, to, frm, via, cseq)
        self.type = '200_OK'
        self.sdp = f'server_addr: {server_addr}\nserver_port: {server_port}\ncodec_choice: {codec_choice}'

# class that makes the ack messages
class Ack(Message):
    def __init__(self, max_forwards: int, call_id: str, 
                 to: str, frm: str, via: str, cseq: int):
        super().__init__(max_forwards, call_id, to, frm, via, cseq)
        self.type = 'ACK'

# class that makes the ack messages
class Sip_Ack(Message):
    def __init__(self, max_forwards: int, call_id: str, 
                 to: str, frm: str, via: str, cseq: int):
        super().__init__(max_forwards, call_id, to, frm, via, cseq)
        self.type = 'SIP_ACK'

# class that makes the bye messages
class Bye(Message):
    def __init__(self, max_forwards: int, call_id: str, 
                 to: str, frm: str, via: str, cseq: int):
        super().__init__(max_forwards, call_id, to, frm, via, cseq)
        self.type = 'BYE'

# class that makes RTCP messages
class Rtcp(Message):
    def __init__(self, packets_sent: int, packets_lost: int):
        self.type = 'RTCP'
        self.packets_sent = packets_sent
        self.packets_lost = packets_lost

# testing if methods work
if __name__=='__main__':

    inv = Invite('0.0.0.0', 22, ['uhhe', 'dnjdb'], 1,
                 'called@lmao', 'bob', 'alice',
                 'via something', 5).to_string()
    
    print(inv)

    inv_dict = Message.to_dict(inv)

    print(inv_dict)
    """inv = Invite('0.0.0.0', 60000, ['something', 'another thing']).to_string()
    ok = Ok('0.0.0.0', 60001, 'something').to_string()
    ack = Ack().to_string()

    inv_dict = Message.to_dict(inv)
    ok_dict = Message.to_dict(ok)
    ack_dict = Message.to_dict(ack)

    client_sdp = Message.to_dict(inv_dict['sdp'])
    server_sdp = Message.to_dict(ok_dict['sdp'])

    print(f'{client_sdp['client_addr']} | {client_sdp['client_port']} | {client_sdp['codec_choices']}')
    print(f'{server_sdp['server_addr']} | {server_sdp['server_port']} | {server_sdp['codec_choice']}')"""