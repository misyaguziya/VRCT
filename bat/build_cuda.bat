call .venv_cuda/Scripts/activate
pyinstaller spec/backend_cuda.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR