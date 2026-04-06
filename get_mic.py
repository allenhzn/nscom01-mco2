import pyaudio
pa = pyaudio.PyAudio()

for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    api = pa.get_host_api_info_by_index(info['hostApi'])
    if api['type'] == pyaudio.paWASAPI and info['maxInputChannels'] > 0:
        print(f"[{i}] {info['name']} — {int(info['defaultSampleRate'])} Hz (WASAPI)")