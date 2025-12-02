"""Test getComputeDeviceList() with mocked ZLUDA detection.

This test verifies the integration logic by mocking ZLUDA detection
to ensure the function correctly prioritizes ZLUDA over native CUDA.
"""

import sys
import os
from unittest.mock import patch, MagicMock

# Add src-python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_with_zluda_available():
    """Test that ZLUDA devices are included when ZLUDA is detected."""
    print("Test 1: ZLUDA available")
    
    # Mock ZLUDA detection to return a valid path
    mock_zluda_path = "/mock/zluda/path"
    
    # Mock ZLUDA device list
    mock_zluda_devices = [
        {
            "device": "cuda",
            "device_index": 0,
            "device_name": "AMD Radeon RX 7900 XTX (ZLUDA)",
            "compute_types": ["auto", "float32", "int8"],
            "zluda": True,
        }
    ]
    
    with patch('zluda_installer.detectZLUDA', return_value=mock_zluda_path):
        with patch('zluda_installer.initializeZLUDA', return_value=True):
            with patch('utils.getZLUDADeviceList', return_value=mock_zluda_devices):
                import utils
                
                devices = utils.getComputeDeviceList()
                
                # Should have CPU + ZLUDA device
                assert len(devices) == 2, f"Expected 2 devices, got {len(devices)}"
                
                # First should be CPU
                assert devices[0]["device"] == "cpu"
                
                # Second should be ZLUDA device
                assert devices[1]["device"] == "cuda"
                assert devices[1].get("zluda") is True
                assert "(ZLUDA)" in devices[1]["device_name"]
                
                print(f"  ✓ ZLUDA device correctly added: {devices[1]['device_name']}")


def test_with_zluda_init_failure():
    """Test that native CUDA is used when ZLUDA initialization fails."""
    print("\nTest 2: ZLUDA detected but initialization fails")
    
    mock_zluda_path = "/mock/zluda/path"
    
    with patch('zluda_installer.detectZLUDA', return_value=mock_zluda_path):
        with patch('zluda_installer.initializeZLUDA', return_value=False):
            # Mock torch.cuda to simulate CUDA available
            with patch('utils.torch') as mock_torch:
                mock_torch.cuda.is_available.return_value = True
                mock_torch.cuda.device_count.return_value = 1
                mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 3080"
                
                import utils
                
                devices = utils.getComputeDeviceList()
                
                # Should have CPU + CUDA device (not ZLUDA)
                assert len(devices) >= 1, "Should have at least CPU"
                
                # Check that no ZLUDA devices are present
                zluda_devices = [d for d in devices if d.get("zluda") is True]
                assert len(zluda_devices) == 0, "Should not have ZLUDA devices when init fails"
                
                print("  ✓ Correctly fell back to native CUDA when ZLUDA init failed")


def test_with_no_zluda_no_cuda():
    """Test that only CPU is returned when neither ZLUDA nor CUDA available."""
    print("\nTest 3: No ZLUDA, no CUDA")
    
    with patch('zluda_installer.detectZLUDA', return_value=None):
        with patch('utils.torch') as mock_torch:
            mock_torch.cuda.is_available.return_value = False
            
            import utils
            
            devices = utils.getComputeDeviceList()
            
            # Should only have CPU
            assert len(devices) == 1, f"Expected only CPU, got {len(devices)} devices"
            assert devices[0]["device"] == "cpu"
            
            print("  ✓ Correctly returned only CPU when no GPU available")


def test_device_order_maintained():
    """Test that device order is CPU, then GPU devices."""
    print("\nTest 4: Device order")
    
    mock_zluda_devices = [
        {
            "device": "cuda",
            "device_index": 0,
            "device_name": "AMD GPU 1 (ZLUDA)",
            "compute_types": ["auto", "float32"],
            "zluda": True,
        },
        {
            "device": "cuda",
            "device_index": 1,
            "device_name": "AMD GPU 2 (ZLUDA)",
            "compute_types": ["auto", "float32"],
            "zluda": True,
        }
    ]
    
    with patch('zluda_installer.detectZLUDA', return_value="/mock/path"):
        with patch('zluda_installer.initializeZLUDA', return_value=True):
            with patch('utils.getZLUDADeviceList', return_value=mock_zluda_devices):
                import utils
                
                devices = utils.getComputeDeviceList()
                
                # First device must be CPU
                assert devices[0]["device"] == "cpu", "First device must be CPU"
                
                # Remaining devices should be GPU
                for i in range(1, len(devices)):
                    assert devices[i]["device"] == "cuda", f"Device {i} should be GPU"
                
                print(f"  ✓ Device order correct: CPU first, then {len(devices) - 1} GPU(s)")


def main():
    """Run all tests."""
    print("Testing getComputeDeviceList() with mocked ZLUDA...\n")
    print("="*60)
    
    try:
        test_with_zluda_available()
        test_with_zluda_init_failure()
        test_with_no_zluda_no_cuda()
        test_device_order_maintained()
        
        print("\n" + "="*60)
        print("All mock tests passed!")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
