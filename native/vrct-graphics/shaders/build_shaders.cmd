@echo off
rem Regenerate the committed shader blobs (no shader compiler at runtime or in cargo build).
setlocal
set FXC=%FXC%
if "%FXC%"=="" set FXC=C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\fxc.exe
pushd "%~dp0"
"%FXC%" /nologo /O3 /T vs_4_0 /E vs_main /Fo compose_vs.cso compose.hlsl || exit /b 1
"%FXC%" /nologo /O3 /T ps_4_0 /E ps_main /Fo compose_ps.cso compose.hlsl || exit /b 1
popd
