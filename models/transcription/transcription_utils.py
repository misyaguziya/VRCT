from pyaudiowpatch import PyAudio, paWASAPI
from faster_whisper.utils import download_model
import logging
logger = logging.getLogger('faster_whisper')
logger.setLevel(logging.CRITICAL)

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
            for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                if device["index"] == defaultInputDevice:
                    return {"host": host, "device": device}
    return {"host": {"name": "NoHost"}, "device": {"name": "NoDevice"}}

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
                                default_device = loopback
                                return default_device
    return {"name":"NoDevice"}

def downloadWhisperWeight(weight_type, path):
    result = False
    try:
        download_model(
            weight_type,
            cache_dir=path)
        result = True
    except Exception:
        pass
    return result

def checkWhisperWeight(weight_type, path):
    result = False
    try:
        result = download_model(
            weight_type,
            local_files_only=True,
            cache_dir=path)
        result = True
    except Exception:
        pass
    return result

if __name__ == "__main__":


    downloadWhisperWeight("base", "./weight/whisper/")

    from faster_whisper import WhisperModel
    whisper_model = WhisperModel("base", device="cpu", device_index=0, compute_type="int8", cpu_threads=4, num_workers=1, download_root="./weight/whisper/")

    print(checkWhisperWeight("base", "./weight/whisper/"))
    print(checkWhisperWeight("tiny", "./weight/whisper/"))