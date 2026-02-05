@echo off
chcp 65001 >nul

REM Cambiar al directorio del script
cd /d "%~dp0"

echo ========================================
echo PREPARANDO CARPETA COMPLETA
echo ========================================
echo.
echo Directorio actual: %CD%
echo.

REM Intentar ejecutar Python primero
echo Ejecutando script Python...
echo.

python preparar_carpeta.py

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo ejecutar el script Python
    echo.
    echo Intentando metodo alternativo (batch)...
    echo.
    call copiar_para_otra_pc.bat
)

pause
