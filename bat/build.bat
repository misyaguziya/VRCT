@echo off
if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
    echo Removing dev-fast PyInstaller placeholder before production build...
    rmdir /S /Q src-tauri\bin\_internal
    if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
        echo ERROR: could not remove the dev-fast PyInstaller placeholder
        exit /b 1
    )
)
call .venv/Scripts/activate
python -m pip install --no-deps ./native/vrct-audio
if errorlevel 1 exit /b 1
python -c "import vrct_audio; assert callable(vrct_audio.encode_flac)"
if errorlevel 1 exit /b 1
python -m pip install --no-deps ./native/vrct-graphics
if errorlevel 1 exit /b 1
python -c "import vrct_graphics; assert hasattr(vrct_graphics, 'CaptureSession')"
if errorlevel 1 exit /b 1
if "%VRCT_PYINSTALLER_CLEAN%"=="1" (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR
) else (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --noconfirm --log-level ERROR
)
