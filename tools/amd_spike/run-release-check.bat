@echo off
REM Double-click this to run ONLY the release checks (2-3 minutes).
REM The full run is VRCT-AMD-Check.exe on its own, and takes much longer.
cd /d "%~dp0"
"%~dp0VRCT-AMD-Check.exe" --stage d
echo.
echo Finished. Please send amd_spike_report.txt from this folder.
pause
