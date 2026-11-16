@echo off
rem Clique duas vezes neste arquivo para desligar o Gerenciador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desligar.ps1"
echo.
pause
