REM .venv .venv_cuda があれば削除
if exist .venv (
    rmdir /s /q .venv
)

if exist .venv_cuda (
    rmdir /s /q .venv_cuda
)

REM .venv .venv_cuda を作成
python -m venv .venv
python -m venv .venv_cuda

REM .venv .venv_cuda に必要なパッケージをインストール
call .venv/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements.txt

call .venv_cuda/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements_cuda.txt