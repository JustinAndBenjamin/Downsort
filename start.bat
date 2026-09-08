@echo off
setlocal
cd /d "%~dp0"
rem 1) Preferred: bundled portable exe (no Python/customtkinter needed)
if exist "dist\Downsort.exe" (
    start "" "dist\Downsort.exe"
    exit /b
)
rem 2) Fallback: system Python 3.12 pythonw (has customtkinter)
set "PYTHONPATH="
set "SYS=%APPDATA%\..\Local\Programs\Python\Python312\pythonw.exe"
if exist "%SYS%" (
    start "" "%SYS%" main.pyw
) else (
    start "" pythonw main.pyw
)
exit /b