@echo off
rem VRCT AMD check: runs every test with the bundled models. Nothing is sent or downloaded.
rem The translation model for llama.cpp is optional (see README: models\translation.gguf).
cd /d "%~dp0"
set LLAMA=
if exist "models\translation.gguf" set LLAMA=--llama-model models\translation.gguf
vrct-amd-check.exe --runs 3 --timeout 900 --whisper-model models\ggml-large-v3-turbo.bin --ct2-whisper-model models\whisper-ct2-fp16 --nllb-model models\nllb-ct2 %LLAMA%
echo.
echo Finished. Please send vrct_amd_check_report.txt and vrct_amd_check_report.json (in this folder).
pause
