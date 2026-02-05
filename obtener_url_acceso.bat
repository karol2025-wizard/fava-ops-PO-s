@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo OBTENER URL PARA ACCESO DESDE OTRAS PCs
echo ========================================
echo.

REM Obtener IP local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "IP=%%a"
    set "IP=!IP: =!"
    goto :found
)

:found
if not defined IP (
    echo ERROR: No se pudo obtener la IP local
    echo.
    echo Por favor, ejecuta manualmente: ipconfig
    echo Y busca tu "Direccion IPv4"
    pause
    exit /b 1
)

echo Tu IP local es: !IP!
echo.
echo ========================================
echo URLs DE ACCESO:
echo ========================================
echo.
echo Para acceder desde ESTA PC:
echo   http://localhost:8504/
echo   http://localhost:8504/mo_and_recipes
echo.
echo Para acceder desde OTRAS PCs en la red:
echo   http://!IP!:8504/
echo   http://!IP!:8504/mo_and_recipes
echo.
echo ========================================
echo IMPORTANTE:
echo ========================================
echo 1. Asegurate de que el servidor Streamlit este corriendo
echo 2. Asegurate de que el firewall permita conexiones en el puerto 8504
echo 3. Las otras PCs deben estar en la misma red local
echo.
echo ========================================
echo.

REM Copiar URL al portapapeles (requiere PowerShell)
set "URL_RED=http://!IP!:8504/mo_and_recipes"
echo Copiando URL al portapapeles...
powershell -Command "Set-Clipboard -Value '!URL_RED!'"
if errorlevel 1 (
    echo [AVISO] No se pudo copiar al portapapeles. Copia manualmente la URL de arriba.
) else (
    echo [OK] URL copiada al portapapeles: !URL_RED!
)
echo.
echo Verificacion: pega en el navegador con Ctrl+V para comprobar.
echo.

pause

