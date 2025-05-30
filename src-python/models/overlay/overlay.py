"""Manages OpenVR overlays, including their creation, rendering, and interaction with SteamVR."""
import ctypes
import os
import time
from threading import Thread
from typing import Any, Dict, List, Optional, Tuple # Added List for completeness, though not strictly in this snippet yet

import numpy as np
import openvr # Third-party
from PIL import Image # Third-party
from psutil import process_iter # Third-party

try:
    from utils import errorLogging # Local application
except ImportError:
    import traceback # Standard library
    def errorLogging() -> None: # Added type hint
        """Basic error logging if the main utils.errorLogging is not available."""
        print(traceback.format_exc())

try:
    from . import overlay_utils as utils # Local application relative import
except ImportError:
    import overlay_utils as utils # Fallback for direct execution or different structure

def mat34Id(array: np.ndarray) -> openvr.HmdMatrix34_t:
    """Converts a 3x4 NumPy array to an OpenVR HmdMatrix34_t."""
    if array.shape != (3, 4):
        raise ValueError("Input array must be 3x4 for HmdMatrix34_t conversion.")
    arr_openvr = openvr.HmdMatrix34_t()
    for i in range(3):
        for j in range(4):
            arr_openvr[i][j] = array[i][j]
    return arr_openvr

def getBaseMatrix(x_pos: float, y_pos: float, z_pos: float, x_rotation: float, y_rotation: float, z_rotation: float) -> np.ndarray:
    """
    Calculates a 3x4 base transformation matrix from position and Euler rotation angles.
    Note: The original z_pos scaling for x_pos and y_pos might be specific to a certain coordinate system setup.
    """
    arr = np.zeros((3, 4), dtype=float)
    # Assuming euler_to_rotation_matrix returns a 3x3 matrix
    rot: np.ndarray = utils.euler_to_rotation_matrix((x_rotation, y_rotation, z_rotation))

    arr[0:3, 0:3] = rot[0:3, 0:3] # Assign rotation part

    # Original translation logic:
    arr[0][3] = x_pos * z_pos # This scaling by z_pos is unusual for standard transformations.
    arr[1][3] = y_pos * z_pos # Consider if this is intended or if direct x_pos, y_pos is needed.
    arr[2][3] = -z_pos      # Z is often inverted for camera-relative positions.
    return arr

def getHMDBaseMatrix() -> np.ndarray:
    """Returns a predefined base matrix for HMD-relative positioning."""
    x_pos = 0.0
    y_pos = -0.4 # Slightly below HMD center
    z_pos = 1.0  # 1 meter in front
    x_rotation = 0.0
    y_rotation = 0.0
    z_rotation = 0.0
    return getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)

def getLeftHandBaseMatrix() -> np.ndarray:
    """Returns a predefined base matrix for left-hand relative positioning."""
    x_pos = 0.3
    y_pos = 0.1
    z_pos = -0.31 # Slightly in front and offset from hand model origin
    x_rotation = -65.0
    y_rotation = 165.0
    z_rotation = 115.0
    return getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)

def getRightHandBaseMatrix() -> np.ndarray:
    """Returns a predefined base matrix for right-hand relative positioning."""
    x_pos = -0.3
    y_pos = 0.1
    z_pos = -0.31
    x_rotation = -65.0
    y_rotation = -165.0
    z_rotation = -115.0
    return getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)


class Overlay:
    """Main class for managing VR overlays via OpenVR."""
    system: Optional[openvr.IVRSystem]
    overlay: Optional[openvr.IVROverlay]
    # overlay_system: Optional[openvr.IVRSystem] # This was a duplicate of 'system' in original __init__
    handle: Dict[str, int] # Stores overlay handles (uint64 from OpenVR, int in Python)
    
    init_process: bool # Flag to indicate if initialization is in progress
    initialized: bool  # Flag to indicate if OpenVR and overlays are successfully initialized
    loop: bool         # Flag to control the main rendering loop
    thread_overlay: Optional[Thread] # Thread for the overlay rendering loop

    settings: Dict[str, Dict[str, Any]] # Stores settings for different overlay sizes (e.g., "small", "large")
    lastUpdate: Dict[str, float]        # Timestamp of the last update for each overlay size (for fading)
    fadeRatio: Dict[str, float]         # Current fade ratio for each overlay size

    def __init__(self, settings_dict: Dict[str, Dict[str, Any]]) -> None:
        """
        Initializes the Overlay manager with given settings.

        Args:
            settings_dict: A dictionary where keys are overlay size identifiers (e.g., "small", "large")
                           and values are dictionaries of settings for that size.
        """
        self.system = None
        self.overlay = None
        # self.overlay_system = None # Removed, as self.system can be used
        self.handle = {}
        self.init_process = False
        self.initialized = False
        self.loop = False
        self.thread_overlay = None

        self.settings: Dict[str, Dict[str, Any]] = {} 
        self.lastUpdate: Dict[str, float] = {}
        self.fadeRatio: Dict[str, float] = {}
        for key, value in settings_dict.items():
            self.settings[key] = value.copy() 
            self.lastUpdate[key] = time.monotonic()
            self.fadeRatio[key] = 1.0 

    def init(self) -> None:
        """Initializes the OpenVR system and creates overlays as defined in settings."""
        try:
            openvr.checkInitError(openvr.VRApplication_Background) 
            self.system = openvr.VRSystem() 
            if not self.system:
                raise openvr.OpenVRError("Failed to get IVRSystem interface from OpenVR.")
            self.overlay = openvr.IVROverlay()
            if not self.overlay:
                raise openvr.OpenVRError("Failed to get IVROverlay interface from OpenVR.")
            
            self.handle = {} 
            for i, size_key in enumerate(self.settings.keys()):
                overlay_key_str = f"VRCT.Overlay.{size_key}.{os.getpid()}.{i}"
                overlay_name_str = f"VRCT Overlay ({size_key})"
                self.handle[size_key] = self.overlay.createOverlay(overlay_key_str, overlay_name_str)
                self.overlay.showOverlay(self.handle[size_key])
            
            self.initialized = True
            print("OpenVR Initialized and Overlays Created.") # Consider using logging

            for size_key in self.settings.keys():
                s = self.settings[size_key]
                self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), size_key) 
                self.updateColor((1.0, 1.0, 1.0), size_key) 
                self.updateOpacity(float(s.get("opacity", 1.0)), size_key)
                self.updateUiScaling(float(s.get("ui_scaling", 1.0)), size_key)
                self.updatePosition(
                    float(s.get("x_pos", 0.0)), float(s.get("y_pos", 0.0)), float(s.get("z_pos", 1.0)),
                    float(s.get("x_rotation", 0.0)), float(s.get("y_rotation", 0.0)), float(s.get("z_rotation", 0.0)),
                    str(s.get("tracker", "HMD")), size_key
                )
                self.updateDisplayDuration(int(s.get("display_duration", 5)), size_key)
                self.updateFadeoutDuration(int(s.get("fadeout_duration", 2)), size_key)
            self.init_process = False
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR Initialization Error: {e}")
            if self.system: openvr.shutdown()
            self.system = None
            self.overlay = None
            self.initialized = False
            self.init_process = False 
        except Exception as e: 
            errorLogging(f"Unexpected error during Overlay init: {e}")
            if self.system: openvr.shutdown() 
            self.system = None
            self.overlay = None
            self.initialized = False
            self.init_process = False

    def updateImage(self, img: Image.Image, size: str) -> None:
        """Updates the specified overlay with a new image after converting it to raw RGBA bytes."""
        if not self.initialized or not self.overlay or size not in self.handle:
            return

        width, height = img.size
        if width == 0 or height == 0:
            errorLogging(f"Overlay image for '{size}' has zero dimension ({width}x{height}). Skipping update.")
            return
            
        try:
            img_rgba = img.convert("RGBA") if img.mode != "RGBA" else img
            img_bytes = img_rgba.tobytes()
            img_ctype = (ctypes.c_char * len(img_bytes)).from_buffer_copy(img_bytes)
            self.overlay.setOverlayRaw(self.handle[size], img_ctype, width, height, 4) 
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR Error updating image for overlay '{size}': {e}. Attempting to restart overlay.")
            self.reStartOverlay() 
        except Exception as e:
            errorLogging(f"Unexpected error updating image for overlay '{size}': {e}")

        self.lastUpdate[size] = time.monotonic() 
        self.fadeRatio[size] = 1.0 
        # Re-apply opacity after setting new image, as some OpenVR actions might reset it.
        current_opacity = self.settings[size].get("opacity", 1.0) # Get current opacity from settings
        if isinstance(current_opacity, (float, int)):
             self.updateOpacity(float(current_opacity), size) # Call updateOpacity to handle actual application
        else: # Fallback if opacity is not a number
             self.updateOpacity(1.0, size)


    def clearImage(self, size: str) -> None:
        """Clears the specified overlay by setting a transparent 1x1 image."""
        if not self.initialized or not self.overlay or size not in self.handle: # Check essential attributes
            return
        transparent_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        self.updateImage(transparent_img, size)

    def updateColor(self, col: Tuple[float, float, float], size: str) -> None:
        """
        Updates the color tint of the specified overlay.

        Args:
            col: A 3-tuple (r, g, b) with values between 0.0 and 1.0.
            size: The identifier for the overlay size (e.g., "small", "large").
        """
        if not self.initialized or not self.overlay or size not in self.handle:
            return
        r, g, b = col # Ensure col has 3 elements if necessary, though Tuple type hint helps
        try:
            self.overlay.setOverlayColor(self.handle[size], r, g, b)
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR Error updating color for overlay '{size}': {e}")
        except Exception as e:
            errorLogging(f"Unexpected error updating color for overlay '{size}': {e}")

    def updateOpacity(self, opacity: float, size: str, with_fade: bool = False) -> None:
        """Updates the opacity of the specified overlay, optionally applying current fade ratio."""
        # Ensure opacity is float and clamped between 0.0 and 1.0
        clamped_opacity = max(0.0, min(1.0, float(opacity)))
        self.settings[size]["opacity"] = clamped_opacity

        if not self.initialized or not self.overlay or size not in self.handle:
            return
        
        current_opacity_setting = self.settings[size]["opacity"] # Already clamped
        effective_opacity: float
        if with_fade:
            # Ensure fadeRatio is also clamped and valid
            current_fade_ratio = max(0.0, min(1.0, self.fadeRatio.get(size, 1.0)))
            effective_opacity = current_fade_ratio * current_opacity_setting
        else:
            effective_opacity = current_opacity_setting
        
        try:
            self.overlay.setOverlayAlpha(self.handle[size], max(0.0, min(1.0, effective_opacity))) # Final clamp
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR Error updating opacity for overlay '{size}': {e}")
        except Exception as e:
            errorLogging(f"Unexpected error updating opacity for overlay '{size}': {e}")

    def updateUiScaling(self, ui_scaling: float, size: str) -> None:
        """Updates the width (in meters) of the specified overlay in the virtual world."""
        self.settings[size]["ui_scaling"] = float(ui_scaling) # Ensure float
        if not self.initialized or not self.overlay or size not in self.handle:
            return
        try:
            self.overlay.setOverlayWidthInMeters(self.handle[size], self.settings[size]["ui_scaling"]) 
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR Error updating UI scaling for overlay '{size}': {e}")
        except Exception as e:
            errorLogging(f"Unexpected error updating UI scaling for overlay '{size}': {e}")

    def updatePosition(self, x_pos: float, y_pos: float, z_pos: float, x_rotation: float, y_rotation: float, z_rotation: float, tracker: str, size: str) -> None:
        """
        Updates the position and rotation of the specified overlay relative to a tracker.
        Ensures all numerical inputs are floats.
        """
        s = self.settings[size] # s is a Dict[str, Any]
        s["x_pos"], s["y_pos"], s["z_pos"] = float(x_pos), float(y_pos), float(z_pos)
        s["x_rotation"], s["y_rotation"], s["z_rotation"] = float(x_rotation), float(y_rotation), float(z_rotation)
        s["tracker"] = str(tracker) # Ensure tracker is a string

        if not self.initialized or not self.overlay or not self.system or size not in self.handle:
            return

        base_matrix: np.ndarray
        tracker_index: int # openvr uses uint32 for device indices

        match tracker:
            case "HMD":
                base_matrix = getHMDBaseMatrix()
                tracker_index = openvr.k_unTrackedDeviceIndex_Hmd
            case "LeftHand":
                base_matrix = getLeftHandBaseMatrix()
                tracker_index = self.system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_LeftHand)
            case "RightHand":
                base_matrix = getRightHandBaseMatrix()
                tracker_index = self.system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_RightHand)
            case _: 
                errorLogging(f"Unknown tracker type '{tracker}' for overlay '{size}'. Defaulting to HMD.")
                base_matrix = getHMDBaseMatrix()
                tracker_index = openvr.k_unTrackedDeviceIndex_Hmd
        
        # Ensure values from settings are correctly typed before use
        current_x_pos: float = s.get("x_pos", 0.0)
        current_y_pos: float = s.get("y_pos", 0.0)
        current_z_pos: float = s.get("z_pos", 0.0) 
        current_x_rot: float = s.get("x_rotation", 0.0)
        current_y_rot: float = s.get("y_rotation", 0.0)
        current_z_rot: float = s.get("z_rotation", 0.0)

        translation_vec: Tuple[float, float, float] = (current_x_pos, current_y_pos, -current_z_pos) 
        rotation_vec: Tuple[float, float, float] = (current_x_rot, current_y_rot, current_z_rot)
        
        try:
            if not self.system.isTrackedDeviceConnected(tracker_index):
                # Silently return if tracker not connected, to avoid log spam.
                return 

            transform_np: np.ndarray = utils.transform_matrix(base_matrix, translation_vec, rotation_vec)
            transform_ovr: openvr.HmdMatrix34_t = mat34Id(transform_np)

            self.overlay.setOverlayTransformTrackedDeviceRelative(self.handle[size], tracker_index, transform_ovr)
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR Error updating position for overlay '{size}': {e}")
        except Exception as e:
            errorLogging(f"Unexpected error updating position for overlay '{size}': {e}")

    def updateDisplayDuration(self, display_duration: int, size: str) -> None:
        """Updates the display duration setting for the specified overlay. Ensures non-negative integer."""
        self.settings[size]["display_duration"] = max(0, int(display_duration)) 

    def updateFadeoutDuration(self, fadeout_duration: int, size: str) -> None:
        """Updates the fade-out duration setting for the specified overlay. Ensures non-negative integer."""
        self.settings[size]["fadeout_duration"] = max(0, int(fadeout_duration)) 

    def checkActive(self) -> bool:
        """
        Checks if the VR system is active and processes OpenVR events.
        Returns False if a quit event is received or an error occurs.
        """
        try:
            if self.system is not None and self.initialized is True:
                new_event = openvr.VREvent_t()
                # Poll all pending events
                while self.system.pollNextEvent(new_event, ctypes.sizeof(openvr.VREvent_t)):
                    if new_event.eventType == openvr.VREvent_Quit:
                        print("OpenVR Quit Event received. Shutting down overlay.") # Consider logging
                        self.shutdownOverlay() # Initiate shutdown on quit event
                        return False
            return True # Assume active if no quit event and no errors
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR error during event polling: {e}")
            self.shutdownOverlay() # Attempt to shutdown on OpenVR error
            return False
        except Exception as e: # Catch any other unexpected errors
            errorLogging(f"Unexpected error in checkActive: {e}")
            self.shutdownOverlay() # Attempt to shutdown
            return False

    def evaluateOpacityFade(self, size: str) -> None:
        """Calculates and applies opacity fade effect based on time since last update."""
        if not self.initialized or not self.overlay or size not in self.handle:
            return

        current_time = time.monotonic()
        display_duration = self.settings[size].get("display_duration", 5)
        fadeout_duration = self.settings[size].get("fadeout_duration", 2)
        
        if fadeout_duration <= 0: # Avoid division by zero if fadeout is instant or disabled
            self.fadeRatio[size] = 0.0 if (current_time - self.lastUpdate.get(size, current_time)) > display_duration else 1.0
        elif (current_time - self.lastUpdate.get(size, current_time)) > display_duration:
            time_since_display_end = current_time - self.lastUpdate.get(size, current_time) - display_duration
            ratio = 1.0 - (time_since_display_end / fadeout_duration)
            self.fadeRatio[size] = max(0.0, min(1.0, ratio)) # Clamp between 0 and 1
        else:
            self.fadeRatio[size] = 1.0 # Not yet fading

        try:
            # Apply the calculated fade ratio to the base opacity
            base_opacity = float(self.settings[size].get("opacity", 1.0))
            effective_opacity = self.fadeRatio[size] * base_opacity
            self.overlay.setOverlayAlpha(self.handle[size], max(0.0, min(1.0, effective_opacity)))
        except openvr.OpenVRError as e:
            errorLogging(f"OpenVR error during opacity fade for overlay '{size}': {e}")
        except Exception as e:
            errorLogging(f"Unexpected error during opacity fade for overlay '{size}': {e}")


    def update(self, size: str) -> None:
        """Updates a specific overlay's opacity, applying fade if configured."""
        if not self.initialized or size not in self.settings:
            return
            
        if self.settings[size].get("fadeout_duration", 0) > 0:
            self.evaluateOpacityFade(size)
        else:
            # No fade, just ensure current opacity is set
            self.updateOpacity(float(self.settings[size].get("opacity", 1.0)), size, with_fade=False)

    def mainloop(self) -> None:
        """Main rendering loop for overlays. Continuously updates overlay states."""
        self.loop = True
        target_frame_time = 1.0 / 16.0 # Target 16 FPS for overlay updates, can be adjusted
        
        print("Overlay mainloop started.") # Consider logging
        while self.loop and self.checkActive(): # checkActive also handles VR quit events
            start_time = time.monotonic()
            
            for size_key in self.settings.keys(): # Iterate over configured overlay sizes
                self.update(size_key)
            
            elapsed_time = time.monotonic() - start_time
            sleep_time = target_frame_time - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        print("Overlay mainloop ended.") # Consider logging
        # Ensure shutdown is called if loop exits due to checkActive() returning False
        if not self.loop: # If loop was stopped by self.stop()
             pass # shutdownOverlay will be called by the stop method
        else: # If loop was stopped by checkActive (e.g. VR quit)
             self.shutdownOverlay()


    def main(self) -> None:
        """Entry point for the overlay thread. Waits for SteamVR, initializes, then runs mainloop."""
        print("Overlay thread started. Waiting for SteamVR...") # Consider logging
        while not self.checkSteamvrRunning():
            if not self.loop: # Allow early exit if shutdownOverlay was called
                print("SteamVR not found and overlay startup cancelled.")
                return
            time.sleep(10)
        
        print("SteamVR detected. Initializing Overlay...") # Consider logging
        if not self.init_process: # Ensure init is only called if not already in process by another call
            self.init_process = True # Mark that we are attempting init
            self.init() # Attempt to initialize OpenVR and overlays
            self.init_process = False # Reset flag after init attempt
        
        if self.initialized:
            self.mainloop()
        else:
            print("Overlay initialization failed. Thread exiting.") # Consider logging


    def startOverlay(self) -> None:
        """Starts the overlay system in a new thread if not already initialized or starting."""
        if not self.initialized and not self.init_process:
            print("Attempting to start overlay thread.") # Consider logging
            self.init_process = True # Set flag before starting thread
            self.loop = True # Ensure loop flag is true before thread starts
            self.thread_overlay = Thread(target=self.main, name="OverlayThread")
            self.thread_overlay.daemon = True
            self.thread_overlay.start()
        elif self.initialized:
            print("Overlay already initialized and potentially running.")
        elif self.init_process:
            print("Overlay initialization already in progress.")


    def shutdownOverlay(self) -> None:
        """Shuts down the OpenVR system and destroys overlays."""
        print("Attempting to shutdown overlay...") # Consider logging
        self.loop = False # Signal mainloop to stop
        
        thread_to_join = self.thread_overlay
        if thread_to_join is not None and thread_to_join.is_alive():
            print("Joining overlay thread...") # Consider logging
            thread_to_join.join(timeout=2.0) # Wait for the thread to finish
            if thread_to_join.is_alive():
                errorLogging("Overlay thread did not join in time.")
        self.thread_overlay = None

        if self.initialized and self.overlay:
            try:
                for size_key in self.handle: # Iterate over keys that were successfully created
                    if isinstance(self.handle[size_key], int): # Check if handle is valid int
                         self.overlay.destroyOverlay(self.handle[size_key])
                print("Overlays destroyed.") # Consider logging
            except openvr.OpenVRError as e:
                errorLogging(f"OpenVR error destroying overlays: {e}")
            except Exception as e:
                errorLogging(f"Unexpected error destroying overlays: {e}")
            finally:
                self.overlay = None # Clear overlay object
        
        if self.system: # Check if system was initialized
            try:
                openvr.shutdown()
                print("OpenVR shutdown.") # Consider logging
            except openvr.OpenVRError as e:
                errorLogging(f"OpenVR error during shutdown: {e}")
            except Exception as e:
                errorLogging(f"Unexpected error during OpenVR shutdown: {e}")
            finally:
                self.system = None
        
        self.initialized = False
        self.init_process = False # Reset init_process flag
        print("Overlay shutdown complete.")


    def reStartOverlay(self) -> None:
        """Restarts the overlay system by shutting it down and then starting it again."""
        print("Restarting overlay...") # Consider logging
        self.shutdownOverlay()
        # Wait a moment before restarting to ensure resources are released
        time.sleep(0.5) 
        self.startOverlay()

    @classmethod # Changed to classmethod as it doesn't use 'self'
    def checkSteamvrRunning(cls) -> bool:
        """Checks if SteamVR (vrmonitor.exe) is currently running."""
        _proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
        return _proc_name in (p.name() for p in process_iter())

if __name__ == "__main__":
# Example usage for Overlay.
    from overlay_image import OverlayImage
    import logging

    logging.basicConfig(level=logging.DEBUG)

    small_settings = {
        "x_pos": 0.0,
        "y_pos": 0.0,
        "z_pos": 0.0,
        "x_rotation": 0.0,
        "y_rotation": 0.0,
        "z_rotation": 0.0,
        "display_duration": 5,
        "fadeout_duration": 2,
        "opacity": 1.0,
        "ui_scaling": 1.0,
        "tracker": "HMD",
    }

    large_settings = {
        "x_pos": 0.0,
        "y_pos": 0.0,
        "z_pos": 0.0,
        "x_rotation": 0.0,
        "y_rotation": 0.0,
        "z_rotation": 0.0,
        "display_duration": 5,
        "fadeout_duration": 2,
        "opacity": 1.0,
        "ui_scaling": 0.25,
        "tracker": "LeftHand",
    }

    settings_dict = {
        "small": small_settings,
        "large": large_settings
    }

    # オーバーレイの初期化設定を確認
    logging.debug(f"Settings Dict: {settings_dict}")

    overlay_image = OverlayImage()
    overlay = Overlay(settings_dict)
    overlay.startOverlay()

    while overlay.initialized is False:
        time.sleep(1)

    # Example usage
    for i in range(1000):
        try:
            print(i)
            img = overlay_image.createOverlayImageLargeLog("send", f"こんにちは、世界！さようなら {i}", "Japanese", "Hello,World!Goodbye", "Japanese")
            logging.debug(f"Generated Image: {img}")
            overlay.updateImage(img, "large")
            img = overlay_image.createOverlayImageSmallLog(f"こんにちは、世界！さようなら_{i}", "Japanese", "Hello,World!Goodbye", "Japanese")
            overlay.updateImage(img, "small")
            time.sleep(1)
        except openvr.error_code.OverlayError_InvalidParameter as e:
            errorLogging()
            logging.error(f"OverlayError_InvalidParameter: {e}")
            break
        except Exception as e:
            errorLogging()
            logging.error(f"Unexpected error: {e}")
            break

    # for i in range(100):
    #     print(i)
    #     # Example usage
    #     img = overlay_image.createOverlayImageSmallLog(f"こんにちは、世界！さようなら_{i}", "Japanese", "Hello,World!Goodbye", "Japanese")
    #     overlay.updateImage(img, "small")
    #     time.sleep(5)

    #     if i%2 == 0:
    #         overlay.updatePosition(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "HMD", "small")
    #     else:
    #         overlay.updatePosition(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "RightHand", "small")

    overlay.shutdownOverlay()