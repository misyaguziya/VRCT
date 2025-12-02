@echo off
REM ZLUDA Installation Script for VRCT
REM This script detects AMD GPUs and installs ZLUDA for GPU acceleration

REM Check if install path is provided as argument
set "ZLUDA_INSTALL_PATH=%~1"
if "%ZLUDA_INSTALL_PATH%"=="" (
    REM Default to .venv_cuda\zluda if no path provided
    set "ZLUDA_INSTALL_PATH=%~dp0..\venv_cuda\zluda"
)

echo.
echo ========================================
echo ZLUDA Installation for VRCT
echo ========================================
echo.
echo Install path: %ZLUDA_INSTALL_PATH%
echo.

REM Check for AMD GPU presence
echo Checking for AMD GPU...
python -c "import subprocess; result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], capture_output=True, text=True); exit(0 if 'AMD' in result.stdout or 'Radeon' in result.stdout or 'ATI' in result.stdout else 1)" 2>nul

if %errorlevel% neq 0 (
    echo No AMD GPU detected. ZLUDA is only useful for AMD GPUs.
    echo Skipping ZLUDA installation.
    echo.
    exit /b 0
)

echo AMD GPU detected!
echo.

REM Skip user prompt if running from installer (path provided)
if not "%~1"=="" (
    echo Running automated ZLUDA installation...
    goto :start_install
)

REM Prompt user for ZLUDA installation
echo ZLUDA enables GPU acceleration for AMD graphics cards.
echo This will download and install ZLUDA automatically.
echo.
set /p INSTALL_ZLUDA=Would you like to install ZLUDA for GPU acceleration? (Y/N): 

if /I not "%INSTALL_ZLUDA%"=="Y" (
    echo ZLUDA installation skipped by user.
    echo.
    exit /b 0
)

:start_install
echo.
echo Starting ZLUDA installation...
echo.

REM Activate the CUDA virtual environment if it exists
if exist "%~dp0..\.venv_cuda\Scripts\activate.bat" (
    call "%~dp0..\.venv_cuda\Scripts\activate.bat"
) else (
    REM Try to use system Python if venv doesn't exist
    echo Virtual environment not found, using system Python...
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found.
    echo Please ensure Python is installed and in PATH.
    echo.
    exit /b 1
)

REM Call Python ZLUDA installer module
echo Downloading and installing ZLUDA...
echo This may take a few minutes depending on your internet connection.
echo.

python -c "import sys; sys.path.insert(0, '%~dp0..\\src-python'); from zluda_installer import ZLUDAInstaller; installer = ZLUDAInstaller(r'%ZLUDA_INSTALL_PATH%'); success = installer.install(); exit(0 if success else 1)"

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo ZLUDA installation failed.
    echo ========================================
    echo.
    echo This is not critical - VRCT will continue to work with CPU processing.
    echo You can try installing ZLUDA manually later if needed.
    echo.
    echo Possible reasons for failure:
    echo   - Network connection issues
    echo   - GitHub API rate limiting
    echo   - Incompatible ZLUDA version
    echo.
    echo The application will use CPU for processing instead.
    echo.
    pause
    exit /b 0
)

echo.
echo ========================================
echo ZLUDA installed successfully!
echo ========================================
echo.
echo ZLUDA has been installed to: .venv_cuda\zluda
echo Your AMD GPU will now be available for acceleration.
echo.
echo You can select your AMD GPU in the VRCT settings under "Compute Device".
echo.

exit /b 0
