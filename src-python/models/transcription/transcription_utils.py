from time import sleep
from threading import Thread
from pyaudiowpatch import PyAudio, paWASAPI

class DeviceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeviceManager, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.input_devices = {"NoHost": [{"name": "NoDevice"}]}
        self.default_input_device = {"host": {"name": "NoHost"}, "device": {"name": "NoDevice"}}
        self.output_devices = [{"name": "NoDevice"}]
        self.default_output_device = {"device": {"name": "NoDevice"}}
        self.update()

        self.monitoring_flag = True
        self.th_monitoring = Thread(target=self.startMonitoring)
        self.th_monitoring.daemon = True
        self.th_monitoring.start()

    def update(self):
        buffer_input_devices = {}
        buffer_default_input_device = {"host": {"name": "NoHost"}, "device": {"name": "NoDevice"}}
        buffer_output_devices = []
        buffer_default_output_device = {"device": {"name": "NoDevice"}}

        with PyAudio() as p:
            for host_index in range(p.get_host_api_count()):
                host = p.get_host_api_info_by_index(host_index)
                device_count = host.get('deviceCount', 0)
                for device_index in range(device_count):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device.get("maxInputChannels", 0) > 0 and not device.get("isLoopbackDevice", True):
                        buffer_input_devices.setdefault(host["name"], []).append(device)
            if not buffer_input_devices:
                buffer_input_devices = {"NoHost": [{"name": "NoDevice"}]}

            api_info = p.get_default_host_api_info()
            default_input_device = api_info["defaultInputDevice"]

            for host_index in range(p.get_host_api_count()):
                host = p.get_host_api_info_by_index(host_index)
                device_count = host.get('deviceCount', 0)
                for device_index in range(device_count):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["index"] == default_input_device:
                        buffer_default_input_device = {"host": host, "device": device}
                        break
                else:
                    continue
                break

            output_devices = []
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
                                    output_devices.append(loopback)
            output_devices = [dict(t) for t in {tuple(d.items()) for d in output_devices}] or [{"name": "NoDevice"}]
            buffer_output_devices = sorted(output_devices, key=lambda d: d['index'])

            wasapi_info = p.get_host_api_info_by_type(paWASAPI)
            default_output_device_index = wasapi_info["defaultOutputDevice"]

            for host_index in range(p.get_host_api_count()):
                host_info = p.get_host_api_info_by_index(host_index)
                device_count = host_info.get('deviceCount', 0)
                for device_index in range(0, device_count):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["index"] == default_output_device_index:
                        default_speakers = device
                        if not default_speakers.get("isLoopbackDevice", True):
                            for loopback in p.get_loopback_device_info_generator():
                                if default_speakers["name"] in loopback["name"]:
                                    buffer_default_output_device = {"device": loopback}
                                    break
                        break

                if buffer_default_output_device["device"]["name"] != "NoDevice":
                    break

        self.input_devices = buffer_input_devices
        self.default_input_device = buffer_default_input_device
        self.output_devices = buffer_output_devices
        self.default_output_device = buffer_default_output_device

    def startMonitoring(self):
        self.monitoring_flag = True
        while self.monitoring_flag is True:
            self.update()
            sleep(1)

    def stopMonitoring(self):
        self.monitoring_flag = False
        self.th_monitoring.join()

    def getInputDevices(self):
        return self.input_devices

    def getDefaultInputDevice(self):
        return self.default_input_device

    def getOutputDevices(self):
        return self.output_devices

    def getDefaultOutputDevice(self):
        return self.default_output_device

device_manager = DeviceManager()

if __name__ == "__main__":
    print("getInputDevices()", device_manager.getInputDevices())
    print("getDefaultInputDevice()", device_manager.getDefaultInputDevice())
    print("getOutputDevices()", device_manager.getOutputDevices())
    print("getDefaultOutputDevice()", device_manager.getDefaultOutputDevice())