@echo off
setlocal
chcp 65001 >nul
title Concept Learning Loop

set "APP_DIR=C:\Users\cashrus\Documents\Codex\.kb\app"
set "PYTHON_EXE=C:\Python314\python.exe"
set "PKG_DIR=C:\Users\cashrus\Documents\Codex\.tools\python-packages"

if not exist "%PYTHON_EXE%" (
    echo Python not found: %PYTHON_EXE%
    pause
    exit /b 2
)

if not exist "%PKG_DIR%\streamlit\__init__.py" (
    echo Streamlit dependencies not found: %PKG_DIR%
    pause
    exit /b 3
)

set "PYTHONPATH=%PKG_DIR%"
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
cd /d "%APP_DIR%"

echo Starting Concept Learning Loop...
echo URL: http://localhost:8517
echo Close this window to stop the server.
echo.

"%PYTHON_EXE%" -m streamlit run "%APP_DIR%\app_v3_demo.py" --global.developmentMode false --server.headless false --server.port 8517 --browser.gatherUsageStats false
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Streamlit stopped. Exit code: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
