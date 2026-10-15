@echo off
chcp 65001 >nul
cd /d "%~dp0"
python main.py
echo.
echo (finished, press any key to close)
pause >nul
