@echo off
REM Script para verificar que todos los archivos necesarios estén presentes
REM Úsalo antes de ejecutar la aplicación en el otro computador

cd /d "%~dp0"

echo ========================================
echo VERIFICACION DE ARCHIVOS NECESARIOS
echo ========================================
echo.
echo Directorio: %CD%
echo.

set "ERRORES=0"
set "ADVERTENCIAS=0"

echo Verificando estructura de archivos...
echo.

REM Verificar ejecutable
if exist "mo_and_recipes.exe" (
    echo [OK] mo_and_recipes.exe
) else (
    echo [ERROR] mo_and_recipes.exe - NO ENCONTRADO
    set /a ERRORES+=1
)

echo.

REM Verificar estructura de carpetas
echo Verificando carpetas...
if exist "pages" (
    echo [OK] Carpeta pages\
    if exist "pages\mo_and_recipes.py" (
        echo     [OK] pages\mo_and_recipes.py
    ) else (
        echo     [ERROR] pages\mo_and_recipes.py - NO ENCONTRADO
        set /a ERRORES+=1
    )
) else (
    echo [ERROR] Carpeta pages\ - NO ENCONTRADA
    set /a ERRORES+=1
)

if exist "shared" (
    echo [OK] Carpeta shared\
    dir /b shared\*.py >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo     [OK] Archivos .py encontrados en shared\
    ) else (
        echo     [WARN] No se encontraron archivos .py en shared\
        set /a ADVERTENCIAS+=1
    )
) else (
    echo [ERROR] Carpeta shared\ - NO ENCONTRADA
    set /a ERRORES+=1
)

if exist ".streamlit" (
    echo [OK] Carpeta .streamlit\
    if exist ".streamlit\secrets.toml" (
        echo     [OK] .streamlit\secrets.toml
    ) else (
        echo     [ERROR] .streamlit\secrets.toml - NO ENCONTRADO
        set /a ERRORES+=1
    )
) else (
    echo [ERROR] Carpeta .streamlit\ - NO ENCONTRADA
    set /a ERRORES+=1
)

if exist "credentials" (
    echo [OK] Carpeta credentials\
    dir /b credentials\*.json >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo     [OK] Archivos JSON encontrados en credentials\
    ) else (
        echo     [WARN] No se encontraron archivos JSON en credentials\
        set /a ADVERTENCIAS+=1
    )
) else (
    echo [WARN] Carpeta credentials\ - NO ENCONTRADA (puede ser necesario)
    set /a ADVERTENCIAS+=1
)

if exist "config.py" (
    echo [OK] config.py
) else (
    echo [WARN] config.py - NO ENCONTRADO (puede ser necesario)
    set /a ADVERTENCIAS+=1
)

echo.
echo ========================================
echo RESUMEN
echo ========================================
echo.
if %ERRORES%==0 (
    echo [OK] Todos los archivos críticos están presentes
) else (
    echo [ERROR] Se encontraron %ERRORES% error(es) crítico(s)
    echo         La aplicación NO funcionará sin estos archivos
)

if %ADVERTENCIAS% GTR 0 (
    echo [WARN] Se encontraron %ADVERTENCIAS% advertencia(s)
    echo        La aplicación puede funcionar, pero puede tener problemas
)

echo.
echo ========================================
echo.

if %ERRORES% GTR 0 (
    echo SOLUCION:
    echo 1. Asegúrate de copiar TODA la carpeta mo_and_recipes_completo
    echo 2. Verifica que no falten archivos
    echo 3. Ejecuta este script de nuevo para verificar
    echo.
    pause
    exit /b 1
) else (
    echo La estructura de archivos parece correcta.
    echo Puedes intentar ejecutar la aplicación.
    echo.
    echo Para ejecutar con modo debug (ver errores):
    echo   EJECUTAR_CON_DEBUG.bat
    echo.
    echo Para ejecutar normalmente:
    echo   mo_and_recipes.exe
    echo.
    pause
)
