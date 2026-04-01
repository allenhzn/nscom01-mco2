from bitstruct import calcsize

HEADER_FORMAT = "u2b1b1u4b1u7u16u32u32"
HEADER_SIZE = calcsize(HEADER_FORMAT)

print(HEADER_SIZE) # 96 bits / 12 bytes exactly the same as the RFC

"""
HEADER FORMAT: 
        
    Bitstruct is most significant byte first by default so we don't need to specify
    https://bitstruct.readthedocs.io/en/latest/#bitstruct.pack
    
    Version (V): 2 bits
        Current version of RTP. RFC 3550 uses 2, it sounds funny if we use 3 lol
    
    Padding (P): 1 bit
        If the padding bit is set, the packet contains one or more
        additional padding octets at the end which are not part of the
        payload.  The last octet of the padding contains a count of how
        many padding octets should be ignored, including itself.  Padding
        may be needed by some encryption algorithms with fixed block sizes
        or for carrying several RTP packets in a lower-layer protocol data unit.

    Extension (X): 1 bit
        If the extension bit is set, the fixed header MUST be followed by
        exactly one header extension, with a format defined in Section
        5.3.1.

    CSRC count (CC): 4 bits
        Number of CSRC identifiers that follow the fixed header.
        https://stackoverflow.com/questions/21775531/csrc-and-ssrc-in-rtp
        
    Marker (M): 1 bit
         The interpretation of the marker is defined by a profile.  It is
         intended to allow significant events such as frame boundaries to
         be marked in the packet stream.
         
    Payload Type (PT): 7 bits
        This field identifies the format of the RTP payload and determines
        its interpretation by the application.  A profile MAY specify a
        default static mapping of payload type codes to payload formats.
    
    Sequence Number: 16 bits
        The sequence number increments by one for each RTP data packet
        sent, and may be used by the receiver to detect packet loss and to
        restore packet sequence.  The initial value of the sequence number
        SHOULD be random (unpredictable) to make known-plaintext attacks
        on encryption more difficult - I guess we should do this. 
        
    Timestamp: 32 bits
        The timestamp reflects the sampling instant of the first octet in
        the RTP data packet.  The sampling instant MUST be derived from a
        clock that increments monotonically and linearly in time to allow
        synchronization and jitter calculations (see Section 6.4.1).
        https://stackoverflow.com/questions/24658525/how-to-calculate-the-rtp-timestamp-for-each-packet-in-an-audio-stream
    
    SSRC: 32 bits
        The SSRC field identifies the synchronization source.  This
        identifier SHOULD be chosen randomly, with the intent that no two
        synchronization sources within the same RTP session will have the
        same SSRC identifier.
        
    CSRC list: 0 to 15 items, 32 bits each
        The CSRC list identifies the contributing sources for the payload
        contained in this packet.
    
    IMPORTANT - Since this is a variable size it's not in the struct format string,
    the values will be read using the CSRC count value    
"""

class RtpMessage:
    pass

