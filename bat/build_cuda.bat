@echo off
call .venv_cuda/Scripts/activate
if "%VRCT_PYINSTALLER_CLEAN%"=="1" (
    pyinstaller spec/backend_cuda.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR
) else (
    pyinstaller spec/backend_cuda.spec --distpath src-tauri/bin --noconfirm --log-level ERROR
)
