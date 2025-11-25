call .venv/Scripts/activate
pyinstaller spec/backend.spec --distpath src-tauri/bin --clean --noconfirm --log-level ERROR