@echo off
REM Script simple que siempre funciona
REM Cambia al directorio del script
cd /d "%~dp0"

echo ========================================
echo PREPARANDO CARPETA COMPLETA
echo ========================================
echo.
echo Directorio: %CD%
echo.

set "DESTINO=dist\mo_and_recipes_completo"

REM Limpiar carpeta anterior
if exist "%DESTINO%" (
    echo Limpiando carpeta anterior...
    rmdir /s /q "%DESTINO%"
)

REM Crear estructura
echo.
echo Creando carpetas...
mkdir "%DESTINO%" 2>nul
mkdir "%DESTINO%\.streamlit" 2>nul
mkdir "%DESTINO%\credentials" 2>nul
mkdir "%DESTINO%\pages" 2>nul
mkdir "%DESTINO%\shared" 2>nul

echo.
echo Copiando archivos...
echo.

REM Copiar ejecutable
if exist "dist\mo_and_recipes.exe" (
    copy "dist\mo_and_recipes.exe" "%DESTINO%\" >nul
    echo [OK] mo_and_recipes.exe
) else (
    echo [ERROR] dist\mo_and_recipes.exe no encontrado
    set "ERROR=1"
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

REM Copiar pages
if exist "pages\mo_and_recipes.py" (
    copy "pages\mo_and_recipes.py" "%DESTINO%\pages\" >nul
    echo [OK] pages\mo_and_recipes.py
) else (
    echo [ERROR] pages\mo_and_recipes.py no encontrado
    set "ERROR=1"
)

REM Copiar shared
if exist "shared" (
    for %%f in (shared\*.py) do (
        copy "%%f" "%DESTINO%\shared\" >nul
    )
    echo [OK] shared\
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

REM Copiar scripts de ayuda
if exist "EJECUTAR_CON_DEBUG.bat" (
    copy "EJECUTAR_CON_DEBUG.bat" "%DESTINO%\" >nul
    echo [OK] EJECUTAR_CON_DEBUG.bat
)

if exist "VERIFICAR_ARCHIVOS.bat" (
    copy "VERIFICAR_ARCHIVOS.bat" "%DESTINO%\" >nul
    echo [OK] VERIFICAR_ARCHIVOS.bat
)

if exist "SOLUCION_MULTIPLES_VENTANAS.md" (
    copy "SOLUCION_MULTIPLES_VENTANAS.md" "%DESTINO%\" >nul
    echo [OK] SOLUCION_MULTIPLES_VENTANAS.md
)

if exist "LEEME_PRIMERO.txt" (
    copy "LEEME_PRIMERO.txt" "%DESTINO%\" >nul
    echo [OK] LEEME_PRIMERO.txt
)

if exist "VERIFICAR_ARCHIVOS_V2.bat" (
    copy "VERIFICAR_ARCHIVOS_V2.bat" "%DESTINO%\" >nul
    echo [OK] VERIFICAR_ARCHIVOS_V2.bat
)

if exist "EJECUTAR_CON_DEBUG_V2.bat" (
    copy "EJECUTAR_CON_DEBUG_V2.bat" "%DESTINO%\" >nul
    echo [OK] EJECUTAR_CON_DEBUG_V2.bat
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
    echo Copia completada exitosamente!
    echo.
)
echo ========================================
echo.
echo Carpeta lista en: %DESTINO%
echo.
echo Siguiente paso:
echo 1. Ve a: %DESTINO%
echo 2. Clic derecho en la carpeta
echo 3. "Enviar a" -^> "Carpeta comprimida (en zip)"
echo.
pause
