@echo off
setlocal
cargo build --release --manifest-path utils\dev_sidecar\Cargo.toml
if errorlevel 1 exit /b 1
if not exist src-tauri\bin mkdir src-tauri\bin
copy /Y utils\dev_sidecar\target\release\VRCT-sidecar-x86_64-pc-windows-msvc.exe src-tauri\bin\VRCT-sidecar-x86_64-pc-windows-msvc.exe
if errorlevel 1 exit /b 1
echo dev sidecar wrapper installed at src-tauri\bin\VRCT-sidecar-x86_64-pc-windows-msvc.exe
endlocal
