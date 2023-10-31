@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof

set exe_name=%1
set folder_name=%2
set folder_tmp=%3
set restart=%4

taskkill /im %exe_name% /F
ping -n 2 127.0.0.1 > nul
del /f %exe_name%
rmdir /s /q %folder_name%
move /Y %exe_tmp_name%\* .\
rmdir /s /q %exe_tmp_name%

if %restart% == True (
    START "" %exe_name%
)

del /f "%~dp0%~nx0"