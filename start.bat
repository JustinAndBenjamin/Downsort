@echo off
setlocal
set "PYTHONPATH="
cd /d "C:\Users\Friedrich\Documents\Portfolio\GitHub\Downsort"
set "PYW=C:\Users\Friedrich\AppData\Local\Programs\Python\Python312\pythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" main.pyw
) else (
    start "" pythonw main.pyw
)