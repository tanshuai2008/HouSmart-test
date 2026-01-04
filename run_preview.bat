@echo off
echo Starting HouSmart Offline Preview...
cd /d "%~dp0"

REM Use absolute python path to ensure we use the correct environment
set PYTHON_EXE=C:\Users\admin\AppData\Local\Programs\Python\Python313\python.exe

echo Using Python: %PYTHON_EXE%

"%PYTHON_EXE%" -m streamlit run app.py --server.port 8503 --server.headless=true

if errorlevel 1 (
    echo.
    echo Error occurred.
    pause
)
pause
