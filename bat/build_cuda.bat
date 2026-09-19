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
REM The two specs were merged into spec/backend.spec; the edition is passed
REM through this variable (see VRCT_BUILD_EDITION in spec/backend.spec).
set VRCT_BUILD_EDITION=cuda
if "%VRCT_PYINSTALLER_CLEAN%"=="1" (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR
) else (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --noconfirm --log-level ERROR
)
