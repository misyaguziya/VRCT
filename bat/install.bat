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

REM if .venv_amd exists
if exist .venv_amd (
    rmdir /s /q .venv_amd
)

REM make .venv_amd
REM AMD (ROCm) lineage. Developer / verification use only for now -- nothing
REM is distributed from here yet (see issue #88). Safe to skip if you do not
REM have an AMD GPU; the CPU and CUDA environments above are unaffected.
python -m venv .venv_amd

REM install packages for .venv_amd
call .venv_amd/Scripts/activate
python.exe -m pip install --upgrade pip
pip install --no-cache-dir --force-reinstall -r requirements_amd.txt
REM rapidocr requires opencv-python, but this app uses opencv-python-headless.
REM Both provide the same cv2 and collide, so reinstall it without its
REM dependencies (the dependencies are listed explicitly in requirements).
pip install --no-cache-dir --force-reinstall --no-deps rapidocr==3.9.2
REM Replace the PyPI (CPU) ctranslate2 with the ROCm build. This must run
REM AFTER the requirements install above, otherwise pip's dependency
REM resolution puts the CPU wheel back.
python -X utf8 tools\fetch_ct2_rocm_wheel.py
python -X utf8 tools\fetch_ocr_models.py
