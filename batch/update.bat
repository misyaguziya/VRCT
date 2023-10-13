@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof

taskkill /im %1 /F
ping -n 2 127.0.0.1 > nul
del /f %1
ping -n 2 127.0.0.1 > nul
rename %2 %1
ping -n 2 127.0.0.1 > nul
if %3 == True (
    START "" %1
)