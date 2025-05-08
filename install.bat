python -m venv .venv
python -m venv .venv_cuda

call .venv/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements.txt

call .venv_cuda/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements_cuda.txt