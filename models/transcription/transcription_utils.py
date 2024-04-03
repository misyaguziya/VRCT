from pyaudiowpatch import PyAudio, paWASAPI

def getInputDevices():
    devices = {}
    with PyAudio() as p:
        for host_index in range(0, p.get_host_api_count()):
            host = p.get_host_api_info_by_index(host_index)
            for device_index in range(0, p.get_host_api_info_by_index(host_index)['deviceCount']):
                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                if device["maxInputChannels"] > 0 and device["isLoopbackDevice"] is False:
                    if host["name"] in devices.keys():
                        devices[host["name"]].append(device)
                    else:
                        devices[host["name"]] = [device]
    if len(devices) == 0:
        devices = {"NoHost": [{"name": "NoDevice"}]}
    return devices

def getDefaultInputDevice():
    with PyAudio() as p:
        api_info = p.get_default_host_api_info()
        defaultInputDevice = api_info["defaultInputDevice"]

        for host_index in range(0, p.get_host_api_count()):
            host = p.get_host_api_info_by_index(host_index)
            for device_index in range(0, p.get_host_api_info_by_index(host_index)['deviceCount']):
                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                if device["index"] == defaultInputDevice:
                    return {"host": host, "device": device}
    return {"host": {"name": "NoHost"}, "device": {"name": "NoDevice"}}

def getOutputDevices():
    devices = []
    with PyAudio() as p:
        wasapi_info = p.get_host_api_info_by_type(paWASAPI)
        for host_index in range(0, p.get_host_api_count()):
            host = p.get_host_api_info_by_index(host_index)
            if host["name"] == wasapi_info["name"]:
                for device_index in range(0, p.get_host_api_info_by_index(host_index)['deviceCount']):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if not device["isLoopbackDevice"]:
                        for loopback in p.get_loopback_device_info_generator():
                            if device["name"] in loopback["name"]:
                                devices.append(loopback)

        if len(devices) == 0:
            devices = [{"name": "NoDevice"}]
    return devices

def getDefaultOutputDevice():
    with PyAudio() as p:
        wasapi_info = p.get_host_api_info_by_type(paWASAPI)
        defaultOutputDevice = wasapi_info["defaultOutputDevice"]

        for host_index in range(0, p.get_host_api_count()):
            for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                if device["index"] == defaultOutputDevice:
                    default_speakers = device
                    if not default_speakers["isLoopbackDevice"]:
                        for loopback in p.get_loopback_device_info_generator():
                            if default_speakers["name"] in loopback["name"]:
                                return {"device": loopback}
    return {"device": {"name": "NoDevice"}}

if __name__ == "__main__":
    print("getOutputDevices()", getOutputDevices())
    print("getDefaultOutputDevice()", getDefaultOutputDevice())