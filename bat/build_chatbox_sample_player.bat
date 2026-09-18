@echo off
setlocal
cd /d "%~dp0.."
if not defined VRCT_CHATBOX_PYTHON set "VRCT_CHATBOX_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%VRCT_CHATBOX_PYTHON%" (
    echo Python not found. See docs\chatbox_sample_player.md.
    exit /b 1
)
"%VRCT_CHATBOX_PYTHON%" -X utf8 tools\build_chatbox_sample_player.py
exit /b %errorlevel%
