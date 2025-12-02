"""ZLUDA installer and detection module.

This module provides functionality to detect, download, install, and configure
ZLUDA (a CUDA compatibility layer for AMD GPUs) for VRCT.
"""

import os
import sys
import subprocess
import platform
import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import logging
import urllib.request
import json

# Setup logger for ZLUDA operations
logger = logging.getLogger(__name__)


def detectZLUDA() -> Optional[str]:
    """Detect if ZLUDA is installed and return its path.
    
    This function checks multiple locations for ZLUDA installation:
    1. ZLUDA_PATH environment variable
    2. Standard installation paths relative to the application:
       - .venv_zluda/
       - .venv_cuda/zluda/
    3. System PATH for zluda.dll (Windows) or libzluda.so (Linux)
    
    Returns:
        Path to ZLUDA installation directory if found, None otherwise.
        The returned path should contain the ZLUDA binaries (DLLs/SOs).
    
    Examples:
        >>> zluda_path = detectZLUDA()
        >>> if zluda_path:
        ...     print(f"ZLUDA found at: {zluda_path}")
        ... else:
        ...     print("ZLUDA not installed")
    """
    # Check 1: Environment variable ZLUDA_PATH
    env_zluda_path = os.environ.get('ZLUDA_PATH')
    if env_zluda_path and _isValidZLUDAPath(env_zluda_path):
        logger.info(f"ZLUDA detected via ZLUDA_PATH environment variable: {env_zluda_path}")
        return env_zluda_path
    
    # Check 2: Standard installation paths relative to application root
    # Get the application root (parent of src-python directory)
    app_root = Path(__file__).parent.parent
    
    standard_paths = [
        app_root / '.venv_zluda',
        app_root / '.venv_cuda' / 'zluda',
    ]
    
    for path in standard_paths:
        if path.exists() and _isValidZLUDAPath(str(path)):
            logger.info(f"ZLUDA detected at standard path: {path}")
            return str(path)
    
    # Check 3: System PATH for ZLUDA binaries
    zluda_binary = 'zluda.dll' if sys.platform == 'win32' else 'libzluda.so'
    path_zluda = _findInSystemPath(zluda_binary)
    if path_zluda:
        logger.info(f"ZLUDA detected in system PATH: {path_zluda}")
        return path_zluda
    
    logger.debug("ZLUDA not detected in any standard location")
    return None


def _isValidZLUDAPath(path: str) -> bool:
    """Check if the given path contains a valid ZLUDA installation.
    
    A valid ZLUDA installation should contain the necessary binary files:
    - On Windows: nvcuda.dll, cublas.dll, cudart.dll, etc.
    - On Linux: libcuda.so, libcublas.so, libcudart.so, etc.
    
    Args:
        path: Path to check for ZLUDA installation
        
    Returns:
        True if the path contains ZLUDA binaries, False otherwise
    """
    if not os.path.isdir(path):
        return False
    
    # Check for key ZLUDA files based on platform
    if sys.platform == 'win32':
        # Windows: Check for any CUDA-related DLL files that ZLUDA provides
        # ZLUDA typically includes: nvcuda.dll, cublas.dll, cudart.dll, nvml.dll, etc.
        required_patterns = ['nvcuda.dll', 'cublas.dll', 'cudart.dll', 'nvml.dll']
    else:
        # Linux: Check for libcuda.so or other CUDA libraries
        required_patterns = ['libcuda.so', 'libcublas.so', 'libcudart.so']
    
    # Check if at least one required file exists (need at least one to be valid)
    path_obj = Path(path)
    found_files = []
    
    # Check root directory
    for pattern in required_patterns:
        if (path_obj / pattern).exists():
            found_files.append(pattern)
    
    # Also check in common subdirectories
    for subdir in ['bin', 'lib', 'lib64', '']:
        if subdir:
            subdir_path = path_obj / subdir
            if not subdir_path.exists():
                continue
        else:
            subdir_path = path_obj
            
        for pattern in required_patterns:
            file_path = subdir_path / pattern
            if file_path.exists():
                found_files.append(f"{subdir}/{pattern}" if subdir else pattern)
    
    # Also check for any .dll files (Windows) or .so files (Linux) as a fallback
    if not found_files:
        extension = '.dll' if sys.platform == 'win32' else '.so'
        for item in path_obj.rglob(f'*{extension}'):
            if item.is_file():
                found_files.append(str(item.relative_to(path_obj)))
                break  # Found at least one library file
    
    if found_files:
        logger.debug(f"Found ZLUDA files: {found_files[:5]}")  # Log first 5 files
        return True
    
    logger.debug(f"No ZLUDA files found in {path}")
    return False


def _findInSystemPath(filename: str) -> Optional[str]:
    """Search for a file in the system PATH.
    
    Args:
        filename: Name of the file to search for
        
    Returns:
        Directory path containing the file if found, None otherwise
    """
    path_env = os.environ.get('PATH', '')
    if not path_env:
        return None
    
    # Split PATH by the appropriate separator
    path_separator = ';' if sys.platform == 'win32' else ':'
    paths = path_env.split(path_separator)
    
    for path in paths:
        if not path:
            continue
        
        file_path = Path(path) / filename
        if file_path.exists() and file_path.is_file():
            return path
    
    return None


def initializeZLUDA(zluda_path: str) -> bool:
    """Initialize ZLUDA by setting environment variables.
    
    This function configures the environment to use ZLUDA as a CUDA replacement
    by setting the necessary environment variables:
    - CUDA_PATH: Points to ZLUDA installation
    - PATH (Windows) / LD_LIBRARY_PATH (Linux): Includes ZLUDA binaries
    
    This function is idempotent - calling it multiple times with the same path
    is safe and will not cause issues.
    
    Args:
        zluda_path: Path to ZLUDA installation directory
        
    Returns:
        True if initialization successful, False otherwise
        
    Examples:
        >>> zluda_path = detectZLUDA()
        >>> if zluda_path:
        ...     success = initializeZLUDA(zluda_path)
        ...     if success:
        ...         print("ZLUDA initialized successfully")
    """
    if not zluda_path or not os.path.isdir(zluda_path):
        logger.error(f"Invalid ZLUDA path provided: {zluda_path}")
        return False
    
    if not _isValidZLUDAPath(zluda_path):
        logger.error(f"Path does not contain valid ZLUDA installation: {zluda_path}")
        return False
    
    try:
        # Set CUDA_PATH to ZLUDA installation
        os.environ['CUDA_PATH'] = zluda_path
        logger.info(f"Set CUDA_PATH to: {zluda_path}")
        
        # Add ZLUDA binaries to library path
        zluda_path_obj = Path(zluda_path)
        
        # Determine binary directories to add
        bin_dirs = [str(zluda_path_obj)]
        
        # Check for common subdirectories
        for subdir in ['bin', 'lib', 'lib64']:
            subdir_path = zluda_path_obj / subdir
            if subdir_path.exists():
                bin_dirs.append(str(subdir_path))
        
        if sys.platform == 'win32':
            # Windows: Add to PATH
            current_path = os.environ.get('PATH', '')
            new_paths = [d for d in bin_dirs if d not in current_path]
            
            if new_paths:
                path_separator = ';'
                os.environ['PATH'] = path_separator.join(new_paths) + path_separator + current_path
                logger.info(f"Added ZLUDA directories to PATH: {new_paths}")
        else:
            # Linux: Add to LD_LIBRARY_PATH
            current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
            new_paths = [d for d in bin_dirs if d not in current_ld_path]
            
            if new_paths:
                path_separator = ':'
                if current_ld_path:
                    os.environ['LD_LIBRARY_PATH'] = path_separator.join(new_paths) + path_separator + current_ld_path
                else:
                    os.environ['LD_LIBRARY_PATH'] = path_separator.join(new_paths)
                logger.info(f"Added ZLUDA directories to LD_LIBRARY_PATH: {new_paths}")
        
        logger.info("ZLUDA initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize ZLUDA: {e}")
        return False


class ZLUDAInstaller:
    """Handles ZLUDA download, installation, and configuration.
    
    This class provides functionality to:
    - Detect AMD GPUs in the system
    - Download ZLUDA from GitHub releases
    - Extract and install ZLUDA binaries
    - Verify the installation
    """
    
    ZLUDA_REPO = "https://github.com/vosen/ZLUDA"
    ZLUDA_RELEASE_API = "https://api.github.com/repos/vosen/ZLUDA/releases/latest"
    
    def __init__(self, install_path: str):
        """Initialize installer with target installation path.
        
        Args:
            install_path: Directory where ZLUDA should be installed
        """
        self.install_path = Path(install_path)
        self.download_path: Optional[Path] = None
        self.temp_dir: Optional[Path] = None
        logger.info(f"ZLUDAInstaller initialized with install_path: {install_path}")
    
    def detectAMDGPU(self) -> bool:
        """Detect if AMD GPU is present in system.
        
        Uses platform-specific methods to detect AMD GPUs:
        - Windows: Uses wmic to query video controllers
        - Linux: Checks lspci output for AMD/ATI graphics
        
        Returns:
            True if AMD GPU detected, False otherwise
        """
        try:
            if sys.platform == 'win32':
                # Windows: Use wmic to query video controllers
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    output = result.stdout.lower()
                    # Check for AMD/Radeon in the output
                    if 'amd' in output or 'radeon' in output or 'ati' in output:
                        logger.info("AMD GPU detected via wmic")
                        return True
                    
            elif sys.platform.startswith('linux'):
                # Linux: Use lspci to check for AMD graphics
                result = subprocess.run(
                    ['lspci'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    output = result.stdout.lower()
                    # Check for AMD/ATI VGA/Display controller
                    for line in output.split('\n'):
                        if ('vga' in line or 'display' in line or '3d' in line) and \
                           ('amd' in line or 'ati' in line or 'radeon' in line):
                            logger.info("AMD GPU detected via lspci")
                            return True
            
            logger.info("No AMD GPU detected")
            return False
            
        except subprocess.TimeoutExpired:
            logger.warning("GPU detection timed out")
            return False
        except FileNotFoundError as e:
            logger.warning(f"GPU detection command not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Error detecting AMD GPU: {e}")
            return False
    
    def _getLatestRelease(self) -> Optional[Dict[str, Any]]:
        """Fetch latest ZLUDA release information from GitHub API.
        
        Returns:
            Dictionary with release information or None if failed
        """
        try:
            logger.info(f"Fetching latest ZLUDA release from {self.ZLUDA_RELEASE_API}")
            
            # Create request with User-Agent header (required by GitHub API)
            req = urllib.request.Request(
                self.ZLUDA_RELEASE_API,
                headers={'User-Agent': 'VRCT-ZLUDA-Installer'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                logger.info(f"Found ZLUDA release: {data.get('tag_name', 'unknown')}")
                return data
                
        except urllib.error.URLError as e:
            logger.error(f"Failed to fetch ZLUDA release info: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ZLUDA release JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ZLUDA release: {e}")
            return None
    
    def _selectAsset(self, release_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select the appropriate ZLUDA asset for the current platform.
        
        Args:
            release_data: Release information from GitHub API
            
        Returns:
            Asset dictionary or None if no suitable asset found
        """
        assets = release_data.get('assets', [])
        
        if not assets:
            logger.error("No assets found in ZLUDA release")
            return None
        
        # Determine platform-specific asset name pattern
        if sys.platform == 'win32':
            # Look for Windows build (typically contains 'windows' or 'win')
            pattern = 'windows'
        elif sys.platform.startswith('linux'):
            # Look for Linux build
            pattern = 'linux'
        else:
            logger.error(f"Unsupported platform: {sys.platform}")
            return None
        
        # Find matching asset
        for asset in assets:
            name = asset.get('name', '').lower()
            if pattern in name and name.endswith('.zip'):
                logger.info(f"Selected asset: {asset.get('name')}")
                return asset
        
        # If no exact match, try to find any zip file
        for asset in assets:
            name = asset.get('name', '').lower()
            if name.endswith('.zip'):
                logger.warning(f"Using fallback asset: {asset.get('name')}")
                return asset
        
        logger.error(f"No suitable ZLUDA asset found for platform: {sys.platform}")
        return None
    
    def downloadZLUDA(self, callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Download latest ZLUDA release.
        
        Args:
            callback: Optional progress callback function(bytes_downloaded, total_bytes)
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Get latest release info
            release_data = self._getLatestRelease()
            if not release_data:
                return False
            
            # Select appropriate asset
            asset = self._selectAsset(release_data)
            if not asset:
                return False
            
            download_url = asset.get('browser_download_url')
            if not download_url:
                logger.error("No download URL found in asset")
                return False
            
            # Create temporary directory for download
            self.temp_dir = Path(tempfile.mkdtemp(prefix='zluda_install_'))
            self.download_path = self.temp_dir / asset.get('name', 'zluda.zip')
            
            logger.info(f"Downloading ZLUDA from: {download_url}")
            logger.info(f"Download path: {self.download_path}")
            
            # Download with progress tracking
            def _progress_hook(block_num, block_size, total_size):
                if callback:
                    downloaded = block_num * block_size
                    callback(downloaded, total_size)
            
            urllib.request.urlretrieve(
                download_url,
                self.download_path,
                reporthook=_progress_hook if callback else None
            )
            
            # Verify download
            if not self.download_path.exists():
                logger.error("Download file not found after download")
                return False
            
            file_size = self.download_path.stat().st_size
            logger.info(f"Download complete: {file_size} bytes")
            
            return True
            
        except urllib.error.URLError as e:
            logger.error(f"Failed to download ZLUDA: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading ZLUDA: {e}")
            return False
    
    def extractZLUDA(self) -> bool:
        """Extract ZLUDA binaries to installation path.
        
        Returns:
            True if extraction successful, False otherwise
        """
        try:
            if not self.download_path or not self.download_path.exists():
                logger.error("No download file found to extract")
                return False
            
            logger.info(f"Extracting ZLUDA to: {self.install_path}")
            
            # Create installation directory if it doesn't exist
            self.install_path.mkdir(parents=True, exist_ok=True)
            
            # Extract zip file
            with zipfile.ZipFile(self.download_path, 'r') as zip_ref:
                # List contents for logging
                file_list = zip_ref.namelist()
                logger.info(f"Extracting {len(file_list)} files")
                
                # Extract all files
                zip_ref.extractall(self.install_path)
            
            logger.info("Extraction complete")
            
            # Verify extraction by checking for key files
            if not _isValidZLUDAPath(str(self.install_path)):
                logger.error("Extracted files do not appear to be a valid ZLUDA installation")
                return False
            
            return True
            
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid zip file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to extract ZLUDA: {e}")
            return False
    
    def configureEnvironment(self) -> bool:
        """Configure environment variables for ZLUDA.
        
        Uses the existing initializeZLUDA function to set up environment.
        
        Returns:
            True if configuration successful, False otherwise
        """
        try:
            logger.info("Configuring environment for ZLUDA")
            return initializeZLUDA(str(self.install_path))
        except Exception as e:
            logger.error(f"Failed to configure ZLUDA environment: {e}")
            return False
    
    def install(self, callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Complete installation process.
        
        Performs the full installation workflow:
        1. Detect AMD GPU
        2. Download ZLUDA
        3. Extract ZLUDA
        4. Configure environment
        5. Verify installation
        
        Args:
            callback: Optional progress callback function(bytes_downloaded, total_bytes)
            
        Returns:
            True if installation successful, False otherwise
        """
        try:
            logger.info("Starting ZLUDA installation")
            
            # Step 1: Detect AMD GPU
            logger.info("Step 1/5: Detecting AMD GPU...")
            if not self.detectAMDGPU():
                logger.warning("No AMD GPU detected, but continuing installation anyway")
            
            # Step 2: Download ZLUDA
            logger.info("Step 2/5: Downloading ZLUDA...")
            if not self.downloadZLUDA(callback):
                logger.error("Failed to download ZLUDA")
                return False
            
            # Step 3: Extract ZLUDA
            logger.info("Step 3/5: Extracting ZLUDA...")
            if not self.extractZLUDA():
                logger.error("Failed to extract ZLUDA")
                return False
            
            # Step 4: Configure environment
            logger.info("Step 4/5: Configuring environment...")
            if not self.configureEnvironment():
                logger.error("Failed to configure ZLUDA environment")
                return False
            
            # Step 5: Verify installation
            logger.info("Step 5/5: Verifying installation...")
            if not self.verify():
                logger.error("ZLUDA installation verification failed")
                return False
            
            logger.info("ZLUDA installation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"ZLUDA installation failed: {e}")
            return False
        finally:
            # Clean up temporary files
            self._cleanup()
    
    def verify(self) -> bool:
        """Verify ZLUDA installation is working.
        
        Checks:
        1. Installation path exists and contains ZLUDA files
        2. Environment variables are set correctly
        3. ZLUDA can be detected by detectZLUDA() (if in standard location)
        
        Returns:
            True if verification successful, False otherwise
        """
        try:
            logger.info("Verifying ZLUDA installation")
            
            # Check 1: Installation path exists and is valid
            if not self.install_path.exists():
                logger.error(f"Installation path does not exist: {self.install_path}")
                return False
            
            if not _isValidZLUDAPath(str(self.install_path)):
                logger.error("Installation path does not contain valid ZLUDA files")
                return False
            
            logger.info("✓ Installation path is valid")
            
            # Check 2: Environment variables are set
            cuda_path = os.environ.get('CUDA_PATH')
            if not cuda_path or Path(cuda_path) != self.install_path:
                logger.warning(f"CUDA_PATH not set correctly: {cuda_path}")
            else:
                logger.info("✓ CUDA_PATH is set correctly")
            
            # Check 3: ZLUDA can be detected (optional - may not work for non-standard paths)
            detected_path = detectZLUDA()
            if detected_path:
                logger.info(f"✓ ZLUDA detected at: {detected_path}")
            else:
                # This is OK if we're installing to a non-standard location
                logger.info("Note: ZLUDA not detected via standard detection (may be in custom location)")
            
            logger.info("ZLUDA installation verification passed")
            return True
            
        except Exception as e:
            logger.error(f"ZLUDA verification failed: {e}")
            return False
    
    def _cleanup(self):
        """Clean up temporary files and directories."""
        try:
            if self.temp_dir and self.temp_dir.exists():
                logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {e}")


if __name__ == "__main__":
    # Simple test when run directly
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing ZLUDA detection...")
    zluda_path = detectZLUDA()
    
    if zluda_path:
        print(f"✓ ZLUDA found at: {zluda_path}")
        print("\nTesting ZLUDA initialization...")
        if initializeZLUDA(zluda_path):
            print("✓ ZLUDA initialized successfully")
            print(f"  CUDA_PATH: {os.environ.get('CUDA_PATH')}")
            if sys.platform == 'win32':
                print(f"  PATH includes ZLUDA: {zluda_path in os.environ.get('PATH', '')}")
            else:
                print(f"  LD_LIBRARY_PATH includes ZLUDA: {zluda_path in os.environ.get('LD_LIBRARY_PATH', '')}")
        else:
            print("✗ ZLUDA initialization failed")
    else:
        print("✗ ZLUDA not detected")
        print("\nChecked locations:")
        print(f"  - ZLUDA_PATH environment variable: {os.environ.get('ZLUDA_PATH', 'not set')}")
        app_root = Path(__file__).parent.parent
        print(f"  - {app_root / '.venv_zluda'}")
        print(f"  - {app_root / '.venv_cuda' / 'zluda'}")
        print(f"  - System PATH")
