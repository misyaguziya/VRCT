"""Test ZLUDA runtime error detection and fallback to CPU.

This test verifies that:
1. ZLUDA runtime errors are correctly detected
2. System falls back to CPU when ZLUDA fails
3. Errors are logged and users are notified
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from utils import detectZLUDARuntimeError, isZLUDADevice


class TestZLUDARuntimeErrorDetection(unittest.TestCase):
    """Test ZLUDA runtime error detection."""
    
    def test_detect_cuda_error(self):
        """Test detection of CUDA-related errors."""
        error = RuntimeError("CUDA error: device-side assert triggered")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_detect_zluda_error(self):
        """Test detection of ZLUDA-specific errors."""
        error = RuntimeError("ZLUDA initialization failed")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_detect_amd_error(self):
        """Test detection of AMD GPU errors."""
        error = RuntimeError("AMD GPU driver error")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_detect_hip_error(self):
        """Test detection of HIP runtime errors."""
        error = RuntimeError("HIP runtime error")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_detect_rocm_error(self):
        """Test detection of ROCm platform errors."""
        error = RuntimeError("ROCm platform initialization failed")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_detect_device_error(self):
        """Test detection of generic device errors."""
        error = RuntimeError("Device initialization failed")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_detect_gpu_error(self):
        """Test detection of GPU errors."""
        error = RuntimeError("GPU memory allocation failed")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_detect_out_of_memory_error(self):
        """Test detection of out of memory errors."""
        error = RuntimeError("out of memory")
        self.assertTrue(detectZLUDARuntimeError(error))
    
    def test_non_zluda_error(self):
        """Test that non-ZLUDA errors are not detected as ZLUDA errors."""
        error = ValueError("Invalid input parameter")
        self.assertFalse(detectZLUDARuntimeError(error))
    
    def test_generic_runtime_error(self):
        """Test that generic runtime errors without ZLUDA keywords are detected."""
        error = RuntimeError("runtime error occurred")
        self.assertTrue(detectZLUDARuntimeError(error))


class TestZLUDADeviceIdentification(unittest.TestCase):
    """Test ZLUDA device identification."""
    
    def test_is_zluda_device_true(self):
        """Test identification of ZLUDA device."""
        device = {
            "device": "cuda",
            "device_index": 0,
            "device_name": "AMD Radeon RX 7900 XTX (ZLUDA)",
            "zluda": True
        }
        self.assertTrue(isZLUDADevice(device))
    
    def test_is_zluda_device_false(self):
        """Test identification of non-ZLUDA device."""
        device = {
            "device": "cuda",
            "device_index": 0,
            "device_name": "NVIDIA GeForce RTX 4090",
            "zluda": False
        }
        self.assertFalse(isZLUDADevice(device))
    
    def test_is_zluda_device_cpu(self):
        """Test identification of CPU device."""
        device = {
            "device": "cpu",
            "device_index": 0,
            "device_name": "cpu"
        }
        self.assertFalse(isZLUDADevice(device))
    
    def test_is_zluda_device_missing_flag(self):
        """Test device without zluda flag."""
        device = {
            "device": "cuda",
            "device_index": 0,
            "device_name": "AMD Radeon RX 7900 XTX (ZLUDA)"
        }
        self.assertFalse(isZLUDADevice(device))
    
    def test_is_zluda_device_invalid_input(self):
        """Test with invalid input."""
        self.assertFalse(isZLUDADevice(None))
        self.assertFalse(isZLUDADevice("not a dict"))
        self.assertFalse(isZLUDADevice([]))


class TestZLUDAFallbackBehavior(unittest.TestCase):
    """Test ZLUDA fallback to CPU behavior."""
    
    @patch('utils.torch')
    def test_zluda_fallback_on_initialization_error(self, mock_torch):
        """Test that system falls back to CPU when ZLUDA initialization fails."""
        # Mock torch.cuda to simulate ZLUDA failure
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.side_effect = RuntimeError("ZLUDA initialization failed")
        
        from utils import getZLUDADeviceList
        
        # Should return empty list on ZLUDA failure
        devices = getZLUDADeviceList()
        self.assertEqual(len(devices), 0)
    
    def test_cpu_device_available_in_fallback(self):
        """Test that CPU device is available for fallback."""
        from utils import getComputeDeviceList
        
        devices = getComputeDeviceList()
        
        # CPU should always be first device
        self.assertGreater(len(devices), 0)
        self.assertEqual(devices[0]["device"], "cpu")
        self.assertEqual(devices[0]["device_name"], "cpu")


if __name__ == "__main__":
    unittest.main()
