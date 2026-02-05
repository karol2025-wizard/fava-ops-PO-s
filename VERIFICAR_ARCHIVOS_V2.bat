@echo off
REM Script mejorado que mantiene la ventana abierta SIEMPRE
REM Úsalo antes de ejecutar la aplicación en el otro computador

REM Forzar que la ventana se mantenga abierta
if not "%1"=="keepopen" (
    cmd /k "%~f0" keepopen
    exit /b
)

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Limpiar pantalla
cls

echo ========================================
echo VERIFICACION DE ARCHIVOS NECESARIOS
echo ========================================
echo.
echo Directorio: %CD%
echo.
echo Por favor espera mientras verifico los archivos...
echo.

set "ERRORES=0"
set "ADVERTENCIAS=0"

REM Verificar ejecutable
echo [1/6] Verificando ejecutable...
if exist "mo_and_recipes.exe" (
    echo     [OK] mo_and_recipes.exe encontrado
) else (
    echo     [ERROR] mo_and_recipes.exe - NO ENCONTRADO
    set /a ERRORES+=1
)
echo.

REM Verificar pages
echo [2/6] Verificando carpeta pages...
if exist "pages" (
    echo     [OK] Carpeta pages\ encontrada
    if exist "pages\mo_and_recipes.py" (
        echo     [OK] pages\mo_and_recipes.py encontrado
    ) else (
        echo     [ERROR] pages\mo_and_recipes.py - NO ENCONTRADO
        set /a ERRORES+=1
    )
) else (
    echo     [ERROR] Carpeta pages\ - NO ENCONTRADA
    set /a ERRORES+=1
)
echo.

REM Verificar shared
echo [3/6] Verificando carpeta shared...
if exist "shared" (
    echo     [OK] Carpeta shared\ encontrada
    dir /b shared\*.py >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo     [OK] Archivos .py encontrados en shared\
    ) else (
        echo     [WARN] No se encontraron archivos .py en shared\
        set /a ADVERTENCIAS+=1
    )
) else (
    echo     [ERROR] Carpeta shared\ - NO ENCONTRADA
    set /a ERRORES+=1
)
echo.

REM Verificar .streamlit
echo [4/6] Verificando carpeta .streamlit...
if exist ".streamlit" (
    echo     [OK] Carpeta .streamlit\ encontrada
    if exist ".streamlit\secrets.toml" (
        echo     [OK] .streamlit\secrets.toml encontrado
    ) else (
        echo     [ERROR] .streamlit\secrets.toml - NO ENCONTRADO
        set /a ERRORES+=1
    )
) else (
    echo     [ERROR] Carpeta .streamlit\ - NO ENCONTRADA
    set /a ERRORES+=1
)
echo.

REM Verificar credentials
echo [5/6] Verificando carpeta credentials...
if exist "credentials" (
    echo     [OK] Carpeta credentials\ encontrada
    dir /b credentials\*.json >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo     [OK] Archivos JSON encontrados en credentials\
    ) else (
        echo     [WARN] No se encontraron archivos JSON en credentials\
        set /a ADVERTENCIAS+=1
    )
) else (
    echo     [WARN] Carpeta credentials\ - NO ENCONTRADA (puede ser necesario)
    set /a ADVERTENCIAS+=1
)
echo.

REM Verificar config.py
echo [6/6] Verificando config.py...
if exist "config.py" (
    echo     [OK] config.py encontrado
) else (
    echo     [WARN] config.py - NO ENCONTRADO (puede ser necesario)
    set /a ADVERTENCIAS+=1
)
echo.

echo ========================================
echo RESUMEN
echo ========================================
echo.

if %ERRORES%==0 (
    echo [OK] Todos los archivos críticos están presentes
    echo.
    echo Puedes ejecutar la aplicación ahora.
    echo.
) else (
    echo [ERROR] Se encontraron %ERRORES% error(es) crítico(s)
    echo         La aplicación NO funcionará sin estos archivos
    echo.
    echo SOLUCION:
    echo 1. Asegúrate de copiar TODA la carpeta mo_and_recipes_completo
    echo 2. Verifica que no falten archivos
    echo 3. Ejecuta este script de nuevo para verificar
    echo.
)

if %ADVERTENCIAS% GTR 0 (
    echo [WARN] Se encontraron %ADVERTENCIAS% advertencia(s)
    echo        La aplicación puede funcionar, pero puede tener problemas
    echo.
)

echo ========================================
echo.
echo OPCIONES:
echo.
echo 1. Para ejecutar con modo debug (ver errores):
echo    EJECUTAR_CON_DEBUG.bat
echo.
echo 2. Para ejecutar normalmente:
echo    mo_and_recipes.exe
echo.
echo 3. Para cerrar esta ventana:
echo    Escribe "exit" y presiona Enter
echo.
echo ========================================

REM Mantener la ventana abierta
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
