"""Test for getComputeDeviceList() integration with ZLUDA.

This test verifies that the compute device list generation correctly:
1. Always includes CPU
2. Detects and initializes ZLUDA when available
3. Falls back to native CUDA when ZLUDA not available
4. Maintains correct device order: CPU, CUDA/ZLUDA
5. Handles gracefully when neither CUDA nor ZLUDA available
"""

import sys
import os

# Add src-python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from utils import getComputeDeviceList


def test_compute_device_list_basic():
    """Test that getComputeDeviceList returns at least CPU."""
    devices = getComputeDeviceList()
    
    # Should always have at least one device (CPU)
    assert len(devices) >= 1, "Should have at least CPU device"
    
    # First device should be CPU
    assert devices[0]["device"] == "cpu", "First device should be CPU"
    assert devices[0]["device_index"] == 0, "CPU device index should be 0"
    assert devices[0]["device_name"] == "cpu", "CPU device name should be 'cpu'"
    assert "compute_types" in devices[0], "CPU should have compute_types"
    assert len(devices[0]["compute_types"]) > 0, "CPU should have at least one compute type"
    
    print("✓ Basic test passed: CPU device present")


def test_compute_device_list_structure():
    """Test that all devices have required fields."""
    devices = getComputeDeviceList()
    
    required_fields = ["device", "device_index", "device_name", "compute_types"]
    
    for i, device in enumerate(devices):
        for field in required_fields:
            assert field in device, f"Device {i} missing required field: {field}"
        
        # Verify types
        assert isinstance(device["device"], str), f"Device {i} 'device' should be string"
        assert isinstance(device["device_index"], int), f"Device {i} 'device_index' should be int"
        assert isinstance(device["device_name"], str), f"Device {i} 'device_name' should be string"
        assert isinstance(device["compute_types"], list), f"Device {i} 'compute_types' should be list"
        
        # If ZLUDA device, should have zluda flag
        if "ZLUDA" in device["device_name"]:
            assert "zluda" in device, f"ZLUDA device {i} should have 'zluda' flag"
            assert device["zluda"] is True, f"ZLUDA device {i} 'zluda' flag should be True"
    
    print(f"✓ Structure test passed: All {len(devices)} devices have required fields")


def test_compute_device_list_order():
    """Test that devices are in correct order: CPU, then GPU devices."""
    devices = getComputeDeviceList()
    
    # First device must be CPU
    assert devices[0]["device"] == "cpu", "First device must be CPU"
    
    # All subsequent devices should be CUDA (with or without ZLUDA)
    for i in range(1, len(devices)):
        assert devices[i]["device"] == "cuda", f"Device {i} should be CUDA device"
    
    print(f"✓ Order test passed: CPU first, then {len(devices) - 1} GPU device(s)")


def test_compute_device_list_no_zluda_in_non_zluda_devices():
    """Test that non-ZLUDA devices don't have zluda flag set to True."""
    devices = getComputeDeviceList()
    
    for i, device in enumerate(devices):
        if "ZLUDA" not in device["device_name"]:
            # Non-ZLUDA devices should either not have zluda flag, or it should be False
            if "zluda" in device:
                assert device["zluda"] is not True, f"Non-ZLUDA device {i} should not have zluda=True"
    
    print("✓ ZLUDA flag test passed: Only ZLUDA devices have zluda=True")


def test_compute_device_list_zluda_detection():
    """Test ZLUDA detection and device naming."""
    devices = getComputeDeviceList()
    
    zluda_devices = [d for d in devices if d.get("zluda") is True]
    
    if zluda_devices:
        print(f"✓ ZLUDA detected: {len(zluda_devices)} ZLUDA device(s) found")
        for device in zluda_devices:
            assert "(ZLUDA)" in device["device_name"], "ZLUDA device name should contain '(ZLUDA)'"
            print(f"  - {device['device_name']}")
    else:
        print("✓ No ZLUDA devices detected (expected if ZLUDA not installed)")


def main():
    """Run all tests."""
    print("Testing getComputeDeviceList() integration...\n")
    
    try:
        test_compute_device_list_basic()
        test_compute_device_list_structure()
        test_compute_device_list_order()
        test_compute_device_list_no_zluda_in_non_zluda_devices()
        test_compute_device_list_zluda_detection()
        
        print("\n" + "="*60)
        print("All tests passed!")
        print("="*60)
        
        # Print device list for inspection
        print("\nCurrent compute device list:")
        devices = getComputeDeviceList()
        for i, device in enumerate(devices):
            print(f"{i}. {device['device_name']} ({device['device']}:{device['device_index']})")
            print(f"   Compute types: {', '.join(device['compute_types'][:5])}{'...' if len(device['compute_types']) > 5 else ''}")
            if device.get("zluda"):
                print(f"   ZLUDA: Yes")
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
