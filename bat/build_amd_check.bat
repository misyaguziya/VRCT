@echo off
REM Build the standalone AMD verification tool that we hand to testers.
REM Output: dist_amd_check\VRCT-AMD-Check\VRCT-AMD-Check.exe (zip that folder).
REM
REM This is NOT the VRCT application. It is the diagnostic from
REM tools/amd_spike/check_amd.py, frozen together with the ROCm build of
REM CTranslate2 and the ROCm runtime, so a tester needs no Python, no pip and
REM no HIP SDK on their machine.
REM
REM Requires: .venv_amd (bat\install.bat) and the AMD HIP SDK for Windows
REM (7.2.x or newer -- 7.1.x names the library libhipblas.dll while the
REM CTranslate2 wheel asks for hipblas.dll; see CTranslate2 issue #2016).
if "%HIP_PATH%"=="" (
    echo ERROR: HIP_PATH is not set. Install the AMD HIP SDK for Windows first.
    exit /b 1
)
if not exist .venv_amd (
    echo ERROR: .venv_amd is missing. Run bat\install.bat first.
    exit /b 1
)
call .venv_amd/Scripts/activate
pyinstaller tools/amd_spike/check_amd.spec --distpath dist_amd_check --noconfirm --log-level ERROR
if errorlevel 1 exit /b 1
echo.
echo Built dist_amd_check\VRCT-AMD-Check\
echo Zip that folder and send it to the tester along with
echo tools\amd_spike\README.md
