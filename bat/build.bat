@echo off
call .venv/Scripts/activate
if "%VRCT_PYINSTALLER_CLEAN%"=="1" (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR
) else (
    pyinstaller spec/backend.spec --distpath src-tauri/bin --noconfirm --log-level ERROR
)
