@echo off
echo ========================================
echo Build de mo_and_recipes.exe
echo ========================================
echo.

REM Verificar si PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller no está instalado. Instalando...
    pip install pyinstaller
    if errorlevel 1 (
        echo Error al instalar PyInstaller
        pause
        exit /b 1
    )
)

echo.
echo Limpiando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo Construyendo ejecutable...
pyinstaller mo_and_recipes.spec --clean

if errorlevel 1 (
    echo.
    echo Error al construir el ejecutable
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completado exitosamente!
echo ========================================
echo.
echo El ejecutable se encuentra en: dist\mo_and_recipes.exe
echo.
echo IMPORTANTE: Para usar el .exe en otra PC, necesitas:
echo 1. Copiar el archivo dist\mo_and_recipes.exe
echo 2. Copiar la carpeta dist\mo_and_recipes (si existe) con todos sus archivos
echo 3. Asegurarte de que la PC destino tenga las credenciales necesarias
echo    (archivo .streamlit/secrets.toml o configurar las variables de entorno)
echo.
pause
