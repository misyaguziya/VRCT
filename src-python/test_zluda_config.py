"""Test ZLUDA configuration properties in config.py

This test verifies that ZLUDA_ENABLED and ZLUDA_PATH properties are correctly
integrated into the configuration system by checking the source code directly.
"""

import re

def test_zluda_properties_in_source():
    """Test that ZLUDA properties are defined in config.py source code."""
    
    with open('config.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for ZLUDA_ENABLED property definition
    zluda_enabled_pattern = r"ZLUDA_ENABLED\s*=\s*ManagedProperty\s*\(\s*['\"]ZLUDA_ENABLED['\"].*serialize\s*=\s*False"
    if not re.search(zluda_enabled_pattern, content, re.DOTALL):
        raise AssertionError("ZLUDA_ENABLED property not found or incorrectly configured")
    print("✓ ZLUDA_ENABLED property defined with serialize=False")
    
    # Check for ZLUDA_PATH property definition
    zluda_path_pattern = r"ZLUDA_PATH\s*=\s*ManagedProperty\s*\(\s*['\"]ZLUDA_PATH['\"].*serialize\s*=\s*True"
    if not re.search(zluda_path_pattern, content, re.DOTALL):
        raise AssertionError("ZLUDA_PATH property not found or incorrectly configured")
    print("✓ ZLUDA_PATH property defined with serialize=True")
    
    # Check for ZLUDA_ENABLED initialization
    if "self._ZLUDA_ENABLED = False" not in content:
        raise AssertionError("ZLUDA_ENABLED initialization not found")
    print("✓ ZLUDA_ENABLED initialized to False")
    
    # Check for ZLUDA_PATH initialization
    if "self._ZLUDA_PATH = None" not in content:
        raise AssertionError("ZLUDA_PATH initialization not found")
    print("✓ ZLUDA_PATH initialized to None")
    
    # Check that ZLUDA properties are in the correct section
    if "# --- ZLUDA configuration ---" not in content:
        raise AssertionError("ZLUDA configuration section comment not found")
    print("✓ ZLUDA configuration section properly commented")
    
    # Verify type validation for ZLUDA_ENABLED
    if "type_=bool" not in re.search(r"ZLUDA_ENABLED\s*=\s*ManagedProperty\([^)]+\)", content).group():
        raise AssertionError("ZLUDA_ENABLED missing type_=bool validation")
    print("✓ ZLUDA_ENABLED has type_=bool validation")
    
    # Verify type validation for ZLUDA_PATH
    if "type_=str" not in re.search(r"ZLUDA_PATH\s*=\s*ManagedProperty\([^)]+\)", content).group():
        raise AssertionError("ZLUDA_PATH missing type_=str validation")
    print("✓ ZLUDA_PATH has type_=str validation")

if __name__ == "__main__":
    print("Testing ZLUDA configuration properties in source code...")
    print()
    
    try:
        test_zluda_properties_in_source()
        
        print()
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print()
        print("Summary:")
        print("- ZLUDA_ENABLED property added with serialize=False")
        print("- ZLUDA_PATH property added with serialize=True")
        print("- Both properties initialized with correct defaults")
        print("- Type validation configured for both properties")
        print("- Properties integrate with existing config system")
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"Test failed: {e}")
        print("=" * 60)
        import sys
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"Unexpected error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
