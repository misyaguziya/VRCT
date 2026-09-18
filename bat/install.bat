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
REM rapidocr は opencv-python を要求するが、本体は opencv-python-headless を使う。
REM 両者は同じ cv2 を提供して衝突するため、依存なしで入れ直す (依存は requirements に明示済み)。
pip install --no-cache-dir --force-reinstall --no-deps rapidocr==3.9.2
python -X utf8 toolsetch_ocr_models.py

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
REM rapidocr は opencv-python を要求するが、本体は opencv-python-headless を使う。
REM 両者は同じ cv2 を提供して衝突するため、依存なしで入れ直す (依存は requirements に明示済み)。
pip install --no-cache-dir --force-reinstall --no-deps rapidocr==3.9.2
python -X utf8 toolsetch_ocr_models.py
