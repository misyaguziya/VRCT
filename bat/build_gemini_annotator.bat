@echo off
setlocal
cd /d "%~dp0.."
if not defined VRCT_ANNOTATOR_PYTHON set "VRCT_ANNOTATOR_PYTHON=%CD%\.venv-annotator\Scripts\python.exe"
if not exist "%VRCT_ANNOTATOR_PYTHON%" (
    echo Python not found. See docs\gemini_annotation_workflow.md.
    exit /b 1
)
"%VRCT_ANNOTATOR_PYTHON%" -X utf8 tools\build_gemini_annotator.py
exit /b %errorlevel%
