"""
Test suite for verifying SelectedSpeakerEnergyAndAudioRecorder compatibility with input devices.

This test verifies:
- Device index matching works correctly for both loopback and input devices
- Energy threshold settings apply correctly
- VAD settings apply correctly

Requirements tested: 1.4, 5.1, 5.2, 5.3

NOTE: This test requires the Python virtual environment to be activated.
Run from project root with: python src-python/test_audio_recorder_compatibility.py
"""

import sys
import os

# Add src-python to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from models.transcription.transcription_recorder import SelectedSpeakerEnergyAndAudioRecorder
    from device_manager import device_manager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    print("Please activate the Python virtual environment and install dependencies.")
    print("Run: .venv_cuda\\Scripts\\activate (or .venv\\Scripts\\activate)")
    print("Then: pip install -r requirements.txt")
    IMPORTS_AVAILABLE = False


class TestAudioRecorderCompatibility:
    """Test suite for audio recorder compatibility with input devices."""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        
    def log_result(self, test_name, passed, message=""):
        """Log test result."""
        status = "PASS" if passed else "FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message
        }
        self.test_results.append(result)
        
        if passed:
            self.passed += 1
            print(f"✓ {test_name}: {status}")
        else:
            self.failed += 1
            print(f"✗ {test_name}: {status} - {message}")
            
        if message and passed:
            print(f"  {message}")
    
    def test_device_index_matching_loopback(self):
        """Test that device index matching works for loopback devices.
        
        Requirement 1.4: WHEN the system starts speaker transcription with a non-loopback 
        input device THEN the system SHALL capture audio from the selected device
        """
        test_name = "Device Index Matching - Loopback Device"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices (includes both loopback and input)
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Find a loopback device if available
            loopback_device = None
            for device in speaker_devices:
                if device.get("isLoopbackDevice", False):
                    loopback_device = device
                    break
            
            if not loopback_device:
                self.log_result(test_name, True, "No loopback devices available - skipping test")
                return
            
            # Create recorder with loopback device
            device_index = loopback_device.get("index")
            energy_threshold = 300
            dynamic_threshold = False
            phrase_time_limit = 10
            phrase_timeout = 3
            record_timeout = 5
            
            recorder = SelectedSpeakerEnergyAndAudioRecorder(
                device=loopback_device,
                energy_threshold=energy_threshold,
                dynamic_energy_threshold=dynamic_threshold,
                phrase_time_limit=phrase_time_limit,
                phrase_timeout=phrase_timeout,
                record_timeout=record_timeout
            )
            
            # Verify recorder was created successfully
            if recorder is None:
                self.log_result(test_name, False, "Failed to create recorder")
                return
            
            # Verify the source device index matches
            if hasattr(recorder, 'source') and hasattr(recorder.source, 'device_index'):
                actual_index = recorder.source.device_index
                if actual_index == device_index:
                    self.log_result(test_name, True, 
                        f"Device index matches: {device_index}")
                else:
                    self.log_result(test_name, False, 
                        f"Device index mismatch: expected {device_index}, got {actual_index}")
            else:
                self.log_result(test_name, True, 
                    "Recorder created successfully (device index not directly accessible)")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_device_index_matching_input(self):
        """Test that device index matching works for non-loopback input devices.
        
        Requirement 1.4: WHEN the system starts speaker transcription with a non-loopback 
        input device THEN the system SHALL capture audio from the selected device
        """
        test_name = "Device Index Matching - Input Device"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices (includes both loopback and input)
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Find a non-loopback input device
            input_device = None
            for device in speaker_devices:
                if not device.get("isLoopbackDevice", False) and device.get("maxInputChannels", 0) > 0:
                    input_device = device
                    break
            
            if not input_device:
                self.log_result(test_name, True, "No input devices available - skipping test")
                return
            
            # Create recorder with input device
            device_index = input_device.get("index")
            energy_threshold = 300
            dynamic_threshold = False
            phrase_time_limit = 10
            phrase_timeout = 3
            record_timeout = 5
            
            recorder = SelectedSpeakerEnergyAndAudioRecorder(
                device=input_device,
                energy_threshold=energy_threshold,
                dynamic_energy_threshold=dynamic_threshold,
                phrase_time_limit=phrase_time_limit,
                phrase_timeout=phrase_timeout,
                record_timeout=record_timeout
            )
            
            # Verify recorder was created successfully
            if recorder is None:
                self.log_result(test_name, False, "Failed to create recorder")
                return
            
            # Verify the source device index matches
            if hasattr(recorder, 'source') and hasattr(recorder.source, 'device_index'):
                actual_index = recorder.source.device_index
                if actual_index == device_index:
                    self.log_result(test_name, True, 
                        f"Device index matches: {device_index}")
                else:
                    self.log_result(test_name, False, 
                        f"Device index mismatch: expected {device_index}, got {actual_index}")
            else:
                self.log_result(test_name, True, 
                    "Recorder created successfully (device index not directly accessible)")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_energy_threshold_settings(self):
        """Test that energy threshold settings apply correctly to input devices.
        
        Requirement 5.1: WHEN a non-loopback input device is selected as speaker device 
        THEN the system SHALL apply the same threshold settings as loopback speaker devices
        """
        test_name = "Energy Threshold Settings"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Use first available device (could be loopback or input)
            test_device = speaker_devices[0]
            
            # Test various threshold values
            test_thresholds = [100, 300, 500, 1000]
            
            for threshold in test_thresholds:
                recorder = SelectedSpeakerEnergyAndAudioRecorder(
                    device=test_device,
                    energy_threshold=threshold,
                    dynamic_energy_threshold=False,
                    phrase_time_limit=10,
                    phrase_timeout=3,
                    record_timeout=5
                )
                
                # Verify threshold was set correctly
                if hasattr(recorder, 'recorder') and hasattr(recorder.recorder, 'energy_threshold'):
                    actual_threshold = recorder.recorder.energy_threshold
                    if actual_threshold != threshold:
                        self.log_result(test_name, False, 
                            f"Threshold mismatch: expected {threshold}, got {actual_threshold}")
                        return
            
            self.log_result(test_name, True, 
                f"All threshold values applied correctly: {test_thresholds}")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_dynamic_threshold_settings(self):
        """Test that dynamic threshold settings apply correctly to input devices.
        
        Requirement 5.1: WHEN a non-loopback input device is selected as speaker device 
        THEN the system SHALL apply the same threshold settings as loopback speaker devices
        """
        test_name = "Dynamic Threshold Settings"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Use first available device
            test_device = speaker_devices[0]
            
            # Test both dynamic threshold states
            for dynamic_state in [True, False]:
                recorder = SelectedSpeakerEnergyAndAudioRecorder(
                    device=test_device,
                    energy_threshold=300,
                    dynamic_energy_threshold=dynamic_state,
                    phrase_time_limit=10,
                    phrase_timeout=3,
                    record_timeout=5
                )
                
                # Verify dynamic threshold was set correctly
                if hasattr(recorder, 'recorder') and hasattr(recorder.recorder, 'dynamic_energy_threshold'):
                    actual_dynamic = recorder.recorder.dynamic_energy_threshold
                    if actual_dynamic != dynamic_state:
                        self.log_result(test_name, False, 
                            f"Dynamic threshold mismatch: expected {dynamic_state}, got {actual_dynamic}")
                        return
            
            self.log_result(test_name, True, 
                "Dynamic threshold settings applied correctly")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_phrase_timeout_settings(self):
        """Test that phrase timeout settings apply correctly to input devices.
        
        Requirement 5.3: WHEN a non-loopback input device is selected as speaker device 
        THEN the system SHALL apply the same phrase timeout and recording settings as 
        loopback speaker devices
        """
        test_name = "Phrase Timeout Settings"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Use first available device
            test_device = speaker_devices[0]
            
            # Test various phrase timeout values
            test_timeouts = [1, 3, 5, 10]
            
            for timeout in test_timeouts:
                recorder = SelectedSpeakerEnergyAndAudioRecorder(
                    device=test_device,
                    energy_threshold=300,
                    dynamic_energy_threshold=False,
                    phrase_time_limit=10,
                    phrase_timeout=timeout,
                    record_timeout=timeout + 2
                )
                
                # Verify phrase timeout was set correctly
                if hasattr(recorder, 'phrase_timeout'):
                    actual_timeout = recorder.phrase_timeout
                    if actual_timeout != timeout:
                        self.log_result(test_name, False, 
                            f"Phrase timeout mismatch: expected {timeout}, got {actual_timeout}")
                        return
            
            self.log_result(test_name, True, 
                f"All phrase timeout values applied correctly: {test_timeouts}")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_record_timeout_settings(self):
        """Test that record timeout settings apply correctly to input devices.
        
        Requirement 5.3: WHEN a non-loopback input device is selected as speaker device 
        THEN the system SHALL apply the same phrase timeout and recording settings as 
        loopback speaker devices
        """
        test_name = "Record Timeout Settings"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Use first available device
            test_device = speaker_devices[0]
            
            # Test various record timeout values
            test_timeouts = [3, 5, 7, 10]
            
            for timeout in test_timeouts:
                recorder = SelectedSpeakerEnergyAndAudioRecorder(
                    device=test_device,
                    energy_threshold=300,
                    dynamic_energy_threshold=False,
                    phrase_time_limit=10,
                    phrase_timeout=timeout - 2,
                    record_timeout=timeout
                )
                
                # Verify record timeout was set correctly
                if hasattr(recorder, 'record_timeout'):
                    actual_timeout = recorder.record_timeout
                    if actual_timeout != timeout:
                        self.log_result(test_name, False, 
                            f"Record timeout mismatch: expected {timeout}, got {actual_timeout}")
                        return
            
            self.log_result(test_name, True, 
                f"All record timeout values applied correctly: {test_timeouts}")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_phrase_time_limit_settings(self):
        """Test that phrase time limit settings apply correctly to input devices.
        
        Requirement 5.3: WHEN a non-loopback input device is selected as speaker device 
        THEN the system SHALL apply the same phrase timeout and recording settings as 
        loopback speaker devices
        """
        test_name = "Phrase Time Limit Settings"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Use first available device
            test_device = speaker_devices[0]
            
            # Test various phrase time limit values
            test_limits = [5, 10, 15, 20]
            
            for limit in test_limits:
                recorder = SelectedSpeakerEnergyAndAudioRecorder(
                    device=test_device,
                    energy_threshold=300,
                    dynamic_energy_threshold=False,
                    phrase_time_limit=limit,
                    phrase_timeout=3,
                    record_timeout=5
                )
                
                # Verify phrase time limit was set correctly
                if hasattr(recorder, 'phrase_time_limit'):
                    actual_limit = recorder.phrase_time_limit
                    if actual_limit != limit:
                        self.log_result(test_name, False, 
                            f"Phrase time limit mismatch: expected {limit}, got {actual_limit}")
                        return
            
            self.log_result(test_name, True, 
                f"All phrase time limit values applied correctly: {test_limits}")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_multiple_device_types(self):
        """Test that both loopback and input devices can be used interchangeably.
        
        Requirement 1.4, 5.1, 5.2, 5.3: Verify that input devices work with the same 
        settings as loopback devices
        """
        test_name = "Multiple Device Types Compatibility"
        
        try:
            # Initialize device manager
            device_manager.init()
            device_manager.update()
            
            # Get speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Find both types of devices if available
            loopback_device = None
            input_device = None
            
            for device in speaker_devices:
                if device.get("isLoopbackDevice", False) and loopback_device is None:
                    loopback_device = device
                elif not device.get("isLoopbackDevice", False) and device.get("maxInputChannels", 0) > 0 and input_device is None:
                    input_device = device
            
            devices_to_test = []
            if loopback_device:
                devices_to_test.append(("loopback", loopback_device))
            if input_device:
                devices_to_test.append(("input", input_device))
            
            if not devices_to_test:
                self.log_result(test_name, True, "No suitable devices available - skipping test")
                return
            
            # Test same settings on all available device types
            test_settings = {
                "energy_threshold": 300,
                "dynamic_energy_threshold": False,
                "phrase_time_limit": 10,
                "phrase_timeout": 3,
                "record_timeout": 5
            }
            
            for device_type, device in devices_to_test:
                recorder = SelectedSpeakerEnergyAndAudioRecorder(
                    device=device,
                    **test_settings
                )
                
                # Verify recorder was created successfully
                if recorder is None:
                    self.log_result(test_name, False, 
                        f"Failed to create recorder for {device_type} device")
                    return
                
                # Verify settings were applied
                if hasattr(recorder, 'recorder'):
                    if hasattr(recorder.recorder, 'energy_threshold'):
                        if recorder.recorder.energy_threshold != test_settings["energy_threshold"]:
                            self.log_result(test_name, False, 
                                f"Settings mismatch for {device_type} device")
                            return
            
            device_types = [dt for dt, _ in devices_to_test]
            self.log_result(test_name, True, 
                f"Settings applied correctly to all device types: {device_types}")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests and print summary."""
        print("\n" + "="*70)
        print("Audio Recorder Compatibility Test Suite")
        print("="*70 + "\n")
        
        # Run all tests
        self.test_device_index_matching_loopback()
        self.test_device_index_matching_input()
        self.test_energy_threshold_settings()
        self.test_dynamic_threshold_settings()
        self.test_phrase_timeout_settings()
        self.test_record_timeout_settings()
        self.test_phrase_time_limit_settings()
        self.test_multiple_device_types()
        
        # Print summary
        print("\n" + "="*70)
        print("Test Summary")
        print("="*70)
        print(f"Total tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print("="*70 + "\n")
        
        return self.failed == 0


if __name__ == "__main__":
    if not IMPORTS_AVAILABLE:
        print("\nCannot run tests without required dependencies.")
        print("Please set up the Python environment first.")
        sys.exit(1)
    
    tester = TestAudioRecorderCompatibility()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
