@echo off
setlocal
cd /d "%~dp0"

echo Iniciando Streamlit (app completa con MO Record Insert)...
echo Usando el Python del venv del proyecto.
echo.
set PY=venv\Scripts\python.exe
if not exist "%PY%" (
    echo ERROR: No se encuentra venv\Scripts\python.exe en esta carpeta.
    goto :end
)
echo Cuando abra el navegador, entra a MO Record Insert.
echo NO cierres esta ventana o se apagara la app.
echo.
"%PY%" -m streamlit run home.py --server.port=8504
if errorlevel 1 (
    echo.
    echo Hubo un error al iniciar. Revisa el mensaje de arriba.
)
:end
echo.
pause
