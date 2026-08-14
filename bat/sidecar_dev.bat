@echo off
setlocal
cargo build --release --manifest-path utils\dev_sidecar\Cargo.toml
if errorlevel 1 exit /b 1
if not exist src-tauri\bin mkdir src-tauri\bin
copy /Y utils\dev_sidecar\target\release\VRCT-sidecar-x86_64-pc-windows-msvc.exe src-tauri\bin\VRCT-sidecar-x86_64-pc-windows-msvc.exe
if errorlevel 1 exit /b 1
REM tauri.conf.json の resources 定義は本番の PyInstaller onedir 出力 (bin\_internal)
REM を要求するため、dev-fast (PyInstaller をスキップして .venv 直起動する高速ループ)
REM でも build script が resource path 存在チェックに失敗しないよう空ディレクトリを用意する。
REM 中身は dev-fast 実行時には参照されない (Python は .venv から直接起動される)。
if not exist src-tauri\bin\_internal mkdir src-tauri\bin\_internal
echo dev sidecar wrapper installed at src-tauri\bin\VRCT-sidecar-x86_64-pc-windows-msvc.exe
endlocal
