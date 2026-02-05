@echo off
REM Script para ejecutar mo_and_recipes.exe y mantener la ventana abierta para ver errores
REM Úsalo en el otro computador para diagnosticar problemas

cd /d "%~dp0"

echo ========================================
echo EJECUTANDO MO AND RECIPES (MODO DEBUG)
echo ========================================
echo.
echo Directorio actual: %CD%
echo.

REM Verificar archivos necesarios
echo Verificando archivos necesarios...
echo.

set "ERROR=0"

if not exist "mo_and_recipes.exe" (
    echo [ERROR] mo_and_recipes.exe no encontrado
    set "ERROR=1"
) else (
    echo [OK] mo_and_recipes.exe encontrado
)

if not exist "pages\mo_and_recipes.py" (
    echo [ERROR] pages\mo_and_recipes.py no encontrado
    set "ERROR=1"
) else (
    echo [OK] pages\mo_and_recipes.py encontrado
)

if not exist "shared" (
    echo [ERROR] Carpeta shared\ no encontrada
    set "ERROR=1"
) else (
    echo [OK] Carpeta shared\ encontrada
)

if not exist ".streamlit\secrets.toml" (
    echo [ERROR] .streamlit\secrets.toml no encontrado
    set "ERROR=1"
) else (
    echo [OK] .streamlit\secrets.toml encontrado
)

if not exist "config.py" (
    echo [WARN] config.py no encontrado (puede ser opcional)
) else (
    echo [OK] config.py encontrado
)

if not exist "credentials" (
    echo [WARN] Carpeta credentials\ no encontrada (puede ser necesario)
) else (
    echo [OK] Carpeta credentials\ encontrada
)

echo.
echo ========================================
if defined ERROR (
    echo.
    echo ERROR: Faltan archivos necesarios!
    echo Revisa los mensajes [ERROR] arriba.
    echo.
    echo Presiona cualquier tecla para salir...
    pause >nul
    exit /b 1
)
echo ========================================
echo.
echo Iniciando aplicación...
echo.
echo IMPORTANTE:
echo - Esta ventana mostrará todos los errores
echo - NO la cierres hasta que veas un error o cierres la app
echo - La aplicación se abrirá en: http://localhost:8501
echo - Si se abren múltiples ventanas, cierra las extras
echo.
echo Presiona Ctrl+C para detener la aplicación
echo.
echo ========================================
echo.

REM Ejecutar el .exe y capturar la salida
mo_and_recipes.exe 2>&1

REM Si el .exe termina, mostrar el código de salida
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo ========================================
echo La aplicación terminó con código: %EXIT_CODE%
echo ========================================
echo.
echo Si hubo un error, deberías haberlo visto arriba.
echo.
pause
