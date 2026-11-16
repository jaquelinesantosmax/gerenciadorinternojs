@echo off
rem Clique duas vezes neste arquivo para rodar todos os testes automáticos.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0testar.ps1"
echo.
pause
