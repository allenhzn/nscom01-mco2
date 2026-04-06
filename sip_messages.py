from sdp import create_sdp

class Message:
    # Parent SIP message class

    @staticmethod
    def to_dict(message: str) -> dict:
        result = {}

        # split headers from body at the blank line
        if "\r\n\r\n" in message:
            header_section, body = message.split("\r\n\r\n", 1)
        elif "\n\n" in message:
            header_section, body = message.split("\n\n", 1)
        else:
            header_section = message
            body = ""

        lines = header_section.strip().splitlines()
        if not lines:
            return result

        first = lines[0].strip()
        if first.startswith("SIP/2.0"):
            # status-line: SIP/2.0 200 OK
            parts = first.split(None, 2)
            result["status_code"] = int(parts[1])
            result["reason"] = parts[2] if len(parts) > 2 else ""
        else:
            # request-line: INVITE sip:bob@domain.com SIP/2.0
            parts = first.split(None, 2)
            result["method"] = parts[0]

        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()

        body = body.strip()
        if body:
            result["sdp"] = body

        return result


class Sip_Request(Message):
    def __init__(
        self,
        method: str,
        request_uri: str,
        max_forwards: int,
        call_id: str,
        to: str,
        frm: str,
        via: str,
        cseq: int,
        sdp_body: str = "",
    ):
        self.method = method
        self.request_uri = request_uri
        self.max_forwards = max_forwards
        self.call_id = call_id
        self.to = to
        self.frm = frm
        self.via = via
        self.cseq = cseq
        self.sdp_body = sdp_body

    def to_string(self) -> str:
        lines = [
            f"{self.method} {self.request_uri} SIP/2.0",
            f"Via: {self.via}",
            f"Max-Forwards: {self.max_forwards}",
            f"To: <{self.to}>",
            f"From: <{self.frm}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} {self.method}",
        ]

        if self.sdp_body:
            lines.append("Content-Type: application/sdp")
            lines.append(f"Content-Length: {len(self.sdp_body.encode())}")
            lines.append("")  # blank line before body
            lines.append(self.sdp_body)
        else:
            lines.append("Content-Length: 0")
            lines.append("")  # blank line (end of headers)

        return "\r\n".join(lines)


class Invite(Sip_Request):
    def __init__(
        self,
        client_addr: str,
        rtp_port: int,
        codec_choices: list[int],
        max_forwards: int,
        call_id: str,
        to: str,
        frm: str,
        via: str,
        cseq: int,
    ):
        sdp = create_sdp(client_addr, rtp_port, codec_choices)
        super().__init__("INVITE", to, max_forwards, call_id, to, frm, via, cseq, sdp)


class Ack(Sip_Request):
    def __init__(
        self, max_forwards: int, call_id: str, to: str, frm: str, via: str, cseq: int
    ):
        super().__init__("ACK", to, max_forwards, call_id, to, frm, via, cseq)


class Bye(Sip_Request):
    def __init__(
        self, max_forwards: int, call_id: str, to: str, frm: str, via: str, cseq: int
    ):
        super().__init__("BYE", to, max_forwards, call_id, to, frm, via, cseq)


class Sip_Response(Message):
    def __init__(
        self,
        status_code: int,
        reason: str,
        max_forwards: int,
        call_id: str,
        to: str,
        frm: str,
        via: str,
        cseq: int,
        cseq_method: str = "INVITE",
        sdp_body: str = "",
    ):
        self.status_code = status_code
        self.reason = reason
        self.max_forwards = max_forwards
        self.call_id = call_id
        self.to = to
        self.frm = frm
        self.via = via
        self.cseq = cseq
        self.cseq_method = cseq_method
        self.sdp_body = sdp_body

    def to_string(self) -> str:
        lines = [
            f"SIP/2.0 {self.status_code} {self.reason}",
            f"Via: {self.via}",
            f"Max-Forwards: {self.max_forwards}",
            f"To: <{self.to}>",
            f"From: <{self.frm}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} {self.cseq_method}",
        ]

        if self.sdp_body:
            lines.append("Content-Type: application/sdp")
            lines.append(f"Content-Length: {len(self.sdp_body.encode())}")
            lines.append("")
            lines.append(self.sdp_body)
        else:
            lines.append("Content-Length: 0")
            lines.append("")

        return "\r\n".join(lines)


class Ok(Sip_Response):
    def __init__(
        self,
        server_addr: str,
        rtp_port: int,
        codec_choice: int,
        max_forwards: int,
        call_id: str,
        to: str,
        frm: str,
        via: str,
        cseq: int,
        cseq_method: str = "INVITE",
    ):
        sdp = create_sdp(server_addr, rtp_port, [codec_choice])
        super().__init__(
            200, "OK", max_forwards, call_id, to, frm, via, cseq, cseq_method, sdp
        )


class Rtcp(Message):
    def __init__(self, packets_sent: int, packets_received: int):
        self.type = "RTCP"
        self.packets_sent = packets_sent
        self.packets_received = packets_received

    def to_string(self) -> str:
        lines = [
            f"type: {self.type}",
            f"packets_sent: {self.packets_sent}",
            f"packets_received: {self.packets_received}",
        ]
        return "\n".join(lines)


# testing if methods work
if __name__ == "__main__":
    inv = Invite(
        "127.0.0.1",
        5004,
        [0, 8],
        70,
        "bgtrts@127.0.0.1",
        "sip:bob@domain.com",
        "sip:alice@hereway.com",
        "SIP/2.0/UDP 127.0.0.1:60000;branch=z9hG4bKinvite",
        1,
    ).to_string()

    print("=== INVITE ===")
    print(inv)
    print()

    inv_dict = Message.to_dict(inv)
    print("=== Parsed ===")
    print(inv_dict)
    print()

    ok = Ok(
        "127.0.0.1",
        5004,
        0,
        70,
        "bgtrts@127.0.0.1",
        "sip:bob@domain.com",
        "sip:alice@hereway.com",
        "SIP/2.0/UDP 127.0.0.1:60001;branch=z9hG4bKinvite",
        1,
    ).to_string()

    print("=== 200 OK ===")
    print(ok)
    print()

    ok_dict = Message.to_dict(ok)
    print("=== Parsed ===")
    print(ok_dict)
