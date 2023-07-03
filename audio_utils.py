import pyaudiowpatch as pyaudio

def get_input_device_list():
    devices = []
    with pyaudio.PyAudio() as p:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        for host_index in range(0, p.get_host_api_count()):
            for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                if device["hostApi"] == wasapi_info["index"] and device["maxInputChannels"] > 0 and device["isLoopbackDevice"] is False:
                    devices.append(device)
    return devices

def get_output_device_list():
    devices =[]
    with pyaudio.PyAudio() as p:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        for device in p.get_loopback_device_info_generator():
            if device["hostApi"] == wasapi_info["index"] and device["isLoopbackDevice"] is True:
                devices.append(device)
    return devices

def get_default_input_device():
    with pyaudio.PyAudio() as p:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        defaultInputDevice = wasapi_info["defaultInputDevice"]

        for host_index in range(0, p.get_host_api_count()):
            for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                if device["index"] == defaultInputDevice:
                    default_device = device
                    return default_device

def get_default_output_device():
    with pyaudio.PyAudio() as p:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        defaultOutputDevice = wasapi_info["defaultOutputDevice"]

        for host_index in range(0, p.get_host_api_count()):
            for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                if device["index"] == defaultOutputDevice:
                    default_speakers = device
                    if not default_speakers["isLoopbackDevice"]:
                        for loopback in p.get_loopback_device_info_generator():
                            if default_speakers["name"] in loopback["name"]:
                                default_device = loopback
                                return default_device