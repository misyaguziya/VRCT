from typing import Callable
from time import sleep
from threading import Thread
import comtypes
from pyaudiowpatch import PyAudio, paWASAPI
from pycaw.callbacks import MMNotificationClient
from pycaw.utils import AudioUtilities
from utils import errorLogging

class Client(MMNotificationClient):
    def __init__(self):
        super().__init__()
        self.loop = True

    def on_default_device_changed(self, flow, flow_id, role, role_id, default_device_id):
        self.loop = False

    def on_device_added(self, added_device_id):
        self.loop = False

    def on_device_removed(self, removed_device_id):
        self.loop = False

    def on_device_state_changed(self, device_id, state):
        self.loop = False

    # def on_property_value_changed(self, device_id, key):
    #     self.loop = False

class DeviceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeviceManager, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.mic_devices = {"NoHost": [{"index": -1, "name": "NoDevice"}]}
        self.default_mic_device = {"host": {"index": -1, "name": "NoHost"}, "device": {"index": -1, "name": "NoDevice"}}
        self.speaker_devices = [{"index": -1, "name": "NoDevice"}]
        self.default_speaker_device = {"device": {"index": -1, "name": "NoDevice"}}

        self.update()

        self.prev_mic_host = [host for host in self.mic_devices]
        self.prev_mic_devices = self.mic_devices
        self.prev_default_mic_device = self.default_mic_device
        self.prev_speaker_devices = self.speaker_devices
        self.prev_default_speaker_device = self.default_speaker_device

        self.update_flag_default_mic_device = False
        self.update_flag_default_speaker_device = False
        self.update_flag_host_list = False
        self.update_flag_mic_device_list = False
        self.update_flag_speaker_device_list = False

        self.callback_default_mic_device = None
        self.callback_default_speaker_device = None
        self.callback_host_list = None
        self.callback_mic_device_list = None
        self.callback_speaker_device_list = None
        self.callback_process_before_update_devices = None
        self.callback_process_after_update_devices = None

        self.monitoring_flag = False
        self.startMonitoring()

    def update(self):
        buffer_mic_devices = {}
        buffer_default_mic_device = {"host": {"index": -1, "name": "NoHost"}, "device": {"index": -1, "name": "NoDevice"}}
        buffer_speaker_devices = []
        buffer_default_speaker_device = {"device": {"index": -1, "name": "NoDevice"}}

        with PyAudio() as p:
            for host_index in range(p.get_host_api_count()):
                host = p.get_host_api_info_by_index(host_index)
                device_count = host.get('deviceCount', 0)
                for device_index in range(device_count):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device.get("maxInputChannels", 0) > 0 and not device.get("isLoopbackDevice", True):
                        buffer_mic_devices.setdefault(host["name"], []).append(device)
            if not buffer_mic_devices:
                buffer_mic_devices = {"NoHost": [{"index": -1, "name": "NoDevice"}]}

            api_info = p.get_default_host_api_info()
            default_mic_device = api_info["defaultInputDevice"]

            for host_index in range(p.get_host_api_count()):
                host = p.get_host_api_info_by_index(host_index)
                device_count = host.get('deviceCount', 0)
                for device_index in range(device_count):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["index"] == default_mic_device:
                        buffer_default_mic_device = {"host": host, "device": device}
                        break
                else:
                    continue
                break

            speaker_devices = []
            wasapi_info = p.get_host_api_info_by_type(paWASAPI)
            wasapi_name = wasapi_info["name"]
            for host_index in range(p.get_host_api_count()):
                host = p.get_host_api_info_by_index(host_index)
                if host["name"] == wasapi_name:
                    device_count = host.get('deviceCount', 0)
                    for device_index in range(device_count):
                        device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                        if not device.get("isLoopbackDevice", True):
                            for loopback in p.get_loopback_device_info_generator():
                                if device["name"] in loopback["name"]:
                                    speaker_devices.append(loopback)
            speaker_devices = [dict(t) for t in {tuple(d.items()) for d in speaker_devices}] or [{"index": -1, "name": "NoDevice"}]
            buffer_speaker_devices = sorted(speaker_devices, key=lambda d: d['index'])

            wasapi_info = p.get_host_api_info_by_type(paWASAPI)
            default_speaker_device_index = wasapi_info["defaultOutputDevice"]

            for host_index in range(p.get_host_api_count()):
                host_info = p.get_host_api_info_by_index(host_index)
                device_count = host_info.get('deviceCount', 0)
                for device_index in range(0, device_count):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["index"] == default_speaker_device_index:
                        default_speakers = device
                        if not default_speakers.get("isLoopbackDevice", True):
                            for loopback in p.get_loopback_device_info_generator():
                                if default_speakers["name"] in loopback["name"]:
                                    buffer_default_speaker_device = {"device": loopback}
                                    break
                        break

                if buffer_default_speaker_device["device"]["name"] != "NoDevice":
                    break

        self.mic_devices = buffer_mic_devices
        self.default_mic_device = buffer_default_mic_device
        self.speaker_devices = buffer_speaker_devices
        self.default_speaker_device = buffer_default_speaker_device

    def checkUpdate(self):
        if self.prev_default_mic_device["device"]["name"] != self.default_mic_device["device"]["name"]:
            self.update_flag_default_mic_device = True
            self.prev_default_mic_device = self.default_mic_device
        if self.prev_default_speaker_device["device"]["name"] != self.default_speaker_device["device"]["name"]:
            self.update_flag_default_speaker_device = True
            self.prev_default_speaker_device = self.default_speaker_device
        if self.prev_mic_host != [host for host in self.mic_devices]:
            self.update_flag_host_list = True
            self.prev_mic_host = [host for host in self.mic_devices]
        if {key: [device['name'] for device in devices] for key, devices in self.prev_mic_devices.items()} != {key: [device['name'] for device in devices] for key, devices in self.mic_devices.items()}:
            self.update_flag_mic_device_list = True
            self.prev_mic_devices = self.mic_devices
        if [device['name'] for device in self.prev_speaker_devices] != [device['name'] for device in self.speaker_devices]:
            self.update_flag_speaker_device_list = True
            self.prev_speaker_devices = self.speaker_devices

        update_flag = (
            self.update_flag_default_mic_device or
            self.update_flag_default_speaker_device or
            self.update_flag_host_list or
            self.update_flag_mic_device_list or
            self.update_flag_speaker_device_list
        )
        return update_flag

    def monitoring(self):
        try:
            while self.monitoring_flag is True:
                try:
                    comtypes.CoInitialize()
                    cb = Client()
                    enumerator = AudioUtilities.GetDeviceEnumerator()
                    enumerator.RegisterEndpointNotificationCallback(cb)
                    while cb.loop is True:
                        sleep(1)
                    enumerator.UnregisterEndpointNotificationCallback(cb)
                    comtypes.CoUninitialize()
                    self.runProcessBeforeUpdateDevices()
                    sleep(2)
                    for _ in range(10):
                        self.update()
                        if self.checkUpdate():
                            break
                        sleep(2)
                    self.noticeUpdateDevices()
                    self.runProcessAfterUpdateDevices()
                except Exception:
                    errorLogging()
                finally:
                    pass
        except Exception:
            errorLogging()

    def startMonitoring(self):
        self.monitoring_flag = True
        self.th_monitoring = Thread(target=self.monitoring)
        self.th_monitoring.daemon = True
        self.th_monitoring.start()

    def stopMonitoring(self):
        self.monitoring_flag = False
        self.th_monitoring.join()

    def setCallbackDefaultMicDevice(self, callback):
        self.callback_default_mic_device = callback

    def clearCallbackDefaultMicDevice(self):
        self.callback_default_mic_device = None

    def setCallbackDefaultSpeakerDevice(self, callback):
        self.callback_default_speaker_device = callback

    def clearCallbackDefaultSpeakerDevice(self):
        self.callback_default_speaker_device = None

    def setCallbackHostList(self, callback):
        self.callback_host_list = callback

    def clearCallbackHostList(self):
        self.callback_host_list = None

    def setCallbackMicDeviceList(self, callback):
        self.callback_mic_device_list = callback

    def clearCallbackMicDeviceList(self):
        self.callback_mic_device_list = None

    def setCallbackSpeakerDeviceList(self, callback):
        self.callback_speaker_device_list = callback

    def clearCallbackSpeakerDeviceList(self):
        self.callback_speaker_device_list = None

    def setCallbackProcessBeforeUpdateDevices(self, callback):
        self.callback_process_before_update_devices = callback

    def clearCallbackProcessBeforeUpdateDevices(self):
        self.callback_process_before_update_devices = None

    def runProcessBeforeUpdateDevices(self):
        if isinstance(self.callback_process_before_update_devices, Callable):
            self.callback_process_before_update_devices()

    def setCallbackProcessAfterUpdateDevices(self, callback):
        self.callback_process_after_update_devices = callback

    def clearCallbackProcessAfterUpdateDevices(self):
        self.callback_process_after_update_devices = None

    def runProcessAfterUpdateDevices(self):
        if isinstance(self.callback_process_after_update_devices, Callable):
            self.callback_process_after_update_devices()

    def noticeUpdateDevices(self):
        if self.update_flag_default_mic_device is True:
            self.setMicDefaultDevice()
        if self.update_flag_default_speaker_device is True:
            self.setSpeakerDefaultDevice()
        if self.update_flag_host_list is True:
            self.setMicHostList()
        if self.update_flag_mic_device_list is True:
            self.setMicDeviceList()
        if self.update_flag_speaker_device_list is True:
            self.setSpeakerDeviceList()

        self.update_flag_default_mic_device = False
        self.update_flag_default_speaker_device = False
        self.update_flag_host_list = False
        self.update_flag_mic_device_list = False
        self.update_flag_speaker_device_list = False

    def setMicDefaultDevice(self):
        if isinstance(self.callback_default_mic_device, Callable):
            self.callback_default_mic_device(self.default_mic_device["host"]["name"], self.default_mic_device["device"]["name"])

    def setSpeakerDefaultDevice(self):
        if isinstance(self.callback_default_speaker_device, Callable):
            self.callback_default_speaker_device(self.default_speaker_device["device"]["name"])

    def setMicHostList(self):
        if isinstance(self.callback_host_list, Callable):
            self.callback_host_list()

    def setMicDeviceList(self):
        if isinstance(self.callback_mic_device_list, Callable):
            self.callback_mic_device_list()

    def setSpeakerDeviceList(self):
        if isinstance(self.callback_speaker_device_list, Callable):
            self.callback_speaker_device_list()

    def getMicDevices(self):
        return self.mic_devices

    def getDefaultMicDevice(self):
        return self.default_mic_device

    def getSpeakerDevices(self):
        return self.speaker_devices

    def getDefaultSpeakerDevice(self):
        return self.default_speaker_device

    def forceUpdateAndSetMicDevices(self):
        self.update()
        self.setMicHostList()
        self.setMicDeviceList()
        self.setMicDefaultDevice()

    def forceUpdateAndSetSpeakerDevices(self):
        self.update()
        self.setSpeakerDeviceList()
        self.setSpeakerDefaultDevice()

device_manager = DeviceManager()

if __name__ == "__main__":
    # print("getMicDevices()", device_manager.getMicDevices())
    # print("getDefaultMicDevice()", device_manager.getDefaultMicDevice())
    # print("getSpeakerDevices()", device_manager.getSpeakerDevices())
    # print("getDefaultSpeakerDevice()", device_manager.getDefaultSpeakerDevice())

    while True:
        sleep(1)