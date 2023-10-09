@echo off

taskkill /im %1 /F
START "" %1