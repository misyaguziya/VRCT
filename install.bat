python -m venv .venv
python -m venv .venv_cuda

call .venv/Scripts/activate
python.exe -m pip install --upgrade pip
pip install -r requirements.txt

call .venv_cuda/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
pip install -r requirements_cuda.txt