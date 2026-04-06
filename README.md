# NSCOM01 MCO2 - Real-Time Audio Streaming over IP

Utilizes the Session Initiation Protocol (RFC 3261) and the Real-time Transport Protocol (RFC 3550) to broadcast and 
play audio in real-time. Implemented using UDP and PyAudio.

## Instructions for Running
- Install [uv](https://docs.astral.sh/uv/)
- Clone repository 
- Navigate to folder
- `uv run client1.py [-h] {file,mic} ...`

- `uv run client2.py [-h] {file} ...`
- Use `uv run [client1.py/client2.py] [file/mic] -h` for more detailed instructions

## Features
- Complete SIP Handshake with SDP Negotiation
- Support for 4 different audio codecs, with automatic .wav file encoding/decoding
- RTP Packetization and Real-time Audio Playback
- RTCP Diagnostics for both sender and receiver
- Graceful teardown once audio file completes sending
- Bonus: Real-time microphone capture and playback (1-way)