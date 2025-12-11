@echo off
echo ========================================
echo Configurando Git para el proyecto
echo ========================================
echo.

REM Verificar que Git esté instalado
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git no está instalado o no está en el PATH
    echo Por favor instala Git desde https://git-scm.com/
    pause
    exit /b 1
)

echo [1/7] Inicializando repositorio Git...
git init
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: No se pudo inicializar Git
    pause
    exit /b 1
)

echo.
echo [2/7] Verificando .gitignore...
if not exist .gitignore (
    echo ERROR: No se encontró .gitignore
    pause
    exit /b 1
)

echo.
echo [3/7] Agregando archivos al staging...
git add .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: No se pudieron agregar archivos
    pause
    exit /b 1
)

echo.
echo [4/7] Verificando que archivos sensibles NO estén incluidos...
git status | findstr /C:"secrets.toml" >nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ADVERTENCIA: secrets.toml está en el staging!
    echo Esto NO debería pasar. Revisa .gitignore
    echo ========================================
    echo.
    pause
)

git status | findstr /C:"credentials" >nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ADVERTENCIA: Archivos de credentials están en el staging!
    echo Esto NO debería pasar. Revisa .gitignore
    echo ========================================
    echo.
    pause
)

echo.
echo [5/7] Mostrando estado (verifica que NO aparezcan archivos sensibles)...
git status

echo.
echo ========================================
echo VERIFICACION CRITICA:
echo Asegurate de que NO aparezcan:
echo - secrets.toml
echo - credentials/ o archivos .json de credenciales
echo ========================================
echo.
pause

echo.
echo [6/7] Haciendo commit inicial...
git commit -m "Initial commit: Fava Operations PO's system"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: No se pudo hacer commit
    pause
    exit /b 1
)

echo.
echo [7/7] Configurando remote de GitHub...
git remote add origin https://github.com/karol2025-wizard/fava-ops-PO-s.git
if %ERRORLEVEL% NEQ 0 (
    echo ADVERTENCIA: El remote ya existe o hubo un error
    echo Verificando remotes existentes...
    git remote -v
)

echo.
echo [8/8] Configurando branch main...
git branch -M main

echo.
echo ========================================
echo Configuracion completada!
echo.
echo Para hacer push al repositorio, ejecuta:
echo   git push -u origin main
echo.
echo O ejecuta este script nuevamente con:
echo   setup_git_push.bat
echo ========================================
echo.
pause


