@echo off
setlocal
cd /d "%~dp0.."
if not defined VRCT_COLLECTOR_PYTHON set "VRCT_COLLECTOR_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%VRCT_COLLECTOR_PYTHON%" (
    echo Python not found. See docs\dataset_collector_distribution.md.
    exit /b 1
)
"%VRCT_COLLECTOR_PYTHON%" -X utf8 tools\build_dataset_collector.py
exit /b %errorlevel%
