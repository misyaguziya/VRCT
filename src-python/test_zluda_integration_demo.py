"""Integration demonstration for ZLUDA device enumeration.

This script demonstrates how getZLUDADeviceList() would be used in the
actual application flow with ZLUDA detection and initialization.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def demo_zluda_workflow():
    """Demonstrate the complete ZLUDA device enumeration workflow."""
    print("=" * 70)
    print("ZLUDA Device Enumeration Integration Demo")
    print("=" * 70)
    
    # Simulate ZLUDA being installed
    print("\nScenario: ZLUDA is installed with 2 AMD GPUs")
    print("-" * 70)
    
    # Mock ZLUDA detection
    mock_detect_zluda = Mock(return_value="/path/to/zluda")
    mock_initialize_zluda = Mock(return_value=True)
    
    # Mock torch with 2 AMD GPUs
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.device_count.return_value = 2
    
    def mock_get_device_name(index):
        names = ["AMD Radeon RX 7900 XTX", "AMD Radeon RX 6800 XT"]
        return names[index]
    
    mock_torch.cuda.get_device_name.side_effect = mock_get_device_name
    
    mock_get_supported_compute_types = Mock(return_value=["float32", "int8", "int8_float32"])
    
    with patch('zluda_installer.detectZLUDA', mock_detect_zluda):
        with patch('zluda_installer.initializeZLUDA', mock_initialize_zluda):
            with patch('utils.torch', mock_torch):
                with patch('utils.get_supported_compute_types', mock_get_supported_compute_types):
                    from zluda_installer import detectZLUDA, initializeZLUDA
                    from utils import getZLUDADeviceList
                    
                    # Step 1: Detect ZLUDA
                    print("\n1. Detecting ZLUDA...")
                    zluda_path = detectZLUDA()
                    print(f"   ✓ ZLUDA detected at: {zluda_path}")
                    
                    # Step 2: Initialize ZLUDA
                    print("\n2. Initializing ZLUDA...")
                    if initializeZLUDA(zluda_path):
                        print("   ✓ ZLUDA initialized successfully")
                    
                    # Step 3: Enumerate ZLUDA devices
                    print("\n3. Enumerating ZLUDA devices...")
                    zluda_devices = getZLUDADeviceList()
                    print(f"   ✓ Found {len(zluda_devices)} ZLUDA device(s)")
                    
                    # Step 4: Display device information
                    print("\n4. Device Information:")
                    for i, device in enumerate(zluda_devices):
                        print(f"\n   Device {i}:")
                        print(f"   ├─ Name: {device['device_name']}")
                        print(f"   ├─ Type: {device['device']}")
                        print(f"   ├─ Index: {device['device_index']}")
                        print(f"   ├─ ZLUDA: {device['zluda']}")
                        print(f"   └─ Compute Types: {', '.join(device['compute_types'])}")
                    
                    # Step 5: Verify properties
                    print("\n5. Verification:")
                    all_valid = True
                    
                    for device in zluda_devices:
                        # Check ZLUDA flag
                        if device.get('zluda') != True:
                            print(f"   ✗ Device missing ZLUDA flag")
                            all_valid = False
                        
                        # Check device name format
                        if '(ZLUDA)' not in device.get('device_name', ''):
                            print(f"   ✗ Device name missing (ZLUDA) suffix")
                            all_valid = False
                        
                        # Check device type
                        if device.get('device') != 'cuda':
                            print(f"   ✗ Device type should be 'cuda'")
                            all_valid = False
                    
                    if all_valid:
                        print("   ✓ All devices have correct properties")
                        print("   ✓ Requirements 2.4 satisfied: ZLUDA devices detected")
                        print("   ✓ Requirements 4.2 satisfied: AMD GPU names included")
                    
                    return all_valid


def demo_no_zluda():
    """Demonstrate behavior when ZLUDA is not installed."""
    print("\n" + "=" * 70)
    print("Scenario: ZLUDA is NOT installed")
    print("-" * 70)
    
    # Mock ZLUDA not being detected
    mock_detect_zluda = Mock(return_value=None)
    
    with patch('zluda_installer.detectZLUDA', mock_detect_zluda):
        with patch('utils.torch', None):
            from zluda_installer import detectZLUDA
            from utils import getZLUDADeviceList
            
            print("\n1. Detecting ZLUDA...")
            zluda_path = detectZLUDA()
            if not zluda_path:
                print("   ✓ ZLUDA not detected (expected)")
            
            print("\n2. Attempting to enumerate ZLUDA devices...")
            zluda_devices = getZLUDADeviceList()
            
            if len(zluda_devices) == 0:
                print("   ✓ Returns empty list (expected)")
                print("   ✓ Requirements 7.3 satisfied: No ZLUDA devices when not installed")
                return True
            else:
                print(f"   ✗ Expected empty list, got {len(zluda_devices)} devices")
                return False


def main():
    """Run integration demos."""
    print("\nZLUDA Device Enumeration Integration Demonstration")
    print("=" * 70)
    
    try:
        result1 = demo_zluda_workflow()
        result2 = demo_no_zluda()
        
        print("\n" + "=" * 70)
        if result1 and result2:
            print("✓ All integration scenarios PASSED")
            print("\nImplementation Summary:")
            print("  • getZLUDADeviceList() correctly enumerates AMD GPUs via ZLUDA")
            print("  • Device names include '(ZLUDA)' suffix")
            print("  • ZLUDA flag is set to True for all devices")
            print("  • Returns empty list when ZLUDA not available")
            print("  • Satisfies Requirements 2.4, 4.2, and 7.3")
        else:
            print("✗ Some integration scenarios FAILED")
        print("=" * 70)
        
        return 0 if (result1 and result2) else 1
        
    except Exception as e:
        print(f"\n✗ Demo failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
