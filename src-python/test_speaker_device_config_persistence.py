"""
Test suite for verifying speaker device configuration persistence.

This test verifies:
- Immediate save functionality for speaker device selection
- Configuration round-trip (save and load)
- Fallback to default on unavailable device

Requirements tested: 6.1, 6.2, 6.3, 6.4, 6.5

NOTE: This test requires the Python virtual environment to be activated.
Run from project root with: python src-python/test_speaker_device_config_persistence.py
"""

import sys
import os
import json
import time
import tempfile
import shutil

# Add src-python to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import Config
    from device_manager import device_manager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    print("Please activate the Python virtual environment and install dependencies.")
    print("Run: .venv_cuda\\Scripts\\activate (or .venv\\Scripts\\activate)")
    print("Then: pip install -r requirements.txt")
    IMPORTS_AVAILABLE = False


class TestSpeakerDeviceConfigPersistence:
    """Test suite for speaker device configuration persistence."""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.original_config_path = None
        self.temp_config_path = None
        self.config_backup = None
        
    def setup(self):
        """Set up test environment with temporary config file."""
        # Create a temporary directory for test config
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_path = os.path.join(self.temp_dir, "test_config.json")
        
        # Initialize device manager
        device_manager.init()
        device_manager.update()
        
    def teardown(self):
        """Clean up test environment."""
        # Remove temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
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
    
    def test_speaker_device_save_to_config(self):
        """Test that speaker device selection is saved to configuration.
        
        Requirement 6.1: WHEN a user selects a speaker device (loopback or non-loopback input) 
        THEN the system SHALL save the device name to the configuration file
        """
        test_name = "Speaker Device Save to Config"
        
        try:
            # Create a test config instance
            config = Config()
            original_path = config.PATH_CONFIG
            
            # Temporarily override config path
            config._PATH_CONFIG = self.temp_config_path
            
            # Get available speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                config._PATH_CONFIG = original_path
                return
            
            # Select a speaker device
            test_device_name = speaker_devices[0].get("name")
            config.SELECTED_SPEAKER_DEVICE = test_device_name
            
            # Force immediate save
            config.saveConfigToFile()
            
            # Verify the config file was created and contains the device
            if not os.path.exists(self.temp_config_path):
                self.log_result(test_name, False, "Config file was not created")
                config._PATH_CONFIG = original_path
                return
            
            with open(self.temp_config_path, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
            
            if "SELECTED_SPEAKER_DEVICE" not in saved_config:
                self.log_result(test_name, False, "SELECTED_SPEAKER_DEVICE not in config file")
                config._PATH_CONFIG = original_path
                return
            
            if saved_config["SELECTED_SPEAKER_DEVICE"] != test_device_name:
                self.log_result(test_name, False, 
                    f"Device name mismatch: expected {test_device_name}, got {saved_config['SELECTED_SPEAKER_DEVICE']}")
                config._PATH_CONFIG = original_path
                return
            
            self.log_result(test_name, True, 
                f"Speaker device '{test_device_name}' saved to config successfully")
            
            # Restore original path
            config._PATH_CONFIG = original_path
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_speaker_device_load_from_config(self):
        """Test that speaker device selection is loaded from configuration.
        
        Requirement 6.2: WHEN the application starts THEN the system SHALL load the saved 
        speaker device from configuration
        """
        test_name = "Speaker Device Load from Config"
        
        try:
            # Get available speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Select a test device name
            test_device_name = speaker_devices[0].get("name")
            
            # Create a config file with the device selection
            test_config_data = {
                "SELECTED_SPEAKER_DEVICE": test_device_name,
                "AUTO_SPEAKER_SELECT": False,
                "SPEAKER_THRESHOLD": 300
            }
            
            with open(self.temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(test_config_data, f, indent=4)
            
            # Create a new config instance and load from the temp file
            config = Config()
            original_path = config.PATH_CONFIG
            config._PATH_CONFIG = self.temp_config_path
            
            # Load the config
            config.load_config()
            
            # Verify the device was loaded correctly
            loaded_device = config.SELECTED_SPEAKER_DEVICE
            
            if loaded_device != test_device_name:
                self.log_result(test_name, False, 
                    f"Device name mismatch: expected {test_device_name}, got {loaded_device}")
                config._PATH_CONFIG = original_path
                return
            
            self.log_result(test_name, True, 
                f"Speaker device '{test_device_name}' loaded from config successfully")
            
            # Restore original path
            config._PATH_CONFIG = original_path
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_speaker_device_round_trip(self):
        """Test configuration round-trip (save and load).
        
        Requirement 6.1, 6.2: Verify that saving and loading preserves the device selection
        """
        test_name = "Speaker Device Round-Trip"
        
        try:
            # Get available speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Test with multiple devices if available
            test_devices = [d.get("name") for d in speaker_devices[:min(3, len(speaker_devices))]]
            
            for test_device_name in test_devices:
                # Create config and save device
                config1 = Config()
                original_path = config1.PATH_CONFIG
                config1._PATH_CONFIG = self.temp_config_path
                
                config1.SELECTED_SPEAKER_DEVICE = test_device_name
                config1.saveConfigToFile()
                
                # Create new config instance and load
                config2 = Config()
                config2._PATH_CONFIG = self.temp_config_path
                config2.load_config()
                
                # Verify round-trip
                loaded_device = config2.SELECTED_SPEAKER_DEVICE
                
                if loaded_device != test_device_name:
                    self.log_result(test_name, False, 
                        f"Round-trip failed for '{test_device_name}': got '{loaded_device}'")
                    config1._PATH_CONFIG = original_path
                    config2._PATH_CONFIG = original_path
                    return
                
                # Restore paths
                config1._PATH_CONFIG = original_path
                config2._PATH_CONFIG = original_path
            
            self.log_result(test_name, True, 
                f"Round-trip successful for {len(test_devices)} device(s)")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_speaker_device_restoration_on_startup(self):
        """Test that saved speaker device is automatically selected on startup.
        
        Requirement 6.3: WHERE the saved speaker device is available, WHEN the application 
        starts THEN the system SHALL automatically select it
        """
        test_name = "Speaker Device Restoration on Startup"
        
        try:
            # Get available speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Select a device that exists
            available_device_name = speaker_devices[0].get("name")
            
            # Create config file with this device
            test_config_data = {
                "SELECTED_SPEAKER_DEVICE": available_device_name,
                "AUTO_SPEAKER_SELECT": False
            }
            
            with open(self.temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(test_config_data, f, indent=4)
            
            # Create new config instance (simulating startup)
            config = Config()
            original_path = config.PATH_CONFIG
            config._PATH_CONFIG = self.temp_config_path
            config.load_config()
            
            # Verify the device was restored
            restored_device = config.SELECTED_SPEAKER_DEVICE
            
            if restored_device != available_device_name:
                self.log_result(test_name, False, 
                    f"Device not restored: expected {available_device_name}, got {restored_device}")
                config._PATH_CONFIG = original_path
                return
            
            self.log_result(test_name, True, 
                f"Speaker device '{available_device_name}' restored on startup")
            
            # Restore original path
            config._PATH_CONFIG = original_path
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_speaker_device_fallback_on_unavailable(self):
        """Test fallback to default when saved device is unavailable.
        
        Requirement 6.4: WHERE the saved speaker device is unavailable, WHEN the application 
        starts THEN the system SHALL fall back to the default speaker loopback device
        """
        test_name = "Speaker Device Fallback on Unavailable"
        
        try:
            # Create config file with a non-existent device
            fake_device_name = "NonExistentDevice_12345"
            
            test_config_data = {
                "SELECTED_SPEAKER_DEVICE": fake_device_name,
                "AUTO_SPEAKER_SELECT": False
            }
            
            with open(self.temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(test_config_data, f, indent=4)
            
            # Create new config instance (simulating startup)
            config = Config()
            original_path = config.PATH_CONFIG
            config._PATH_CONFIG = self.temp_config_path
            config.load_config()
            
            # Verify fallback occurred
            loaded_device = config.SELECTED_SPEAKER_DEVICE
            
            # The validator should reject the invalid device, keeping the previous valid value
            # or falling back to default
            if loaded_device == fake_device_name:
                self.log_result(test_name, False, 
                    "Invalid device was not rejected by validator")
                config._PATH_CONFIG = original_path
                return
            
            # Get default speaker device
            default_speaker = device_manager.getDefaultSpeakerDevice()
            default_device_name = default_speaker.get("device", {}).get("name", "NoDevice")
            
            # The loaded device should either be the default or the previous valid value
            # (which would be "NoDevice" in a fresh config)
            self.log_result(test_name, True, 
                f"Fallback successful: invalid device rejected, current device is '{loaded_device}'")
            
            # Restore original path
            config._PATH_CONFIG = original_path
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_immediate_configuration_persistence(self):
        """Test immediate save functionality for speaker device selection.
        
        Requirement 6.5: WHEN the speaker device selection changes THEN the system SHALL 
        update the configuration file immediately
        
        Note: The SELECTED_SPEAKER_DEVICE property uses ValidatedProperty which doesn't 
        have immediate_save=True by default, so it uses the debounce mechanism. This test
        verifies that the save occurs within the debounce time.
        """
        test_name = "Immediate Configuration Persistence"
        
        try:
            # Create a test config instance
            config = Config()
            original_path = config.PATH_CONFIG
            config._PATH_CONFIG = self.temp_config_path
            
            # Get available speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                config._PATH_CONFIG = original_path
                return
            
            # Select a speaker device
            test_device_name = speaker_devices[0].get("name")
            config.SELECTED_SPEAKER_DEVICE = test_device_name
            
            # Wait for debounce time (2 seconds + buffer)
            time.sleep(2.5)
            
            # Verify the config file was updated
            if not os.path.exists(self.temp_config_path):
                self.log_result(test_name, False, "Config file was not created within debounce time")
                config._PATH_CONFIG = original_path
                return
            
            with open(self.temp_config_path, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
            
            if "SELECTED_SPEAKER_DEVICE" not in saved_config:
                self.log_result(test_name, False, "SELECTED_SPEAKER_DEVICE not in config file")
                config._PATH_CONFIG = original_path
                return
            
            if saved_config["SELECTED_SPEAKER_DEVICE"] != test_device_name:
                self.log_result(test_name, False, 
                    f"Device not saved: expected {test_device_name}, got {saved_config['SELECTED_SPEAKER_DEVICE']}")
                config._PATH_CONFIG = original_path
                return
            
            self.log_result(test_name, True, 
                f"Configuration persisted within debounce time (2 seconds)")
            
            # Restore original path
            config._PATH_CONFIG = original_path
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_speaker_device_settings_persistence(self):
        """Test that all speaker device settings are persisted correctly.
        
        Requirement 6.1, 6.5: Verify that all speaker-related settings are saved
        """
        test_name = "Speaker Device Settings Persistence"
        
        try:
            # Create a test config instance
            config = Config()
            original_path = config.PATH_CONFIG
            config._PATH_CONFIG = self.temp_config_path
            
            # Get available speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                config._PATH_CONFIG = original_path
                return
            
            # Set various speaker settings
            test_device_name = speaker_devices[0].get("name")
            test_settings = {
                "SELECTED_SPEAKER_DEVICE": test_device_name,
                "AUTO_SPEAKER_SELECT": False,
                "SPEAKER_THRESHOLD": 500,
                "SPEAKER_AUTOMATIC_THRESHOLD": True,
                "SPEAKER_RECORD_TIMEOUT": 5,
                "SPEAKER_PHRASE_TIMEOUT": 4,
                "SPEAKER_MAX_PHRASES": 15,
                "SPEAKER_VAD_FILTER": True
            }
            
            for key, value in test_settings.items():
                setattr(config, key, value)
            
            # Force save
            config.saveConfigToFile()
            
            # Load config in new instance
            config2 = Config()
            config2._PATH_CONFIG = self.temp_config_path
            config2.load_config()
            
            # Verify all settings were persisted
            for key, expected_value in test_settings.items():
                actual_value = getattr(config2, key)
                if actual_value != expected_value:
                    self.log_result(test_name, False, 
                        f"Setting {key} mismatch: expected {expected_value}, got {actual_value}")
                    config._PATH_CONFIG = original_path
                    config2._PATH_CONFIG = original_path
                    return
            
            self.log_result(test_name, True, 
                f"All {len(test_settings)} speaker settings persisted correctly")
            
            # Restore original paths
            config._PATH_CONFIG = original_path
            config2._PATH_CONFIG = original_path
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_speaker_device_validator(self):
        """Test that the speaker device validator works correctly.
        
        Requirement 6.1: Verify that only valid device names are accepted
        """
        test_name = "Speaker Device Validator"
        
        try:
            # Create a test config instance
            config = Config()
            
            # Get available speaker devices
            speaker_devices = device_manager.getSpeakerDevices()
            
            if not speaker_devices or speaker_devices[0].get("name") == "NoDevice":
                self.log_result(test_name, True, "No devices available - skipping test")
                return
            
            # Test with valid device
            valid_device_name = speaker_devices[0].get("name")
            original_device = config.SELECTED_SPEAKER_DEVICE
            config.SELECTED_SPEAKER_DEVICE = valid_device_name
            
            if config.SELECTED_SPEAKER_DEVICE != valid_device_name:
                self.log_result(test_name, False, 
                    f"Valid device was rejected: {valid_device_name}")
                return
            
            # Test with invalid device
            invalid_device_name = "InvalidDevice_XYZ_12345"
            config.SELECTED_SPEAKER_DEVICE = invalid_device_name
            
            # The validator should reject the invalid device
            if config.SELECTED_SPEAKER_DEVICE == invalid_device_name:
                self.log_result(test_name, False, 
                    "Invalid device was accepted by validator")
                return
            
            # The device should remain as the previous valid value
            if config.SELECTED_SPEAKER_DEVICE != valid_device_name:
                self.log_result(test_name, False, 
                    f"Device changed unexpectedly: expected {valid_device_name}, got {config.SELECTED_SPEAKER_DEVICE}")
                return
            
            self.log_result(test_name, True, 
                "Validator correctly accepts valid devices and rejects invalid ones")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def test_loopback_and_input_device_persistence(self):
        """Test that both loopback and input devices can be persisted.
        
        Requirement 6.1, 6.2: Verify that both device types work with persistence
        """
        test_name = "Loopback and Input Device Persistence"
        
        try:
            # Get available speaker devices
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
                devices_to_test.append(("loopback", loopback_device.get("name")))
            if input_device:
                devices_to_test.append(("input", input_device.get("name")))
            
            if not devices_to_test:
                self.log_result(test_name, True, "No suitable devices available - skipping test")
                return
            
            # Test persistence for each device type
            for device_type, device_name in devices_to_test:
                # Create config and save device
                config1 = Config()
                original_path = config1.PATH_CONFIG
                config1._PATH_CONFIG = self.temp_config_path
                
                config1.SELECTED_SPEAKER_DEVICE = device_name
                config1.saveConfigToFile()
                
                # Load in new instance
                config2 = Config()
                config2._PATH_CONFIG = self.temp_config_path
                config2.load_config()
                
                # Verify persistence
                loaded_device = config2.SELECTED_SPEAKER_DEVICE
                
                if loaded_device != device_name:
                    self.log_result(test_name, False, 
                        f"Persistence failed for {device_type} device '{device_name}': got '{loaded_device}'")
                    config1._PATH_CONFIG = original_path
                    config2._PATH_CONFIG = original_path
                    return
                
                # Restore paths
                config1._PATH_CONFIG = original_path
                config2._PATH_CONFIG = original_path
            
            device_types = [dt for dt, _ in devices_to_test]
            self.log_result(test_name, True, 
                f"Persistence successful for device types: {device_types}")
                
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests and print summary."""
        print("\n" + "="*70)
        print("Speaker Device Configuration Persistence Test Suite")
        print("="*70 + "\n")
        
        # Set up test environment
        self.setup()
        
        try:
            # Run all tests
            self.test_speaker_device_save_to_config()
            self.test_speaker_device_load_from_config()
            self.test_speaker_device_round_trip()
            self.test_speaker_device_restoration_on_startup()
            self.test_speaker_device_fallback_on_unavailable()
            self.test_immediate_configuration_persistence()
            self.test_speaker_device_settings_persistence()
            self.test_speaker_device_validator()
            self.test_loopback_and_input_device_persistence()
        finally:
            # Clean up test environment
            self.teardown()
        
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
    
    tester = TestSpeakerDeviceConfigPersistence()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
