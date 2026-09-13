@echo off
if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
    echo Removing dev-fast PyInstaller placeholder before production build...
    rmdir /S /Q src-tauri\bin\_internal
    if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
        echo ERROR: could not remove the dev-fast PyInstaller placeholder
        exit /b 1
    )
)
call .venv_cuda/Scripts/activate
if "%VRCT_PYINSTALLER_CLEAN%"=="1" (
    pyinstaller spec/backend_cuda.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR
) else (
    pyinstaller spec/backend_cuda.spec --distpath src-tauri/bin --noconfirm --log-level ERROR
)
