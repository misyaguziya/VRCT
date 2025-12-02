REM .venv exists
if exist .venv (
    rmdir /s /q .venv
)

REM make .venv (using Python 3.11)
py -3.11 -m venv .venv

REM install packages for .venv
call .venv/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

REM if .venv_cuda exists
if exist .venv_cuda (
    rmdir /s /q .venv_cuda
)

REM make .venv_cuda (using Python 3.11)
py -3.11 -m venv .venv_cuda

REM install packages for .venv_cuda
call .venv_cuda/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements_cuda.txt

REM Check for ZLUDA installation (optional, for AMD GPU users)
call bat\install_zluda.bat