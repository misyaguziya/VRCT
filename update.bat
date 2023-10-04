taskkill /im %1 /F
timeout 2
del /f %1
timeout 2
rename %2 %1
START "" %1