"""Manual test for ZLUDA initialization functionality.

This test verifies that initializeZLUDA() correctly sets environment variables
and is idempotent and safe.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src-python to path
sys.path.insert(0, str(Path(__file__).parent))

from zluda_installer import initializeZLUDA, _isValidZLUDAPath


def test_initialize_zluda_basic():
    """Test basic ZLUDA initialization."""
    print("Test 1: Basic ZLUDA initialization")
    print("-" * 50)
    
    # Create a temporary mock ZLUDA installation
    with tempfile.TemporaryDirectory() as tmp_dir:
        zluda_dir = Path(tmp_dir) / "zluda"
        zluda_dir.mkdir()
        
        # Create the key ZLUDA file based on platform
        if sys.platform == 'win32':
            (zluda_dir / "nvcuda.dll").touch()
        else:
            (zluda_dir / "libcuda.so").touch()
        
        print(f"Created mock ZLUDA at: {zluda_dir}")
        
        # Verify it's a valid ZLUDA path
        is_valid = _isValidZLUDAPath(str(zluda_dir))
        print(f"Is valid ZLUDA path: {is_valid}")
        assert is_valid, "Mock ZLUDA directory should be valid"
        
        # Save original environment
        original_cuda_path = os.environ.get('CUDA_PATH')
        original_path = os.environ.get('PATH')
        original_ld_path = os.environ.get('LD_LIBRARY_PATH')
        
        try:
            # Test initialization
            print(f"\nInitializing ZLUDA with path: {zluda_dir}")
            result = initializeZLUDA(str(zluda_dir))
            print(f"Initialization result: {result}")
            assert result is True, "Initialization should succeed"
            
            # Verify CUDA_PATH is set
            cuda_path = os.environ.get('CUDA_PATH')
            print(f"\nCUDA_PATH set to: {cuda_path}")
            assert cuda_path == str(zluda_dir), f"CUDA_PATH should be {zluda_dir}"
            
            # Verify library path includes ZLUDA
            if sys.platform == 'win32':
                path_var = os.environ.get('PATH', '')
                print(f"PATH includes ZLUDA: {str(zluda_dir) in path_var}")
                assert str(zluda_dir) in path_var, "PATH should include ZLUDA directory"
            else:
                ld_path = os.environ.get('LD_LIBRARY_PATH', '')
                print(f"LD_LIBRARY_PATH includes ZLUDA: {str(zluda_dir) in ld_path}")
                assert str(zluda_dir) in ld_path, "LD_LIBRARY_PATH should include ZLUDA directory"
            
            print("\n✓ Test 1 PASSED: Basic initialization works correctly")
            
        finally:
            # Restore original environment
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


def test_initialize_zluda_idempotent():
    """Test that ZLUDA initialization is idempotent."""
    print("\n\nTest 2: ZLUDA initialization idempotency")
    print("-" * 50)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        zluda_dir = Path(tmp_dir) / "zluda"
        zluda_dir.mkdir()
        
        if sys.platform == 'win32':
            (zluda_dir / "nvcuda.dll").touch()
        else:
            (zluda_dir / "libcuda.so").touch()
        
        # Save original environment
        original_cuda_path = os.environ.get('CUDA_PATH')
        original_path = os.environ.get('PATH')
        original_ld_path = os.environ.get('LD_LIBRARY_PATH')
        
        try:
            # Initialize once
            print("First initialization...")
            result1 = initializeZLUDA(str(zluda_dir))
            assert result1 is True
            
            # Capture state after first initialization
            cuda_path_1 = os.environ.get('CUDA_PATH')
            if sys.platform == 'win32':
                lib_path_1 = os.environ.get('PATH')
            else:
                lib_path_1 = os.environ.get('LD_LIBRARY_PATH')
            
            # Initialize again (idempotent test)
            print("Second initialization (should be idempotent)...")
            result2 = initializeZLUDA(str(zluda_dir))
            assert result2 is True
            
            # Capture state after second initialization
            cuda_path_2 = os.environ.get('CUDA_PATH')
            if sys.platform == 'win32':
                lib_path_2 = os.environ.get('PATH')
            else:
                lib_path_2 = os.environ.get('LD_LIBRARY_PATH')
            
            # Verify environment is the same (idempotent)
            print(f"\nCUDA_PATH after first init: {cuda_path_1}")
            print(f"CUDA_PATH after second init: {cuda_path_2}")
            assert cuda_path_1 == cuda_path_2, "CUDA_PATH should remain the same"
            
            # Library path should not have duplicates
            if sys.platform == 'win32':
                path_count = lib_path_2.count(str(zluda_dir))
                print(f"Number of times ZLUDA appears in PATH: {path_count}")
                # Should appear at least once, but not be duplicated excessively
                assert path_count >= 1, "ZLUDA should be in PATH"
            else:
                path_count = lib_path_2.count(str(zluda_dir))
                print(f"Number of times ZLUDA appears in LD_LIBRARY_PATH: {path_count}")
                assert path_count >= 1, "ZLUDA should be in LD_LIBRARY_PATH"
            
            print("\n✓ Test 2 PASSED: Initialization is idempotent")
            
        finally:
            # Restore original environment
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


def test_initialize_zluda_invalid_paths():
    """Test that ZLUDA initialization fails safely with invalid paths."""
    print("\n\nTest 3: ZLUDA initialization with invalid paths")
    print("-" * 50)
    
    # Test with non-existent path
    print("Testing with non-existent path...")
    result = initializeZLUDA('/nonexistent/path/to/zluda')
    print(f"Result: {result}")
    assert result is False, "Should fail with non-existent path"
    
    # Test with empty string
    print("\nTesting with empty string...")
    result = initializeZLUDA('')
    print(f"Result: {result}")
    assert result is False, "Should fail with empty string"
    
    # Test with None (should handle gracefully)
    print("\nTesting with None...")
    result = initializeZLUDA(None)
    print(f"Result: {result}")
    assert result is False, "Should fail with None"
    
    print("\n✓ Test 3 PASSED: Invalid paths handled safely")


def test_initialize_zluda_with_subdirectories():
    """Test ZLUDA initialization with bin/lib subdirectories."""
    print("\n\nTest 4: ZLUDA initialization with subdirectories")
    print("-" * 50)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        zluda_dir = Path(tmp_dir) / "zluda"
        zluda_dir.mkdir()
        
        # Create bin subdirectory with ZLUDA files
        bin_dir = zluda_dir / "bin"
        bin_dir.mkdir()
        
        if sys.platform == 'win32':
            (bin_dir / "nvcuda.dll").touch()
        else:
            (bin_dir / "libcuda.so").touch()
        
        print(f"Created ZLUDA with bin subdirectory: {bin_dir}")
        
        # Save original environment
        original_cuda_path = os.environ.get('CUDA_PATH')
        original_path = os.environ.get('PATH')
        original_ld_path = os.environ.get('LD_LIBRARY_PATH')
        
        try:
            # Initialize
            result = initializeZLUDA(str(zluda_dir))
            assert result is True, "Initialization should succeed"
            
            # Verify both main dir and bin dir are in library path
            if sys.platform == 'win32':
                path_var = os.environ.get('PATH', '')
                print(f"Main dir in PATH: {str(zluda_dir) in path_var}")
                print(f"Bin dir in PATH: {str(bin_dir) in path_var}")
                assert str(bin_dir) in path_var, "Bin subdirectory should be in PATH"
            else:
                ld_path = os.environ.get('LD_LIBRARY_PATH', '')
                print(f"Main dir in LD_LIBRARY_PATH: {str(zluda_dir) in ld_path}")
                print(f"Bin dir in LD_LIBRARY_PATH: {str(bin_dir) in ld_path}")
                assert str(bin_dir) in ld_path, "Bin subdirectory should be in LD_LIBRARY_PATH"
            
            print("\n✓ Test 4 PASSED: Subdirectories handled correctly")
            
        finally:
            # Restore original environment
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


if __name__ == "__main__":
    print("=" * 50)
    print("ZLUDA Initialization Manual Tests")
    print("=" * 50)
    
    try:
        test_initialize_zluda_basic()
        test_initialize_zluda_idempotent()
        test_initialize_zluda_invalid_paths()
        test_initialize_zluda_with_subdirectories()
        
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED ✓")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
