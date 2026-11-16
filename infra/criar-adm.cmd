@echo off
rem Clique duas vezes para cadastrar um ADM da plataforma (uso na instalação).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0criar-adm.ps1"
echo.
pause
