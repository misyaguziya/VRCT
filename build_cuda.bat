call .venv_cuda/Scripts/activate
pyinstaller backend_cuda.spec --distpath src-tauri/bin --clean --noconfirm