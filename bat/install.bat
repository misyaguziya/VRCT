REM .venv exists
if exist .venv (
    rmdir /s /q .venv
)

REM make .venv
python -m venv .venv

REM install packages for .venv
call .venv/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements.txt

REM if .venv_cuda exists
if exist .venv_cuda (
    rmdir /s /q .venv_cuda
)

REM make .venv_cuda
python -m venv .venv_cuda

REM install packages for .venv_cuda
call .venv_cuda/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements_cuda.txt