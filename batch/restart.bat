@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof

set name=%1
set local_path=%~dp0

taskkill /im %name% /F
ping -n 2 127.0.0.1 > nul
START "" "%local_path%%name%"
del /f "%~dp0%~nx0"