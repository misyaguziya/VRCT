"""Manual test for ZLUDA detection functionality."""

import os
import sys
import tempfile
from pathlib import Path

# Add src-python to path
sys.path.insert(0, str(Path(__file__).parent))

from zluda_installer import detectZLUDA, initializeZLUDA, _isValidZLUDAPath, _findInSystemPath


def test_is_valid_zluda_path():
    """Test ZLUDA path validation."""
    print("Testing _isValidZLUDAPath...")
    
    # Test with non-existent path
    result = _isValidZLUDAPath("/nonexistent/path")
    assert result is False, "Non-existent path should be invalid"
    print("  ✓ Non-existent path correctly rejected")
    
    # Test with temporary directory (no ZLUDA files)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _isValidZLUDAPath(tmpdir)
        assert result is False, "Empty directory should be invalid"
        print("  ✓ Empty directory correctly rejected")
        
        # Create mock ZLUDA installation
        if sys.platform == 'win32':
            Path(tmpdir, "nvcuda.dll").touch()
        else:
            Path(tmpdir, "libcuda.so").touch()
        
        result = _isValidZLUDAPath(tmpdir)
        assert result is True, "Directory with ZLUDA files should be valid"
        print("  ✓ Valid ZLUDA directory correctly accepted")


def test_find_in_system_path():
    """Test finding files in system PATH."""
    print("\nTesting _findInSystemPath...")
    
    # Test with a file that definitely doesn't exist
    result = _findInSystemPath("nonexistent_file_12345.xyz")
    assert result is None, "Non-existent file should not be found"
    print("  ✓ Non-existent file correctly returns None")
    
    # Test with a common system file (python.exe on Windows, python on Linux)
    if sys.platform == 'win32':
        test_file = "python.exe"
    else:
        test_file = "python"
    
    result = _findInSystemPath(test_file)
    if result:
        print(f"  ✓ Found {test_file} in PATH at: {result}")
    else:
        print(f"  ℹ {test_file} not found in PATH (this is okay)")


def test_initialize_zluda():
    """Test ZLUDA initialization."""
    print("\nTesting initializeZLUDA...")
    
    # Test with invalid path
    result = initializeZLUDA("/nonexistent/path")
    assert result is False, "Invalid path should fail initialization"
    print("  ✓ Invalid path correctly fails")
    
    # Test with valid mock ZLUDA installation
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock ZLUDA files
        if sys.platform == 'win32':
            Path(tmpdir, "nvcuda.dll").touch()
        else:
            Path(tmpdir, "libcuda.so").touch()
        
        # Save original environment
        original_cuda_path = os.environ.get('CUDA_PATH')
        original_path = os.environ.get('PATH')
        original_ld_path = os.environ.get('LD_LIBRARY_PATH')
        
        try:
            result = initializeZLUDA(tmpdir)
            assert result is True, "Valid path should succeed initialization"
            print("  ✓ Valid path correctly initializes")
            
            # Check environment variables
            assert os.environ.get('CUDA_PATH') == tmpdir, "CUDA_PATH should be set"
            print(f"  ✓ CUDA_PATH set to: {os.environ.get('CUDA_PATH')}")
            
            if sys.platform == 'win32':
                assert tmpdir in os.environ.get('PATH', ''), "PATH should include ZLUDA"
                print("  ✓ PATH includes ZLUDA directory")
            else:
                assert tmpdir in os.environ.get('LD_LIBRARY_PATH', ''), "LD_LIBRARY_PATH should include ZLUDA"
                print("  ✓ LD_LIBRARY_PATH includes ZLUDA directory")
        finally:
            # Restore environment
            if original_cuda_path:
                os.environ['CUDA_PATH'] = original_cuda_path
            else:
                os.environ.pop('CUDA_PATH', None)
            
            if original_path:
                os.environ['PATH'] = original_path
            
            if original_ld_path:
                os.environ['LD_LIBRARY_PATH'] = original_ld_path
            else:
                os.environ.pop('LD_LIBRARY_PATH', None)


def test_detect_zluda_with_env():
    """Test ZLUDA detection via environment variable."""
    print("\nTesting detectZLUDA with environment variable...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock ZLUDA installation
        if sys.platform == 'win32':
            Path(tmpdir, "nvcuda.dll").touch()
        else:
            Path(tmpdir, "libcuda.so").touch()
        
        # Save original environment
        original_env = os.environ.get('ZLUDA_PATH')
        
        try:
            os.environ['ZLUDA_PATH'] = tmpdir
            
            result = detectZLUDA()
            assert result == tmpdir, f"Should detect ZLUDA at {tmpdir}"
            print(f"  ✓ ZLUDA correctly detected via ZLUDA_PATH: {result}")
        finally:
            # Restore environment
            if original_env:
                os.environ['ZLUDA_PATH'] = original_env
            else:
                os.environ.pop('ZLUDA_PATH', None)


def main():
    """Run all manual tests."""
    print("=" * 60)
    print("ZLUDA Detection Module - Manual Tests")
    print("=" * 60)
    
    try:
        test_is_valid_zluda_path()
        test_find_in_system_path()
        test_initialize_zluda()
        test_detect_zluda_with_env()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
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
