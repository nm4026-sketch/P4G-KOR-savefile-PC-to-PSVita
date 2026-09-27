@echo off
setlocal
cd /d "%~dp0"

where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw "%~dp0P4G_Steam_to_KR_Vita_Final_Converter_v1.0.pyw"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0P4G_Steam_to_KR_Vita_Final_Converter_v1.0.pyw"
    exit /b 0
)

where py >nul 2>nul
if %errorlevel%==0 (
    py "%~dp0P4G_Steam_to_KR_Vita_Final_Converter_v1.0.pyw"
    exit /b %errorlevel%
)

echo Python 3.9 or newer was not found.
echo Install Python from https://www.python.org/downloads/
echo and enable "Add python.exe to PATH".
pause
