@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo Cambiando al directorio: %CD%
echo.
echo Activando entorno virtual y ejecutando Streamlit...
echo.
echo ========================================
echo IMPORTANTE: Para acceder desde otras PCs
echo ========================================
echo.

REM Obtener IP local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "LOCAL_IP=%%a"
    set "LOCAL_IP=!LOCAL_IP: =!"
    goto :found
)
:found

if defined LOCAL_IP (
    echo El servidor estara disponible en:
    echo   - Local: http://localhost:8502/
    echo   - Red:   http://!LOCAL_IP!:8502/
    echo.
    echo Solo se muestra MO and Recipes - sin menu de navegacion.
) else (
    echo No se pudo obtener la IP local automaticamente.
    echo Ejecuta 'ipconfig' y usa: http://TU_IP:8502/
)
echo.
echo ========================================
echo.
call venv\Scripts\python.exe -m streamlit run mo_only.py --server.address=0.0.0.0 --server.port=8502
pause
