@echo off
chcp 65001 >nul
echo ========================================
echo VERIFICACION ANTES DE COPIAR
echo ========================================
echo.
echo Verificando que todos los archivos esten listos...
echo.

set "CARPETA=dist\mo_and_recipes_completo"
set "ERRORES=0"

if not exist "%CARPETA%" (
    echo [ERROR] La carpeta %CARPETA% no existe!
    echo.
    echo Ejecuta primero: EJECUTAR_AQUI.bat
    echo.
    pause
    exit /b 1
)

echo Verificando archivos en: %CARPETA%
echo.

REM Verificar ejecutable
if exist "%CARPETA%\mo_and_recipes.exe" (
    echo [OK] mo_and_recipes.exe
) else (
    echo [ERROR] mo_and_recipes.exe - FALTANTE
    set /a ERRORES+=1
)

REM Verificar pages
if exist "%CARPETA%\pages\mo_and_recipes.py" (
    echo [OK] pages\mo_and_recipes.py
) else (
    echo [ERROR] pages\mo_and_recipes.py - FALTANTE
    set /a ERRORES+=1
)

REM Verificar shared
if exist "%CARPETA%\shared" (
    set /a archivos=0
    for %%f in ("%CARPETA%\shared\*.py") do set /a archivos+=1
    if !archivos! gtr 0 (
        echo [OK] shared\ (!archivos! archivos .py)
    ) else (
        echo [ERROR] shared\ - Sin archivos .py
        set /a ERRORES+=1
    )
) else (
    echo [ERROR] shared\ - FALTANTE
    set /a ERRORES+=1
)

REM Verificar secrets.toml
if exist "%CARPETA%\.streamlit\secrets.toml" (
    echo [OK] .streamlit\secrets.toml
) else (
    echo [ERROR] .streamlit\secrets.toml - FALTANTE
    set /a ERRORES+=1
)

REM Verificar credentials
if exist "%CARPETA%\credentials" (
    set /a archivos=0
    for %%f in ("%CARPETA%\credentials\*.json") do set /a archivos+=1
    if !archivos! gtr 0 (
        echo [OK] credentials\ (!archivos! archivos JSON)
    ) else (
        echo [WARN] credentials\ - Sin archivos JSON
    )
) else (
    echo [WARN] credentials\ - No encontrada
)

REM Verificar config.py
if exist "%CARPETA%\config.py" (
    echo [OK] config.py
) else (
    echo [WARN] config.py - No encontrado
)

echo.
echo ========================================
if %ERRORES%==0 (
    echo.
    echo [OK] TODOS LOS ARCHIVOS CRITICOS ESTAN PRESENTES!
    echo.
    echo Puedes comprimir la carpeta y copiarla a otra PC.
    echo.
    echo Siguiente paso:
    echo 1. Ve a: %CARPETA%
    echo 2. Clic derecho en la carpeta
    echo 3. "Enviar a" -^> "Carpeta comprimida (en zip)"
    echo.
) else (
    echo.
    echo [ERROR] FALTAN %ERRORES% ARCHIVO(S) CRITICO(S)!
    echo.
    echo Ejecuta primero: EJECUTAR_AQUI.bat
    echo O: copiar_para_otra_pc.bat
    echo.
)
echo ========================================
echo.
pause
