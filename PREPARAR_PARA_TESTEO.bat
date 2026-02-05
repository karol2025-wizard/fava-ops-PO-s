@echo off
REM Script para preparar archivos necesarios para testear mo_and_recipes en otro PC
REM Crea una carpeta portátil con solo lo necesario

cd /d "%~dp0"

echo ========================================
echo PREPARANDO PARA TESTEO EN OTRO PC
echo ========================================
echo.

set "DESTINO=testeo_mo_and_recipes"

REM Limpiar carpeta anterior
if exist "%DESTINO%" (
    echo Limpiando carpeta anterior...
    rmdir /s /q "%DESTINO%"
)

REM Crear estructura
echo.
echo Creando estructura de carpetas...
mkdir "%DESTINO%" 2>nul
mkdir "%DESTINO%\.streamlit" 2>nul
mkdir "%DESTINO%\credentials" 2>nul
mkdir "%DESTINO%\pages" 2>nul
mkdir "%DESTINO%\shared" 2>nul

echo.
echo Copiando archivos necesarios...
echo.

REM Copiar página mo_and_recipes
if exist "pages\mo_and_recipes.py" (
    copy "pages\mo_and_recipes.py" "%DESTINO%\pages\" >nul
    echo [OK] pages\mo_and_recipes.py
) else (
    echo [ERROR] pages\mo_and_recipes.py no encontrado
    set "ERROR=1"
)

REM Copiar shared (todos los .py)
if exist "shared" (
    for %%f in (shared\*.py) do (
        copy "%%f" "%DESTINO%\shared\" >nul
    )
    echo [OK] shared\ (todos los módulos)
) else (
    echo [ERROR] shared\ no encontrada
    set "ERROR=1"
)

REM Copiar config.py
if exist "config.py" (
    copy "config.py" "%DESTINO%\" >nul
    echo [OK] config.py
) else (
    echo [WARN] config.py no encontrado
)

REM Copiar secrets.toml
if exist ".streamlit\secrets.toml" (
    copy ".streamlit\secrets.toml" "%DESTINO%\.streamlit\" >nul
    echo [OK] .streamlit\secrets.toml
) else (
    echo [ERROR] .streamlit\secrets.toml no encontrado
    set "ERROR=1"
)

REM Copiar credentials
if exist "credentials" (
    xcopy "credentials\*.*" "%DESTINO%\credentials\" /E /I /Y /Q >nul
    echo [OK] credentials\
) else (
    echo [WARN] credentials\ no encontrada
)

REM Copiar requirements.txt
if exist "requirements.txt" (
    copy "requirements.txt" "%DESTINO%\" >nul
    echo [OK] requirements.txt
) else (
    echo [WARN] requirements.txt no encontrado
)

REM Copiar script de ejecución
if exist "EJECUTAR.bat" (
    copy "EJECUTAR.bat" "%DESTINO%\" >nul
    echo [OK] EJECUTAR.bat
) else (
    echo @echo off > "%DESTINO%\EJECUTAR.bat"
    echo streamlit run pages\mo_and_recipes.py >> "%DESTINO%\EJECUTAR.bat"
    echo [OK] EJECUTAR.bat (creado)
)

REM Copiar guía
if exist "OPCIONES_TESTEO_MO_AND_RECIPES.md" (
    copy "OPCIONES_TESTEO_MO_AND_RECIPES.md" "%DESTINO%\" >nul
    echo [OK] OPCIONES_TESTEO_MO_AND_RECIPES.md
)

echo.
echo ========================================
if defined ERROR (
    echo.
    echo ADVERTENCIA: Algunos archivos faltan!
    echo Revisa los mensajes [ERROR] arriba.
    echo.
) else (
    echo.
    echo Preparación completada exitosamente!
    echo.
)
echo ========================================
echo.
echo Carpeta lista en: %DESTINO%
echo.
echo OPCIONES PARA USAR EN OTRO PC:
echo.
echo OPCION 1 - Con Python instalado:
echo   1. Copia la carpeta %DESTINO% al otro PC
echo   2. Instala Python 3.8+
echo   3. Instala dependencias: pip install -r requirements.txt
echo   4. Ejecuta: streamlit run pages\mo_and_recipes.py
echo    O usa: EJECUTAR.bat
echo.
echo OPCION 2 - Con el .exe:
echo   1. Ejecuta PREPARAR_CARPETA_SIMPLE.bat primero
echo   2. Copia dist\mo_and_recipes_completo al otro PC
echo   3. Ejecuta mo_and_recipes.exe
echo.
echo ========================================
echo.
pause
