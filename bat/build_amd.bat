@echo off
if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
    echo Removing dev-fast PyInstaller placeholder before production build...
    rmdir /S /Q src-tauri\bin\_internal
    if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
        echo ERROR: could not remove the dev-fast PyInstaller placeholder
        exit /b 1
    )
)
REM The ROCm runtime is not part of the ctranslate2 wheel, so the spec picks
REM it up from the AMD HIP SDK. Fail early with a readable message instead of
REM letting PyInstaller produce a build that cannot load at runtime.
if "%HIP_PATH%"=="" (
    echo ERROR: HIP_PATH is not set. Install the AMD HIP SDK for Windows first.
    echo        This lineage is for development and hardware verification only.
    exit /b 1
)
call .venv_amd/Scripts/activate
set VRCT_BUILD_EDITION=amd
if "%VRCT_PYINSTALLER_CLEAN%"=="1" (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR
) else (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --noconfirm --log-level ERROR
)
