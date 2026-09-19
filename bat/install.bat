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
REM rapidocr requires opencv-python, but this app uses opencv-python-headless.
REM Both provide the same cv2 and collide, so reinstall it without its
REM dependencies (the dependencies are listed explicitly in requirements).
pip install --no-cache-dir --force-reinstall --no-deps rapidocr==3.9.2
python -X utf8 tools\fetch_ocr_models.py

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
REM rapidocr requires opencv-python, but this app uses opencv-python-headless.
REM Both provide the same cv2 and collide, so reinstall it without its
REM dependencies (the dependencies are listed explicitly in requirements).
pip install --no-cache-dir --force-reinstall --no-deps rapidocr==3.9.2
python -X utf8 tools\fetch_ocr_models.py
