"""Test script for ZLUDAInstaller class implementation.

This script tests the basic functionality of the ZLUDAInstaller class
without actually downloading or installing ZLUDA.
"""

import sys
import os
import tempfile
import zipfile
from pathlib import Path

# Add src-python to path
sys.path.insert(0, str(Path(__file__).parent))

from zluda_installer import ZLUDAInstaller, detectZLUDA, initializeZLUDA
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_installer_initialization():
    """Test ZLUDAInstaller initialization."""
    print("\n=== Test 1: Installer Initialization ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        installer = ZLUDAInstaller(temp_dir)
        
        assert installer.install_path == Path(temp_dir), "Install path not set correctly"
        assert installer.download_path is None, "Download path should be None initially"
        assert installer.temp_dir is None, "Temp dir should be None initially"
        
        print("✓ Installer initialization works correctly")
        return True


def test_amd_gpu_detection():
    """Test AMD GPU detection."""
    print("\n=== Test 2: AMD GPU Detection ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        installer = ZLUDAInstaller(temp_dir)
        
        # This will return True or False depending on system
        result = installer.detectAMDGPU()
        
        print(f"AMD GPU detection result: {result}")
        print("✓ AMD GPU detection method works (no exceptions)")
        return True


def test_extract_zluda_with_mock():
    """Test ZLUDA extraction with a mock zip file."""
    print("\n=== Test 3: ZLUDA Extraction (Mock) ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        installer = ZLUDAInstaller(temp_dir)
        
        # Create a mock ZLUDA zip file
        mock_zip_path = Path(temp_dir) / "mock_zluda.zip"
        with zipfile.ZipFile(mock_zip_path, 'w') as zf:
            # Add mock ZLUDA files
            if sys.platform == 'win32':
                zf.writestr("nvcuda.dll", b"mock cuda dll")
                zf.writestr("cublas.dll", b"mock cublas dll")
            else:
                zf.writestr("libcuda.so", b"mock cuda so")
                zf.writestr("libcublas.so", b"mock cublas so")
        
        # Set up installer state
        installer.download_path = mock_zip_path
        installer.install_path = Path(temp_dir) / "zluda_install"
        
        # Test extraction
        result = installer.extractZLUDA()
        
        assert result is True, "Extraction should succeed"
        assert installer.install_path.exists(), "Install path should exist"
        
        # Verify files were extracted
        if sys.platform == 'win32':
            assert (installer.install_path / "nvcuda.dll").exists(), "nvcuda.dll should exist"
        else:
            assert (installer.install_path / "libcuda.so").exists(), "libcuda.so should exist"
        
        print("✓ ZLUDA extraction works correctly")
        return True


def test_configure_environment():
    """Test environment configuration."""
    print("\n=== Test 4: Environment Configuration ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock ZLUDA installation
        install_path = Path(temp_dir) / "zluda"
        install_path.mkdir()
        
        # Create mock ZLUDA files
        if sys.platform == 'win32':
            (install_path / "nvcuda.dll").write_bytes(b"mock")
        else:
            (install_path / "libcuda.so").write_bytes(b"mock")
        
        installer = ZLUDAInstaller(str(install_path))
        
        # Test configuration
        result = installer.configureEnvironment()
        
        assert result is True, "Configuration should succeed"
        assert os.environ.get('CUDA_PATH') == str(install_path), "CUDA_PATH should be set"
        
        print("✓ Environment configuration works correctly")
        return True


def test_verify():
    """Test installation verification."""
    print("\n=== Test 5: Installation Verification ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock ZLUDA installation
        install_path = Path(temp_dir) / "zluda"
        install_path.mkdir()
        
        # Create mock ZLUDA files
        if sys.platform == 'win32':
            (install_path / "nvcuda.dll").write_bytes(b"mock")
        else:
            (install_path / "libcuda.so").write_bytes(b"mock")
        
        installer = ZLUDAInstaller(str(install_path))
        
        # Configure environment first
        installer.configureEnvironment()
        
        # Test verification
        result = installer.verify()
        
        assert result is True, "Verification should succeed"
        
        print("✓ Installation verification works correctly")
        return True


def test_class_attributes():
    """Test class attributes are set correctly."""
    print("\n=== Test 6: Class Attributes ===")
    
    assert hasattr(ZLUDAInstaller, 'ZLUDA_REPO'), "ZLUDA_REPO should exist"
    assert hasattr(ZLUDAInstaller, 'ZLUDA_RELEASE_API'), "ZLUDA_RELEASE_API should exist"
    
    assert ZLUDAInstaller.ZLUDA_REPO == "https://github.com/vosen/ZLUDA"
    assert ZLUDAInstaller.ZLUDA_RELEASE_API == "https://api.github.com/repos/vosen/ZLUDA/releases/latest"
    
    print("✓ Class attributes are correct")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing ZLUDAInstaller Class Implementation")
    print("=" * 60)
    
    tests = [
        test_installer_initialization,
        test_amd_gpu_detection,
        test_extract_zluda_with_mock,
        test_configure_environment,
        test_verify,
        test_class_attributes,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
