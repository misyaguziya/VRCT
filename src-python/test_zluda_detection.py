"""Tests for ZLUDA detection functionality.

This test file verifies that the ZLUDA detection module correctly identifies
ZLUDA installations in various locations.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest

# Add src-python to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from zluda_installer import detectZLUDA, initializeZLUDA, _isValidZLUDAPath, _findInSystemPath


class TestZLUDADetection:
    """Test suite for ZLUDA detection functions."""
    
    def test_detect_zluda_with_env_variable(self, tmp_path):
        """Test ZLUDA detection via ZLUDA_PATH environment variable."""
        # Create a mock ZLUDA installation
        zluda_dir = tmp_path / "zluda"
        zluda_dir.mkdir()
        
        # Create the key ZLUDA file for Windows
        if sys.platform == 'win32':
            (zluda_dir / "nvcuda.dll").touch()
        else:
            (zluda_dir / "libcuda.so").touch()
        
        # Set environment variable
        original_env = os.environ.get('ZLUDA_PATH')
        try:
            os.environ['ZLUDA_PATH'] = str(zluda_dir)
            
            # Test detection
            detected_path = detectZLUDA()
            assert detected_path == str(zluda_dir)
        finally:
            # Restore original environment
            if original_env:
                os.environ['ZLUDA_PATH'] = original_env
            else:
                os.environ.pop('ZLUDA_PATH', None)
    
    def test_detect_zluda_invalid_env_path(self):
        """Test that invalid ZLUDA_PATH is ignored."""
        original_env = os.environ.get('ZLUDA_PATH')
        try:
            # Set to non-existent path
            os.environ['ZLUDA_PATH'] = '/nonexistent/path/to/zluda'
            
            # Should not detect ZLUDA
            detected_path = detectZLUDA()
            # May be None or find it elsewhere, but shouldn't return the invalid path
            assert detected_path != '/nonexistent/path/to/zluda'
        finally:
            if original_env:
                os.environ['ZLUDA_PATH'] = original_env
            else:
                os.environ.pop('ZLUDA_PATH', None)
    
    def test_is_valid_zluda_path_windows(self, tmp_path):
        """Test validation of ZLUDA installation path on Windows."""
        if sys.platform != 'win32':
            pytest.skip("Windows-specific test")
        
        # Create valid ZLUDA directory
        zluda_dir = tmp_path / "zluda"
        zluda_dir.mkdir()
        (zluda_dir / "nvcuda.dll").touch()
        
        assert _isValidZLUDAPath(str(zluda_dir)) is True
        
        # Test with subdirectory
        bin_dir = zluda_dir / "bin"
        bin_dir.mkdir()
        (bin_dir / "nvcuda.dll").touch()
        
        assert _isValidZLUDAPath(str(zluda_dir)) is True
    
    def test_is_valid_zluda_path_linux(self, tmp_path):
        """Test validation of ZLUDA installation path on Linux."""
        if sys.platform == 'win32':
            pytest.skip("Linux-specific test")
        
        # Create valid ZLUDA directory
        zluda_dir = tmp_path / "zluda"
        zluda_dir.mkdir()
        (zluda_dir / "libcuda.so").touch()
        
        assert _isValidZLUDAPath(str(zluda_dir)) is True
    
    def test_is_valid_zluda_path_invalid(self, tmp_path):
        """Test that invalid paths are rejected."""
        # Empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert _isValidZLUDAPath(str(empty_dir)) is False
        
        # Non-existent path
        assert _isValidZLUDAPath(str(tmp_path / "nonexistent")) is False
        
        # File instead of directory
        file_path = tmp_path / "file.txt"
        file_path.touch()
        assert _isValidZLUDAPath(str(file_path)) is False
    
    def test_initialize_zluda_sets_environment(self, tmp_path):
        """Test that initializeZLUDA correctly sets environment variables."""
        # Create mock ZLUDA installation
        zluda_dir = tmp_path / "zluda"
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
            # Initialize ZLUDA
            result = initializeZLUDA(str(zluda_dir))
            assert result is True
            
            # Check CUDA_PATH is set
            assert os.environ.get('CUDA_PATH') == str(zluda_dir)
            
            # Check library path includes ZLUDA
            if sys.platform == 'win32':
                assert str(zluda_dir) in os.environ.get('PATH', '')
            else:
                assert str(zluda_dir) in os.environ.get('LD_LIBRARY_PATH', '')
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
    
    def test_initialize_zluda_invalid_path(self):
        """Test that initializeZLUDA fails gracefully with invalid path."""
        result = initializeZLUDA('/nonexistent/path')
        assert result is False
        
        result = initializeZLUDA('')
        assert result is False
    
    def test_find_in_system_path(self, tmp_path):
        """Test finding files in system PATH."""
        # Create a test file
        test_dir = tmp_path / "testbin"
        test_dir.mkdir()
        test_file = test_dir / "testfile.exe"
        test_file.touch()
        
        # Save original PATH
        original_path = os.environ.get('PATH', '')
        
        try:
            # Add test directory to PATH
            path_sep = ';' if sys.platform == 'win32' else ':'
            os.environ['PATH'] = str(test_dir) + path_sep + original_path
            
            # Test finding the file
            found_path = _findInSystemPath('testfile.exe')
            assert found_path == str(test_dir)
            
            # Test file not in PATH
            not_found = _findInSystemPath('nonexistent.exe')
            assert not_found is None
        finally:
            # Restore original PATH
            os.environ['PATH'] = original_path


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
