"""Test automatic threshold calculation for speaker input devices.

This test verifies that automatic threshold calculation works correctly for
speaker devices, including both loopback and regular input devices.

Requirements tested: 5.5
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from models.transcription.transcription_recorder import SelectedSpeakerEnergyAndAudioRecorder


class TestSpeakerAutomaticThreshold(unittest.TestCase):
    """Test automatic threshold calculation for speaker devices."""

    def test_automatic_threshold_enabled_for_loopback_device(self):
        """Test that automatic threshold can be enabled for loopback devices.
        
        Verifies that when dynamic_energy_threshold is True, the recorder
        properly initializes with automatic threshold enabled for loopback devices.
        """
        # Create a mock loopback device
        loopback_device = {
            'index': 1,
            'name': 'Speakers (Loopback)',
            'defaultSampleRate': 48000,
            'maxInputChannels': 2,
            'isLoopbackDevice': True
        }
        
        # Mock the Microphone class to avoid actual audio device access
        with patch('models.transcription.transcription_recorder.Microphone') as mock_mic:
            mock_source = Mock()
            mock_mic.return_value = mock_source
            
            # Create recorder with automatic threshold enabled
            recorder = SelectedSpeakerEnergyAndAudioRecorder(
                device=loopback_device,
                energy_threshold=300,
                dynamic_energy_threshold=True,  # Automatic threshold enabled
                phrase_time_limit=3,
                phrase_timeout=1,
                record_timeout=5
            )
            
            # Verify the recorder was created with automatic threshold enabled
            self.assertTrue(recorder.recorder.dynamic_energy_threshold)
            self.assertEqual(recorder.recorder.energy_threshold, 300)

    def test_automatic_threshold_enabled_for_input_device(self):
        """Test that automatic threshold can be enabled for regular input devices.
        
        Verifies that when dynamic_energy_threshold is True, the recorder
        properly initializes with automatic threshold enabled for non-loopback
        input devices (e.g., virtual audio cables).
        """
        # Create a mock regular input device (not loopback)
        input_device = {
            'index': 5,
            'name': 'VB-Audio Virtual Cable',
            'defaultSampleRate': 48000,
            'maxInputChannels': 2,
            'isLoopbackDevice': False  # Regular input device
        }
        
        # Mock the Microphone class to avoid actual audio device access
        with patch('models.transcription.transcription_recorder.Microphone') as mock_mic:
            mock_source = Mock()
            mock_mic.return_value = mock_source
            
            # Create recorder with automatic threshold enabled
            recorder = SelectedSpeakerEnergyAndAudioRecorder(
                device=input_device,
                energy_threshold=300,
                dynamic_energy_threshold=True,  # Automatic threshold enabled
                phrase_time_limit=3,
                phrase_timeout=1,
                record_timeout=5
            )
            
            # Verify the recorder was created with automatic threshold enabled
            self.assertTrue(recorder.recorder.dynamic_energy_threshold)
            self.assertEqual(recorder.recorder.energy_threshold, 300)

    def test_automatic_threshold_disabled_for_input_device(self):
        """Test that automatic threshold can be disabled for input devices.
        
        Verifies that when dynamic_energy_threshold is False, the recorder
        uses the manual threshold value for input devices.
        """
        # Create a mock regular input device
        input_device = {
            'index': 5,
            'name': 'VB-Audio Virtual Cable',
            'defaultSampleRate': 48000,
            'maxInputChannels': 2,
            'isLoopbackDevice': False
        }
        
        # Mock the Microphone class
        with patch('models.transcription.transcription_recorder.Microphone') as mock_mic:
            mock_source = Mock()
            mock_mic.return_value = mock_source
            
            # Create recorder with automatic threshold disabled
            recorder = SelectedSpeakerEnergyAndAudioRecorder(
                device=input_device,
                energy_threshold=500,
                dynamic_energy_threshold=False,  # Automatic threshold disabled
                phrase_time_limit=3,
                phrase_timeout=1,
                record_timeout=5
            )
            
            # Verify the recorder uses manual threshold
            self.assertFalse(recorder.recorder.dynamic_energy_threshold)
            self.assertEqual(recorder.recorder.energy_threshold, 500)

    def test_automatic_threshold_with_various_device_types(self):
        """Test automatic threshold with various input device configurations.
        
        Verifies that automatic threshold works correctly across different
        device types: loopback, virtual cables, streaming software outputs, etc.
        """
        # Test various device configurations
        test_devices = [
            {
                'index': 1,
                'name': 'Speakers (Loopback)',
                'defaultSampleRate': 48000,
                'maxInputChannels': 2,
                'isLoopbackDevice': True
            },
            {
                'index': 5,
                'name': 'VB-Audio Virtual Cable',
                'defaultSampleRate': 48000,
                'maxInputChannels': 2,
                'isLoopbackDevice': False
            },
            {
                'index': 7,
                'name': 'OBS Virtual Camera Audio',
                'defaultSampleRate': 44100,
                'maxInputChannels': 2,
                'isLoopbackDevice': False
            },
            {
                'index': 9,
                'name': 'Voicemeeter Output',
                'defaultSampleRate': 48000,
                'maxInputChannels': 8,
                'isLoopbackDevice': False
            }
        ]
        
        # Mock the Microphone class
        with patch('models.transcription.transcription_recorder.Microphone') as mock_mic:
            mock_source = Mock()
            mock_mic.return_value = mock_source
            
            for device in test_devices:
                with self.subTest(device=device['name']):
                    # Create recorder with automatic threshold enabled
                    recorder = SelectedSpeakerEnergyAndAudioRecorder(
                        device=device,
                        energy_threshold=300,
                        dynamic_energy_threshold=True,
                        phrase_time_limit=3,
                        phrase_timeout=1,
                        record_timeout=5
                    )
                    
                    # Verify automatic threshold is enabled for all device types
                    self.assertTrue(
                        recorder.recorder.dynamic_energy_threshold,
                        f"Automatic threshold should be enabled for {device['name']}"
                    )

    def test_threshold_value_propagation(self):
        """Test that threshold values are correctly propagated to the recorder.
        
        Verifies that both the initial threshold value and the automatic
        threshold flag are correctly passed to the underlying speech_recognition
        Recognizer object.
        """
        input_device = {
            'index': 5,
            'name': 'Test Input Device',
            'defaultSampleRate': 48000,
            'maxInputChannels': 2,
            'isLoopbackDevice': False
        }
        
        test_cases = [
            (100, True),   # Low threshold, automatic
            (300, True),   # Medium threshold, automatic
            (500, False),  # High threshold, manual
            (1000, False), # Very high threshold, manual
        ]
        
        with patch('models.transcription.transcription_recorder.Microphone') as mock_mic:
            mock_source = Mock()
            mock_mic.return_value = mock_source
            
            for threshold, automatic in test_cases:
                with self.subTest(threshold=threshold, automatic=automatic):
                    recorder = SelectedSpeakerEnergyAndAudioRecorder(
                        device=input_device,
                        energy_threshold=threshold,
                        dynamic_energy_threshold=automatic,
                        phrase_time_limit=3,
                        phrase_timeout=1,
                        record_timeout=5
                    )
                    
                    # Verify values are correctly set
                    self.assertEqual(recorder.recorder.energy_threshold, threshold)
                    self.assertEqual(recorder.recorder.dynamic_energy_threshold, automatic)


if __name__ == '__main__':
    unittest.main()
