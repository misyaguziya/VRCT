set "current_dir=%CD%"
taskkill /im VRCT.exe /F
timeout 2
for /d /r %%i in (*) do (
    set "folder=%%i"
    set "folder=!folder:%current_dir%\=!"
    if "!folder!" neq "\tmp\" (
        rd /s /q "%%i"
    )
)
timeout 2
xcopy /s /e /y ".\tmp\VRCT\*" ".\"
timeout 2
for /f "delims=" %%i in ('dir /b /s /ad "%current_dir%\tmp"') do rd /s /q "%%i"
VRCT.exe