@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof

set exe_name=%1
set folder_name=%2
set tmp_name=%3
set restart=%4

taskkill /im %exe_name% /F
ping -n 2 127.0.0.1 > nul
del /f %exe_name%
rmdir /s %folder_name%
move %tmp_name%\* .\
del /f %tmp_name%
if %restart% == True (
    START "" %exe_name%
)