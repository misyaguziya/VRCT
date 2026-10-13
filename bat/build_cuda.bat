@echo off
setlocal
REM The Rust backend (CUDA edition): as build.bat, with cuBLAS and cuDNN in _internal (fetch-native --cuda).
if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
    echo Removing the dev-fast placeholder before the production build...
    rmdir /S /Q src-tauri\bin\_internal
    if exist src-tauri\bin\_internal\.vrct-dev-placeholder (
        echo ERROR: could not remove the dev-fast placeholder
        exit /b 1
    )
)
pushd native
cargo xtask fetch-native --cuda
if errorlevel 1 goto failed
cargo build --release -p vrct-backend --bin VRCT-sidecar
if errorlevel 1 goto failed
cargo xtask stage-sidecar --release --cuda --out ..\src-tauri\bin --exe-name VRCT-sidecar-x86_64-pc-windows-msvc.exe
if errorlevel 1 goto failed
popd
endlocal
exit /b 0
:failed
popd
exit /b 1
