from threading import Thread
from time import sleep
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

import comtypes
from pycaw.callbacks import MMNotificationClient
from pycaw.utils import AudioUtilities
from pyaudiowpatch import PyAudio, paWASAPI # Assuming PyAudio is part of pyaudiowpatch for grouping

from utils import errorLogging

T = TypeVar('T')

class Client(MMNotificationClient):
    """Handles audio device change notifications from the Windows Core Audio APIs."""
    loop: bool

    def __init__(self) -> None:
        """Initializes the MMNotificationClient and sets the loop flag."""
        super().__init__()
        self.loop = True

    def on_default_device_changed(self, flow: int, flow_id: Any, role: int, role_id: Any, default_device_id: Optional[str]) -> None:
        """Callback for default device change event. Sets the internal loop flag to False to signal a change."""
        self.loop = False

    def on_device_added(self, added_device_id: Optional[str]) -> None:
        """Callback for device added event. Sets the internal loop flag to False to signal a change."""
        self.loop = False

    def on_device_removed(self, removed_device_id: Optional[str]) -> None:
        """Callback for device removed event. Sets the internal loop flag to False to signal a change."""
        self.loop = False

    def on_device_state_changed(self, device_id: Optional[str], state: int) -> None:
        """Callback for device state change event. Sets the internal loop flag to False to signal a change."""
        self.loop = False

    # def on_property_value_changed(self, device_id: Optional[str], key: Any) -> None:
    #     """Callback for device property value change event. Sets the internal loop flag to False to signal a change."""
    #     self.loop = False

class DeviceManager:
    _instance: Optional['DeviceManager'] # Forward declaration for DeviceManager

    # Device Info Structures (approximated, PyAudio returns dicts)
    # Example: {"index": 0, "name": "DeviceName", "maxInputChannels": 2, ...}
    DeviceInfo = Dict[str, Any]
    HostInfo = Dict[str, Any]

    mic_devices: Dict[str, List[DeviceInfo]]
    default_mic_device: Dict[str, HostInfo | DeviceInfo] # {"host": HostInfo, "device": DeviceInfo}
    speaker_devices: List[DeviceInfo]
    default_speaker_device: Dict[str, DeviceInfo] # {"device": DeviceInfo}

    prev_mic_host: List[str]
    prev_mic_devices: Dict[str, List[DeviceInfo]]
    prev_default_mic_device: Dict[str, HostInfo | DeviceInfo]
    prev_speaker_devices: List[DeviceInfo]
    prev_default_speaker_device: Dict[str, DeviceInfo]

    update_flag_default_mic_device: bool
    update_flag_default_speaker_device: bool
    update_flag_host_list: bool
    update_flag_mic_device_list: bool
    update_flag_speaker_device_list: bool

    callback_default_mic_device: Optional[Callable[[str, str], None]]
    callback_default_speaker_device: Optional[Callable[[str], None]]
    callback_host_list: Optional[Callable[[], None]]
    callback_mic_device_list: Optional[Callable[[], None]]
    callback_speaker_device_list: Optional[Callable[[], None]]
    callback_process_before_update_devices: Optional[Callable[[], None]]
    callback_process_after_update_devices: Optional[Callable[[], None]]

    monitoring_flag: bool
    th_monitoring: Optional[Thread]


    def __new__(cls: Type['DeviceManager']) -> 'DeviceManager':
        """Ensures singleton instance of DeviceManager."""
        if cls._instance is None:
            cls._instance = super(DeviceManager, cls).__new__(cls)
            # Note: init() is called here in the original code IF _instance is None.
            # This means it's called only on the first creation of the instance.
            cls._instance.init()
        return cls._instance

    def init(self) -> None:
        """Initializes device lists, state flags, callbacks, and starts device monitoring."""
        self.mic_devices: Dict[str, List[DeviceManager.DeviceInfo]] = {"NoHost": [{"index": -1, "name": "NoDevice", "maxInputChannels": 0}]} # Added placeholder for maxInputChannels
        self.default_mic_device: Dict[str, DeviceManager.HostInfo | DeviceManager.DeviceInfo] = {
            "host": {"index": -1, "name": "NoHost"}, # Simplified HostInfo
            "device": {"index": -1, "name": "NoDevice"}
        }
        self.speaker_devices: List[DeviceManager.DeviceInfo] = [{"index": -1, "name": "NoDevice"}]
        self.default_speaker_device: Dict[str, DeviceManager.DeviceInfo] = {"device": {"index": -1, "name": "NoDevice"}}

        self.update()

        self.prev_mic_host: List[str] = [host for host in self.mic_devices.keys()] # Use .keys()
        self.prev_mic_devices: Dict[str, List[DeviceManager.DeviceInfo]] = self.mic_devices.copy() # Use .copy()
        self.prev_default_mic_device: Dict[str, DeviceManager.HostInfo | DeviceManager.DeviceInfo] = self.default_mic_device.copy()
        self.prev_speaker_devices: List[DeviceManager.DeviceInfo] = self.speaker_devices.copy()
        self.prev_default_speaker_device: Dict[str, DeviceManager.DeviceInfo] = self.default_speaker_device.copy()

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
        self.th_monitoring = None # Initialize th_monitoring here
        self.startMonitoring()

    def update(self) -> None:
        """Scans and updates the lists of available audio devices using PyAudio."""
        # Initialize with default "NoDevice" structures to ensure attributes are always populated
        buffer_mic_devices: Dict[str, List[DeviceManager.DeviceInfo]] = \
            {"NoHost": [{"index": -1, "name": "NoDevice", "maxInputChannels": 0}]}
        buffer_default_mic_device: Dict[str, DeviceManager.HostInfo | DeviceManager.DeviceInfo] = { # type: ignore
            "host": {"index": -1, "name": "NoHost"},
            "device": {"index": -1, "name": "NoDevice", "maxInputChannels": 0}
        }
        buffer_speaker_devices: List[DeviceManager.DeviceInfo] = [{"index": -1, "name": "NoDevice"}]
        buffer_default_speaker_device: Dict[str, DeviceManager.DeviceInfo] = \
            {"device": {"index": -1, "name": "NoDevice"}}

        try:
            with PyAudio() as p:
                # Microphone devices
                temp_mic_devices: Dict[str, List[DeviceManager.DeviceInfo]] = {}
                for host_index in range(p.get_host_api_count()):
                    host_info = p.get_host_api_info_by_index(host_index)
                    device_count = host_info.get('deviceCount', 0)
                    for device_index in range(device_count):
                        device_info = p.get_device_info_by_host_api_device_index(host_index, device_index)
                        if device_info.get("maxInputChannels", 0) > 0 and not device_info.get("isLoopbackDevice", True):
                            temp_mic_devices.setdefault(host_info["name"], []).append(device_info)
                if temp_mic_devices: # Only overwrite if we found actual devices
                    buffer_mic_devices = temp_mic_devices

                # Default microphone device
                default_host_api_info = p.get_default_host_api_info()
                default_mic_device_index = default_host_api_info["defaultInputDevice"]
                # Search for the default device across all hosts
                found_default_mic = False
                for host_index in range(p.get_host_api_count()):
                    host_info = p.get_host_api_info_by_index(host_index)
                    device_count = host_info.get('deviceCount', 0)
                    for device_index in range(device_count):
                        device_info = p.get_device_info_by_host_api_device_index(host_index, device_index)
                        if device_info["index"] == default_mic_device_index:
                            buffer_default_mic_device = {"host": host_info, "device": device_info}
                            found_default_mic = True
                            break
                    if found_default_mic:
                        break
                
                # Speaker devices (WASAPI loopback)
                temp_speaker_devices: List[DeviceManager.DeviceInfo] = []
                wasapi_info = p.get_host_api_info_by_type(paWASAPI) # Can raise an error if no WASAPI
                if wasapi_info:
                    wasapi_host_name = wasapi_info["name"]
                    for host_index in range(p.get_host_api_count()):
                        host_info = p.get_host_api_info_by_index(host_index)
                        if host_info["name"] == wasapi_host_name:
                            device_count = host_info.get('deviceCount', 0)
                            for device_index in range(device_count):
                                device_info = p.get_device_info_by_host_api_device_index(host_index, device_index)
                                # Check if it's an output device that is not a loopback capture device itself
                                if device_info.get("maxOutputChannels", 0) > 0 and not device_info.get("isLoopbackDevice", False):
                                    # Try to find its corresponding loopback capture device
                                    for loopback_device in p.get_loopback_device_info_generator():
                                        if device_info["name"] in loopback_device["name"]: # Heuristic match
                                            temp_speaker_devices.append(loopback_device)
                                            break # Found corresponding loopback
                # Remove duplicates and sort, assign only if actual devices found
                if temp_speaker_devices:
                    unique_speaker_devices = [dict(t) for t in {tuple(d.items()) for d in temp_speaker_devices}]
                    buffer_speaker_devices = sorted(unique_speaker_devices, key=lambda d: d.get('index', -1))

                # Default speaker device (WASAPI loopback)
                if wasapi_info:
                    default_speaker_render_device_index = wasapi_info["defaultOutputDevice"]
                    found_default_speaker_loopback = False
                    for host_index in range(p.get_host_api_count()): # Search again for the render device
                        host_info = p.get_host_api_info_by_index(host_index)
                        device_count = host_info.get('deviceCount', 0)
                        for device_index in range(device_count):
                            device_info = p.get_device_info_by_host_api_device_index(host_index, device_index)
                            if device_info["index"] == default_speaker_render_device_index:
                                # Now find its loopback
                                if not device_info.get("isLoopbackDevice", False):
                                    for loopback in p.get_loopback_device_info_generator():
                                        if device_info["name"] in loopback["name"]:
                                            buffer_default_speaker_device = {"device": loopback}
                                            found_default_speaker_loopback = True
                                            break
                                if found_default_speaker_loopback: break
                        if found_default_speaker_loopback: break
        except Exception as e:
            errorLogging(f"Error updating audio devices: {e}")
            # Keep existing buffer_... defaults if PyAudio errors out

        self.mic_devices = buffer_mic_devices
        self.default_mic_device = buffer_default_mic_device
        self.speaker_devices = buffer_speaker_devices
        self.default_speaker_device = buffer_default_speaker_device

    def checkUpdate(self) -> bool:
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

    def monitoring(self) -> None:
        """
        Runs in a separate thread to monitor system audio device changes.
        Uses MMNotificationClient for Windows Core Audio notifications.
        Triggers device list updates and callbacks on detected changes.
        """
        try:
            comtypes.CoInitialize() # Initialize COM library for this thread
            client_callback = Client()
            device_enumerator = AudioUtilities.GetDeviceEnumerator()
            if device_enumerator: # Ensure enumerator was obtained
                device_enumerator.RegisterEndpointNotificationCallback(client_callback)

                while self.monitoring_flag:
                    if not client_callback.loop: # loop becomes False when a notification arrives
                        print("Device change detected by MMNotificationClient.")
                        self.runProcessBeforeUpdateDevices()
                        # Wait a bit for changes to settle, then try to update
                        sleep(2) # Initial sleep
                        updated_successfully = False
                        for attempt in range(10): # Try up to 10 times
                            self.update() # Refresh device lists
                            if self.checkUpdate(): # Check if the update captured the change
                                updated_successfully = True
                                break
                            print(f"Device update attempt {attempt + 1} did not reflect change, retrying...")
                            sleep(2) # Wait before retrying
                        
                        if updated_successfully:
                            self.noticeUpdateDevices()
                        else:
                            print("Failed to confirm device update after multiple attempts.")
                        
                        self.runProcessAfterUpdateDevices()
                        client_callback.loop = True # Reset loop for next notification
                    sleep(0.5) # Check loop status periodically

                if device_enumerator:
                    device_enumerator.UnregisterEndpointNotificationCallback(client_callback)
            else:
                errorLogging("Could not get device enumerator for monitoring.")
        except Exception as e:
            errorLogging(f"Exception in device monitoring thread: {e}")
        finally:
            comtypes.CoUninitialize() # Uninitialize COM library for this thread

    def startMonitoring(self) -> None:
        """Starts the background thread for device monitoring if not already running."""
        if not self.monitoring_flag or self.th_monitoring is None or not self.th_monitoring.is_alive():
            self.monitoring_flag = True
            self.th_monitoring = Thread(target=self.monitoring)
            self.th_monitoring.daemon = True
            self.th_monitoring.start()

    def stopMonitoring(self) -> None:
        """Stops the device monitoring thread and waits for it to join."""
        if self.monitoring_flag and self.th_monitoring is not None and self.th_monitoring.is_alive():
            self.monitoring_flag = False
            self.th_monitoring.join(timeout=5.0) # Add timeout to prevent indefinite blocking
            if self.th_monitoring.is_alive():
                errorLogging("Device monitoring thread did not terminate in time.")
        self.th_monitoring = None


    def setCallbackDefaultMicDevice(self, callback: Callable[[str, str], None]) -> None:
        """Sets the callback for default mic device changes."""
        self.callback_default_mic_device = callback

    def clearCallbackDefaultMicDevice(self) -> None:
        """Clears the callback for default mic device changes."""
        self.callback_default_mic_device = None

    def setCallbackDefaultSpeakerDevice(self, callback: Callable[[str], None]) -> None:
        """Sets the callback for default speaker device changes."""
        self.callback_default_speaker_device = callback

    def clearCallbackDefaultSpeakerDevice(self) -> None:
        """Clears the callback for default speaker device changes."""
        self.callback_default_speaker_device = None

    def setCallbackHostList(self, callback: Callable[[], None]) -> None:
        """Sets the callback for mic host list changes."""
        self.callback_host_list = callback

    def clearCallbackHostList(self) -> None:
        """Clears the callback for mic host list changes."""
        self.callback_host_list = None

    def setCallbackMicDeviceList(self, callback: Callable[[], None]) -> None:
        """Sets the callback for mic device list changes."""
        self.callback_mic_device_list = callback

    def clearCallbackMicDeviceList(self) -> None:
        """Clears the callback for mic device list changes."""
        self.callback_mic_device_list = None

    def setCallbackSpeakerDeviceList(self, callback: Callable[[], None]) -> None:
        """Sets the callback for speaker device list changes."""
        self.callback_speaker_device_list = callback

    def clearCallbackSpeakerDeviceList(self) -> None:
        """Clears the callback for speaker device list changes."""
        self.callback_speaker_device_list = None

    def setCallbackProcessBeforeUpdateDevices(self, callback: Callable[[], None]) -> None:
        """Sets a callback to run before device lists are updated."""
        self.callback_process_before_update_devices = callback

    def clearCallbackProcessBeforeUpdateDevices(self) -> None:
        """Clears the callback that runs before device lists are updated."""
        self.callback_process_before_update_devices = None

    def runProcessBeforeUpdateDevices(self) -> None:
        """Executes the registered callback before device lists are updated."""
        if isinstance(self.callback_process_before_update_devices, Callable):
            try:
                self.callback_process_before_update_devices()
            except Exception as e:
                errorLogging(f"Error in runProcessBeforeUpdateDevices callback: {e}")


    def setCallbackProcessAfterUpdateDevices(self, callback: Callable[[], None]) -> None:
        """Sets a callback to run after device lists are updated and changes are noticed."""
        self.callback_process_after_update_devices = callback

    def clearCallbackProcessAfterUpdateDevices(self) -> None:
        """Clears the callback that runs after device lists are updated."""
        self.callback_process_after_update_devices = None

    def runProcessAfterUpdateDevices(self) -> None:
        """Executes the registered callback after device lists are updated and changes are noticed."""
        if isinstance(self.callback_process_after_update_devices, Callable):
            try:
                self.callback_process_after_update_devices()
            except Exception as e:
                errorLogging(f"Error in runProcessAfterUpdateDevices callback: {e}")

    def noticeUpdateDevices(self) -> None:
        """
        Notifies relevant parts of the application about device changes
        by invoking registered callbacks based on set update flags.
        Resets update flags after processing.
        """
        if self.update_flag_default_mic_device:
            self.setMicDefaultDevice()
        if self.update_flag_default_speaker_device:
            self.setSpeakerDefaultDevice()
        if self.update_flag_host_list:
            self.setMicHostList()
        if self.update_flag_mic_device_list:
            self.setMicDeviceList()
        if self.update_flag_speaker_device_list:
            self.setSpeakerDeviceList()

        # Reset all flags after processing
        self.update_flag_default_mic_device = False
        self.update_flag_default_speaker_device = False
        self.update_flag_host_list = False
        self.update_flag_mic_device_list = False
        self.update_flag_speaker_device_list = False

    def setMicDefaultDevice(self) -> None:
        """Invokes the callback for default microphone device changes if registered."""
        if isinstance(self.callback_default_mic_device, Callable):
            try:
                # Ensure keys exist before accessing, or use .get with defaults
                host_name = self.default_mic_device.get("host", {}).get("name", "Unknown Host")
                device_name = self.default_mic_device.get("device", {}).get("name", "Unknown Device")
                self.callback_default_mic_device(str(host_name), str(device_name))
            except Exception as e:
                errorLogging(f"Error in setMicDefaultDevice callback: {e}")

    def setSpeakerDefaultDevice(self) -> None:
        """Invokes the callback for default speaker device changes if registered."""
        if isinstance(self.callback_default_speaker_device, Callable):
            try:
                device_name = self.default_speaker_device.get("device", {}).get("name", "Unknown Device")
                self.callback_default_speaker_device(str(device_name))
            except Exception as e:
                errorLogging(f"Error in setSpeakerDefaultDevice callback: {e}")

    def setMicHostList(self) -> None:
        """Invokes the callback for microphone host list changes if registered."""
        if isinstance(self.callback_host_list, Callable):
            try:
                self.callback_host_list()
            except Exception as e:
                errorLogging(f"Error in setMicHostList callback: {e}")

    def setMicDeviceList(self) -> None:
        """Invokes the callback for microphone device list changes if registered."""
        if isinstance(self.callback_mic_device_list, Callable):
            try:
                self.callback_mic_device_list()
            except Exception as e:
                errorLogging(f"Error in setMicDeviceList callback: {e}")

    def setSpeakerDeviceList(self) -> None:
        """Invokes the callback for speaker device list changes if registered."""
        if isinstance(self.callback_speaker_device_list, Callable):
            try:
                self.callback_speaker_device_list()
            except Exception as e:
                errorLogging(f"Error in setSpeakerDeviceList callback: {e}")

    def getMicDevices(self) -> Dict[str, List[DeviceInfo]]:
        """Returns the dictionary of available microphone devices, grouped by host API."""
        return self.mic_devices

    def getDefaultMicDevice(self) -> Dict[str, HostInfo | DeviceInfo]: # type: ignore
        """Returns the current default microphone device information."""
        return self.default_mic_device

    def getSpeakerDevices(self) -> List[DeviceInfo]:
        """Returns the list of available speaker devices (loopback capture)."""
        return self.speaker_devices

    def getDefaultSpeakerDevice(self) -> Dict[str, DeviceInfo]:
        """Returns the current default speaker device information (loopback capture)."""
        return self.default_speaker_device

    def forceUpdateAndSetMicDevices(self) -> None:
        """Manually triggers a device scan, updates internal lists, and calls notification callbacks for mic devices."""
        self.update()
        # These directly call the callbacks if registered
        self.setMicHostList()
        self.setMicDeviceList()
        self.setMicDefaultDevice()

    def forceUpdateAndSetSpeakerDevices(self) -> None:
        """Manually triggers a device scan, updates internal lists, and calls notification callbacks for speaker devices."""
        self.update()
        # These directly call the callbacks if registered
        self.setSpeakerDeviceList()
        self.setSpeakerDefaultDevice()

device_manager: DeviceManager = DeviceManager()

if __name__ == "__main__":
    # print("getMicDevices()", device_manager.getMicDevices())
    # print("getDefaultMicDevice()", device_manager.getDefaultMicDevice())
    # print("getSpeakerDevices()", device_manager.getSpeakerDevices())
    # print("getDefaultSpeakerDevice()", device_manager.getDefaultSpeakerDevice())

    while True:
        sleep(1)