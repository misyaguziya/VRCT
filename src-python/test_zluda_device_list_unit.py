"""Unit tests for getZLUDADeviceList() function.

This test verifies the function logic without requiring actual ZLUDA installation.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_zluda_device_list_no_torch():
    """Test getZLUDADeviceList when torch is not available."""
    print("\n1. Testing with torch=None...")
    
    with patch('utils.torch', None):
        from utils import getZLUDADeviceList
        devices = getZLUDADeviceList()
        
        assert devices == [], f"Expected empty list, got {devices}"
        print("   ✓ Returns empty list when torch is None")


def test_zluda_device_list_no_cuda():
    """Test getZLUDADeviceList when CUDA is not available."""
    print("\n2. Testing with CUDA not available...")
    
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    
    with patch('utils.torch', mock_torch):
        from utils import getZLUDADeviceList
        devices = getZLUDADeviceList()
        
        assert devices == [], f"Expected empty list, got {devices}"
        print("   ✓ Returns empty list when CUDA not available")


def test_zluda_device_list_single_device():
    """Test getZLUDADeviceList with a single AMD GPU."""
    print("\n3. Testing with single AMD GPU...")
    
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 1
    mock_torch.cuda.get_device_name.return_value = "AMD Radeon RX 7900 XTX"
    
    mock_get_supported_compute_types = Mock(return_value=["float32", "int8", "int8_float32"])
    
    with patch('utils.torch', mock_torch):
        with patch('utils.get_supported_compute_types', mock_get_supported_compute_types):
            from utils import getZLUDADeviceList
            devices = getZLUDADeviceList()
            
            assert len(devices) == 1, f"Expected 1 device, got {len(devices)}"
            
            device = devices[0]
            assert device['device'] == 'cuda', f"Expected device='cuda', got {device['device']}"
            assert device['device_index'] == 0, f"Expected device_index=0, got {device['device_index']}"
            assert '(ZLUDA)' in device['device_name'], f"Expected '(ZLUDA)' in name, got {device['device_name']}"
            assert 'AMD Radeon RX 7900 XTX' in device['device_name'], f"Expected GPU name in device_name"
            assert device['zluda'] == True, f"Expected zluda=True, got {device['zluda']}"
            assert isinstance(device['compute_types'], list), f"Expected list for compute_types"
            assert len(device['compute_types']) > 0, f"Expected non-empty compute_types"
            assert 'auto' in device['compute_types'], f"Expected 'auto' in compute_types"
            
            print(f"   ✓ Device name: {device['device_name']}")
            print(f"   ✓ Compute types: {device['compute_types']}")
            print("   ✓ All properties valid for single device")


def test_zluda_device_list_multiple_devices():
    """Test getZLUDADeviceList with multiple AMD GPUs."""
    print("\n4. Testing with multiple AMD GPUs...")
    
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 2
    
    def mock_get_device_name(index):
        names = ["AMD Radeon RX 7900 XTX", "AMD Radeon RX 6800 XT"]
        return names[index]
    
    mock_torch.cuda.get_device_name.side_effect = mock_get_device_name
    
    mock_get_supported_compute_types = Mock(return_value=["float32", "int8"])
    
    with patch('utils.torch', mock_torch):
        with patch('utils.get_supported_compute_types', mock_get_supported_compute_types):
            from utils import getZLUDADeviceList
            devices = getZLUDADeviceList()
            
            assert len(devices) == 2, f"Expected 2 devices, got {len(devices)}"
            
            for i, device in enumerate(devices):
                assert device['device'] == 'cuda', f"Device {i}: Expected device='cuda'"
                assert device['device_index'] == i, f"Device {i}: Expected device_index={i}"
                assert '(ZLUDA)' in device['device_name'], f"Device {i}: Expected '(ZLUDA)' in name"
                assert device['zluda'] == True, f"Device {i}: Expected zluda=True"
                print(f"   ✓ Device {i}: {device['device_name']}")
            
            print("   ✓ All properties valid for multiple devices")


def test_zluda_device_list_compute_type_filtering():
    """Test that compute types are filtered appropriately for AMD GPUs."""
    print("\n5. Testing compute type filtering...")
    
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 1
    mock_torch.cuda.get_device_name.return_value = "AMD Radeon RX 7900 XTX"
    
    # Simulate ctranslate2 returning many compute types
    mock_get_supported_compute_types = Mock(return_value=[
        "float32", "float16", "int8", "int8_float32", "int8_float16", "bfloat16", "int8_bfloat16"
    ])
    
    with patch('utils.torch', mock_torch):
        with patch('utils.get_supported_compute_types', mock_get_supported_compute_types):
            from utils import getZLUDADeviceList
            devices = getZLUDADeviceList()
            
            assert len(devices) == 1, f"Expected 1 device"
            
            device = devices[0]
            compute_types = device['compute_types']
            
            # Should filter to safe types for AMD
            assert 'auto' in compute_types, "Expected 'auto' in compute_types"
            assert 'float32' in compute_types, "Expected 'float32' in compute_types"
            
            # Should not include potentially unsupported types
            unsafe_types = ['float16', 'bfloat16', 'int8_float16', 'int8_bfloat16']
            for unsafe_type in unsafe_types:
                assert unsafe_type not in compute_types, f"Should not include {unsafe_type}"
            
            print(f"   ✓ Filtered compute types: {compute_types}")
            print("   ✓ Compute type filtering works correctly")


def test_zluda_device_list_error_handling():
    """Test error handling in getZLUDADeviceList."""
    print("\n6. Testing error handling...")
    
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 2
    
    # First device succeeds, second device throws exception
    def mock_get_device_name(index):
        if index == 0:
            return "AMD Radeon RX 7900 XTX"
        else:
            raise RuntimeError("Device error")
    
    mock_torch.cuda.get_device_name.side_effect = mock_get_device_name
    
    mock_get_supported_compute_types = Mock(return_value=["float32"])
    
    with patch('utils.torch', mock_torch):
        with patch('utils.get_supported_compute_types', mock_get_supported_compute_types):
            from utils import getZLUDADeviceList
            devices = getZLUDADeviceList()
            
            # Should return the one successful device
            assert len(devices) == 1, f"Expected 1 device (error on second), got {len(devices)}"
            assert devices[0]['device_index'] == 0, "Expected first device to succeed"
            
            print("   ✓ Handles device enumeration errors gracefully")


def main():
    """Run all unit tests."""
    print("=" * 70)
    print("Unit Tests for getZLUDADeviceList()")
    print("=" * 70)
    
    try:
        test_zluda_device_list_no_torch()
        test_zluda_device_list_no_cuda()
        test_zluda_device_list_single_device()
        test_zluda_device_list_multiple_devices()
        test_zluda_device_list_compute_type_filtering()
        test_zluda_device_list_error_handling()
        
        print("\n" + "=" * 70)
        print("✓ All unit tests PASSED")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
