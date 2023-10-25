@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof

set name=%1

taskkill /im %name% /F

START "" %name%