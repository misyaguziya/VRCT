@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof

set exe_name=%1
set folder_name=%2
set folder_tmp=%3
set restart=%4
set local_path=%~dp0

taskkill /im %exe_name% /F
ping -n 2 127.0.0.1 > nul
del /f %local_path%%exe_name%
rmdir /s /q %local_path%%folder_name%
xcopy %local_path%%folder_tmp% %local_path% /E /I
rmdir /s /q %local_path%%folder_tmp%

if %restart% == True (
    START "" %local_path%%exe_name%
)

del /f "%~dp0%~nx0"