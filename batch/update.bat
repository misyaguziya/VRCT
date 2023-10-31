@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof

set exe_name=%1
set exe_tmp_name=%2
set folder_name=%3
set folder_tmp_name=%4
set restart=%5

taskkill /im %exe_name% /F
ping -n 2 127.0.0.1 > nul
del /f %exe_name%
rename %exe_tmp_name% %exe_name%
rmdir /s /q %folder_name%
rename %folder_tmp_name% %folder_name%

if %restart% == True (
    START "" %exe_name%
)

del /f "%~dp0%~nx0"