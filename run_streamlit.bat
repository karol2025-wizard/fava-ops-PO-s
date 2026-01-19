@echo off
cd /d "%~dp0"
echo Cambiando al directorio: %CD%
echo.
echo Activando entorno virtual y ejecutando Streamlit...
call venv\Scripts\python.exe -m streamlit run home.py
pause
