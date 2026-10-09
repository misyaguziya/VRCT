REM .venv exists
if exist .venv (
    rmdir /s /q .venv
)

REM make .venv
python -m venv .venv

REM install packages for .venv
call .venv/Scripts/activate
python.exe -m pip install --upgrade pip
python -m pip install --no-cache-dir --force-reinstall -r requirements.txt
if errorlevel 1 exit /b 1
python -m pip install --no-deps ./native/vrct-audio
if errorlevel 1 exit /b 1
python -m pip install --no-deps ./native/vrct-graphics
if errorlevel 1 exit /b 1
REM rapidocr/windows-capture pull in opencv-python, which overwrites headless cv2.
REM Uninstall the overlapping GUI files first, then restore the pinned headless build.
python -m pip uninstall --yes opencv-python
if errorlevel 1 exit /b 1
python -m pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless==4.10.0.84
if errorlevel 1 exit /b 1
python -c "import cv2; import importlib.metadata as m; assert cv2.__version__ == '4.10.0'; assert m.version('opencv-python-headless') == '4.10.0.84'; assert not any(d.metadata['Name'].lower() == 'opencv-python' for d in m.distributions())"
if errorlevel 1 exit /b 1
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
python -m pip install --no-cache-dir --force-reinstall -r requirements_cuda.txt
if errorlevel 1 exit /b 1
python -m pip install --no-deps ./native/vrct-audio
if errorlevel 1 exit /b 1
python -m pip install --no-deps ./native/vrct-graphics
if errorlevel 1 exit /b 1
REM rapidocr/windows-capture pull in opencv-python, which overwrites headless cv2.
REM Uninstall the overlapping GUI files first, then restore the pinned headless build.
python -m pip uninstall --yes opencv-python
if errorlevel 1 exit /b 1
python -m pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless==4.10.0.84
if errorlevel 1 exit /b 1
python -c "import cv2; import importlib.metadata as m; assert cv2.__version__ == '4.10.0'; assert m.version('opencv-python-headless') == '4.10.0.84'; assert not any(d.metadata['Name'].lower() == 'opencv-python' for d in m.distributions())"
if errorlevel 1 exit /b 1
python -X utf8 tools\fetch_ocr_models.py
