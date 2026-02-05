@echo off
REM Cambiar al directorio del script
cd /d "%~dp0"

echo ========================================
echo Preparando carpeta completa para otra PC
echo ========================================
echo.
echo Directorio de trabajo: %CD%
echo.

set "DESTINO=dist\mo_and_recipes_completo"

echo Limpiando carpeta anterior (si existe)...
if exist "%DESTINO%" rmdir /s /q "%DESTINO%"

echo.
echo Creando estructura de carpetas...
mkdir "%DESTINO%"
mkdir "%DESTINO%\.streamlit"
mkdir "%DESTINO%\credentials"
mkdir "%DESTINO%\pages"
mkdir "%DESTINO%\shared"

echo.
echo Copiando archivos...
echo.

REM Copiar el ejecutable
if exist "dist\mo_and_recipes.exe" (
    copy "dist\mo_and_recipes.exe" "%DESTINO%\" >nul
    echo [OK] mo_and_recipes.exe
) else (
    echo [ERROR] No se encontro dist\mo_and_recipes.exe
    echo         Asegurate de haber ejecutado el build primero!
    echo.
    echo CONTINUANDO con los demas archivos...
    echo (Puedes copiar el .exe manualmente despues)
    echo.
    set "ERROR=1"
)

REM Copiar secrets.toml
if exist ".streamlit\secrets.toml" (
    copy ".streamlit\secrets.toml" "%DESTINO%\.streamlit\" >nul
    echo [OK] .streamlit\secrets.toml
) else (
    echo [ERROR] .streamlit\secrets.toml no encontrado - CRITICO
    set "ERROR=1"
)

REM Copiar credentials (todos los archivos)
if exist "credentials" (
    xcopy "credentials\*.*" "%DESTINO%\credentials\" /E /I /Y >nul
    echo [OK] credentials\ (carpeta completa)
) else (
    echo [WARN] Carpeta credentials no encontrada
)

REM Copiar pages/mo_and_recipes.py
if exist "pages\mo_and_recipes.py" (
    copy "pages\mo_and_recipes.py" "%DESTINO%\pages\" >nul
    echo [OK] pages\mo_and_recipes.py
) else (
    echo [ERROR] pages\mo_and_recipes.py no encontrado - CRITICO
    set "ERROR=1"
)

REM Copiar shared (todos los archivos .py, excluyendo __pycache__)
if exist "shared" (
    for %%f in (shared\*.py) do (
        copy "%%f" "%DESTINO%\shared\" >nul
    )
    echo [OK] shared\ (todos los archivos .py)
) else (
    echo [ERROR] Carpeta shared no encontrada - CRITICO
    set "ERROR=1"
)

REM Copiar config.py
if exist "config.py" (
    copy "config.py" "%DESTINO%\" >nul
    echo [OK] config.py
) else (
    echo [WARN] config.py no encontrado
)

REM Crear README en la carpeta
(
echo ========================================
echo MO AND RECIPES - Aplicacion Completa
echo ========================================
echo.
echo INSTRUCCIONES DE USO:
echo.
echo 1. Copia TODA esta carpeta a la PC destino
echo.
echo 2. Asegurate de que la estructura sea:
echo    mo_and_recipes_completo\
echo    ├── mo_and_recipes.exe
echo    ├── pages\
echo    │   └── mo_and_recipes.py
echo    ├── shared\
echo    │   └── [archivos .py]
echo    ├── .streamlit\
echo    │   └── secrets.toml
echo    ├── credentials\
echo    │   └── [archivos JSON]
echo    └── config.py
echo.
echo 3. Ejecuta mo_and_recipes.exe haciendo doble clic
echo.
echo 4. La aplicacion se abrira en: http://localhost:8501
echo.
echo 5. Si no se abre automaticamente, abre tu navegador
echo    y ve a esa direccion.
echo.
echo NOTAS:
echo - No muevas ni elimines ningun archivo de esta carpeta
echo - Todos los archivos deben estar en la misma carpeta
echo - La primera ejecucion puede tardar unos segundos
echo.
echo ========================================
) > "%DESTINO%\LEEME_PRIMERO.txt"

echo [OK] LEEME_PRIMERO.txt (instrucciones)

REM Copiar script de verificacion
copy "verificar_archivos_necesarios.bat" "%DESTINO%\" >nul 2>&1

echo.
echo ========================================
if defined ERROR (
    echo.
    echo ADVERTENCIA: Algunos archivos criticos faltan!
    echo Revisa los mensajes [ERROR] arriba.
    echo.
    echo El script continuo copiando los archivos disponibles.
    echo Si falta el ejecutable, ejecuta primero: python run_build.py
    echo.
) else (
    echo.
    echo Copia completada exitosamente!
    echo Todos los archivos necesarios estan listos.
    echo.
)
echo ========================================
echo.
echo Carpeta lista en: %DESTINO%
echo.
echo ESTRUCTURA CREADA:
echo.
dir /b /ad "%DESTINO%"
echo.
echo Puedes:
echo 1. Comprimir esta carpeta (ZIP/RAR)
echo 2. Copiarla a otra PC
echo 3. Descomprimirla
echo 4. Ejecutar mo_and_recipes.exe
echo.
echo IMPORTANTE: Copia TODA la carpeta, no solo el .exe
echo.
pause
