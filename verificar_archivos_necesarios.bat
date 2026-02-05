@echo off
echo ========================================
echo Verificando archivos necesarios
echo ========================================
echo.

set "ERROR=0"

echo Verificando estructura de archivos...
echo.

REM Verificar pages/mo_and_recipes.py
if exist "pages\mo_and_recipes.py" (
    echo [OK] pages\mo_and_recipes.py
) else (
    echo [ERROR] pages\mo_and_recipes.py - FALTANTE
    set "ERROR=1"
)

REM Verificar shared
if exist "shared" (
    echo [OK] shared\ (carpeta)
) else (
    echo [ERROR] shared\ - FALTANTE
    set "ERROR=1"
)

REM Verificar config.py
if exist "config.py" (
    echo [OK] config.py
) else (
    echo [WARN] config.py - No encontrado (puede ser necesario)
)

REM Verificar .streamlit/secrets.toml
if exist ".streamlit\secrets.toml" (
    echo [OK] .streamlit\secrets.toml
) else (
    echo [ERROR] .streamlit\secrets.toml - FALTANTE (CRITICO)
    set "ERROR=1"
)

REM Verificar credentials
if exist "credentials" (
    echo [OK] credentials\ (carpeta)
) else (
    echo [WARN] credentials\ - No encontrado (puede ser necesario)
)

echo.
echo ========================================

if %ERROR%==1 (
    echo.
    echo ERRORES ENCONTRADOS!
    echo Por favor, asegurate de copiar todos los archivos necesarios.
    echo.
    echo Revisa el archivo COMO_USAR_EN_OTRA_PC.txt para mas detalles.
) else (
    echo.
    echo Todos los archivos necesarios estan presentes!
    echo Puedes ejecutar mo_and_recipes.exe
)

echo.
pause
