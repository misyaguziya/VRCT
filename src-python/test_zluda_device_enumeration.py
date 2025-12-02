"""Test script for ZLUDA device enumeration functionality.

This script tests the getZLUDADeviceList() function to ensure it properly
enumerates AMD GPUs through ZLUDA with correct formatting and flags.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zluda_installer import detectZLUDA, initializeZLUDA
from utils import getZLUDADeviceList


def test_zluda_device_enumeration():
    """Test ZLUDA device enumeration."""
    print("=" * 70)
    print("Testing ZLUDA Device Enumeration")
    print("=" * 70)
    
    # Step 1: Detect ZLUDA
    print("\n1. Detecting ZLUDA installation...")
    zluda_path = detectZLUDA()
    
    if not zluda_path:
        print("   ✗ ZLUDA not detected")
        print("   This test requires ZLUDA to be installed.")
        print("   Skipping ZLUDA device enumeration test.")
        return False
    
    print(f"   ✓ ZLUDA detected at: {zluda_path}")
    
    # Step 2: Initialize ZLUDA
    print("\n2. Initializing ZLUDA...")
    if not initializeZLUDA(zluda_path):
        print("   ✗ ZLUDA initialization failed")
        return False
    
    print("   ✓ ZLUDA initialized successfully")
    
    # Step 3: Enumerate ZLUDA devices
    print("\n3. Enumerating ZLUDA devices...")
    zluda_devices = getZLUDADeviceList()
    
    if not zluda_devices:
        print("   ⚠ No ZLUDA devices found")
        print("   This may be expected if no AMD GPUs are present.")
        return True  # Not a failure - just no AMD GPUs
    
    print(f"   ✓ Found {len(zluda_devices)} ZLUDA device(s)")
    
    # Step 4: Validate device properties
    print("\n4. Validating device properties...")
    all_valid = True
    
    for i, device in enumerate(zluda_devices):
        print(f"\n   Device {i}:")
        print(f"   - Name: {device.get('device_name', 'N/A')}")
        print(f"   - Device: {device.get('device', 'N/A')}")
        print(f"   - Device Index: {device.get('device_index', 'N/A')}")
        print(f"   - ZLUDA Flag: {device.get('zluda', 'N/A')}")
        print(f"   - Compute Types: {device.get('compute_types', [])}")
        
        # Validate required fields
        required_fields = ['device', 'device_index', 'device_name', 'compute_types', 'zluda']
        for field in required_fields:
            if field not in device:
                print(f"   ✗ Missing required field: {field}")
                all_valid = False
        
        # Validate device type is "cuda"
        if device.get('device') != 'cuda':
            print(f"   ✗ Device type should be 'cuda', got: {device.get('device')}")
            all_valid = False
        
        # Validate ZLUDA flag is True
        if device.get('zluda') != True:
            print(f"   ✗ ZLUDA flag should be True, got: {device.get('zluda')}")
            all_valid = False
        
        # Validate device name contains "(ZLUDA)"
        device_name = device.get('device_name', '')
        if '(ZLUDA)' not in device_name:
            print(f"   ✗ Device name should contain '(ZLUDA)', got: {device_name}")
            all_valid = False
        
        # Validate compute types is a non-empty list
        compute_types = device.get('compute_types', [])
        if not isinstance(compute_types, list) or len(compute_types) == 0:
            print(f"   ✗ Compute types should be a non-empty list, got: {compute_types}")
            all_valid = False
        
        # Validate device_index is an integer
        device_index = device.get('device_index')
        if not isinstance(device_index, int):
            print(f"   ✗ Device index should be an integer, got: {type(device_index)}")
            all_valid = False
    
    if all_valid:
        print("\n   ✓ All device properties are valid")
    else:
        print("\n   ✗ Some device properties are invalid")
    
    return all_valid


def main():
    """Main test function."""
    print("\nZLUDA Device Enumeration Test")
    print("=" * 70)
    
    try:
        success = test_zluda_device_enumeration()
        
        print("\n" + "=" * 70)
        if success:
            print("✓ ZLUDA device enumeration test PASSED")
        else:
            print("✗ ZLUDA device enumeration test FAILED")
        print("=" * 70)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
