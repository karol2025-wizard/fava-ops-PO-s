@echo off
echo ========================================
echo Haciendo push al repositorio de GitHub
echo ========================================
echo.

REM Verificar que Git esté instalado
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git no está instalado o no está en el PATH
    pause
    exit /b 1
)

echo Verificando remotes...
git remote -v
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: No hay remotes configurados
    echo Ejecuta primero: setup_git.bat
    pause
    exit /b 1
)

echo.
echo Haciendo push a GitHub...
echo Esto puede requerir autenticación.
echo.
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ¡Push completado exitosamente!
    echo Tu repositorio debería estar disponible en:
    echo https://github.com/karol2025-wizard/fava-ops-PO-s
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR: No se pudo hacer push
    echo Posibles causas:
    echo - No estás autenticado con GitHub
    echo - El repositorio no existe en GitHub
    echo - Problemas de conexión
    echo.
    echo Soluciones:
    echo 1. Verifica que el repositorio exista en GitHub
    echo 2. Autenticate con: git config --global user.name "Tu Nombre"
    echo 3. Usa un token de acceso personal si es necesario
    echo ========================================
)

echo.
pause


