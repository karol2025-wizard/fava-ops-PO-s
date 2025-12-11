@echo off
echo ========================================
echo Verificando estado de Git
echo ========================================
echo.

if exist .git (
    echo [OK] Repositorio Git inicializado
    echo.
    echo Verificando remotes configurados...
    git remote -v
    echo.
    echo Verificando estado del repositorio...
    git status
    echo.
    echo Verificando ultimo commit...
    git log --oneline -1 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ========================================
        echo Estado: Repositorio Git configurado
        echo ========================================
    ) else (
        echo.
        echo ========================================
        echo Estado: Git inicializado pero sin commits
        echo ========================================
    )
) else (
    echo [ERROR] Repositorio Git NO inicializado
    echo.
    echo Para inicializar, ejecuta:
    echo   git init
    echo.
    echo ========================================
    echo Estado: NO conectado con GitHub
    echo ========================================
)

echo.
pause

