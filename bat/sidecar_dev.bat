@echo off
setlocal
cargo build --release --manifest-path utils\dev_sidecar\Cargo.toml
if errorlevel 1 exit /b 1
if not exist src-tauri\bin mkdir src-tauri\bin
copy /Y utils\dev_sidecar\target\release\VRCT-sidecar-x86_64-pc-windows-msvc.exe src-tauri\bin\VRCT-sidecar-x86_64-pc-windows-msvc.exe
if errorlevel 1 exit /b 1
REM tauri dev does not always re-copy the externalBin from src-tauri\bin\ into
REM its cached build output (src-tauri\target\debug\VRCT-sidecar.exe /
REM target\release\VRCT-sidecar.exe) when the Rust side has no source changes.
REM If a production build (npm run build etc., which drops a PyInstaller
REM frozen exe into src-tauri\bin\) ever ran before, that frozen exe can stay
REM cached in target\debug forever, silently making dev-fast run stale Python
REM code no matter how many times you edit src-python and restart (hit this
REM for real on 2026-08-15). Force both cached copies back in sync here.
if exist src-tauri\target\debug\VRCT-sidecar.exe (
    copy /Y utils\dev_sidecar\target\release\VRCT-sidecar-x86_64-pc-windows-msvc.exe src-tauri\target\debug\VRCT-sidecar.exe
    if errorlevel 1 exit /b 1
)
if exist src-tauri\target\release\VRCT-sidecar.exe (
    copy /Y utils\dev_sidecar\target\release\VRCT-sidecar-x86_64-pc-windows-msvc.exe src-tauri\target\release\VRCT-sidecar.exe
    if errorlevel 1 exit /b 1
)
REM tauri.conf.json's resources entry expects the production PyInstaller
REM onedir output (bin\_internal). Create an empty placeholder so the build
REM script's resource-path existence check doesn't fail under dev-fast
REM (PyInstaller skipped, .venv launched directly). Its contents are never
REM read during dev-fast (Python is launched straight from .venv).
if not exist src-tauri\bin\_internal mkdir src-tauri\bin\_internal
echo dev sidecar wrapper installed at src-tauri\bin\VRCT-sidecar-x86_64-pc-windows-msvc.exe
endlocal
