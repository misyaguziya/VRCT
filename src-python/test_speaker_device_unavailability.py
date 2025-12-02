"""Test speaker device unavailability error handling.

This test verifies that the system properly detects and handles
speaker device unavailability during transcription.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from controller import Controller
from config import config
from device_manager import device_manager


class TestSpeakerDeviceUnavailability(unittest.TestCase):
    """Test speaker device unavailability detection and handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.controller = Controller()
        self.controller.run_mapping = {
            "error_device": "error_device",
            "enable_transcription_receive": "enable_transcription_receive",
        }
        self.run_calls = []
        
        def mock_run(status, endpoint, payload):
            self.run_calls.append({
                "status": status,
                "endpoint": endpoint,
                "payload": payload
            })
        
        self.controller.run = mock_run

    def test_handle_speaker_device_unavailable_when_device_missing(self):
        """Test that handleSpeakerDeviceUnavailable detects missing device."""
        # Set up a selected device that won't be in the list
        config.SELECTED_SPEAKER_DEVICE = "TestDevice"
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        
        # Mock device_manager to return empty list
        with patch.object(device_manager, 'getSpeakerDevices', return_value=[]):
            with patch.object(self.controller, 'stopTranscriptionReceiveMessage'):
                self.controller.handleSpeakerDeviceUnavailable()
        
        # Verify error notification was sent
        error_calls = [call for call in self.run_calls if call["endpoint"] == "error_device"]
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0]["status"], 400)
        self.assertIn("TestDevice", error_calls[0]["payload"]["message"])
        
        # Verify transcription was disabled
        self.assertFalse(config.ENABLE_TRANSCRIPTION_RECEIVE)
        
        # Verify UI was notified
        enable_calls = [call for call in self.run_calls if call["endpoint"] == "enable_transcription_receive"]
        self.assertEqual(len(enable_calls), 1)
        self.assertFalse(enable_calls[0]["payload"])

    def test_handle_speaker_device_unavailable_when_device_present(self):
        """Test that handleSpeakerDeviceUnavailable does nothing when device is present."""
        # Set up a selected device that will be in the list
        config.SELECTED_SPEAKER_DEVICE = "TestDevice"
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        
        # Mock device_manager to return device in list
        mock_devices = [{"name": "TestDevice", "index": 0}]
        with patch.object(device_manager, 'getSpeakerDevices', return_value=mock_devices):
            with patch.object(self.controller, 'stopTranscriptionReceiveMessage') as mock_stop:
                self.controller.handleSpeakerDeviceUnavailable()
                
                # Verify stopTranscriptionReceiveMessage was NOT called
                mock_stop.assert_not_called()
        
        # Verify no error notifications were sent
        error_calls = [call for call in self.run_calls if call["endpoint"] == "error_device"]
        self.assertEqual(len(error_calls), 0)
        
        # Verify transcription is still enabled
        self.assertTrue(config.ENABLE_TRANSCRIPTION_RECEIVE)

    def test_restart_access_speaker_devices_detects_unavailable_device(self):
        """Test that restartAccessSpeakerDevices detects unavailable device."""
        config.SELECTED_SPEAKER_DEVICE = "MissingDevice"
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        
        # Mock device_manager to return empty list
        with patch.object(device_manager, 'getSpeakerDevices', return_value=[]):
            with patch.object(self.controller, 'handleSpeakerDeviceUnavailable') as mock_handle:
                with patch.object(self.controller, 'startThreadingTranscriptionReceiveMessage') as mock_start:
                    self.controller.restartAccessSpeakerDevices()
                    
                    # Verify handleSpeakerDeviceUnavailable was called
                    mock_handle.assert_called_once()
                    
                    # Verify startThreadingTranscriptionReceiveMessage was NOT called
                    mock_start.assert_not_called()

    def test_restart_access_speaker_devices_starts_when_device_available(self):
        """Test that restartAccessSpeakerDevices starts transcription when device is available."""
        config.SELECTED_SPEAKER_DEVICE = "AvailableDevice"
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        config.ENABLE_CHECK_ENERGY_RECEIVE = False
        
        # Mock device_manager to return device in list
        mock_devices = [{"name": "AvailableDevice", "index": 0}]
        with patch.object(device_manager, 'getSpeakerDevices', return_value=mock_devices):
            with patch.object(self.controller, 'handleSpeakerDeviceUnavailable') as mock_handle:
                with patch.object(self.controller, 'startThreadingTranscriptionReceiveMessage') as mock_start:
                    self.controller.restartAccessSpeakerDevices()
                    
                    # Verify handleSpeakerDeviceUnavailable was NOT called
                    mock_handle.assert_not_called()
                    
                    # Verify startThreadingTranscriptionReceiveMessage WAS called
                    mock_start.assert_called_once()

    def test_start_transcription_catches_os_error(self):
        """Test that startTranscriptionReceiveMessage catches OSError from device."""
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        self.controller.device_access_status = True
        
        # Mock model.startSpeakerTranscript to raise OSError
        with patch('controller.model.startSpeakerTranscript', side_effect=OSError("Device not found")):
            self.controller.startTranscriptionReceiveMessage()
        
        # Verify error notification was sent
        error_calls = [call for call in self.run_calls if call["endpoint"] == "error_device"]
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0]["status"], 400)
        self.assertIn("Speaker device error", error_calls[0]["payload"]["message"])
        
        # Verify transcription was disabled
        self.assertFalse(config.ENABLE_TRANSCRIPTION_RECEIVE)

    def test_start_transcription_catches_io_error(self):
        """Test that startTranscriptionReceiveMessage catches IOError from device."""
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        self.controller.device_access_status = True
        
        # Mock model.startSpeakerTranscript to raise IOError
        with patch('controller.model.startSpeakerTranscript', side_effect=IOError("I/O error")):
            self.controller.startTranscriptionReceiveMessage()
        
        # Verify error notification was sent
        error_calls = [call for call in self.run_calls if call["endpoint"] == "error_device"]
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0]["status"], 400)
        
        # Verify transcription was disabled
        self.assertFalse(config.ENABLE_TRANSCRIPTION_RECEIVE)


if __name__ == '__main__':
    unittest.main()
