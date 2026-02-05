@echo off
REM Script simple para ejecutar mo_and_recipes directamente
REM Úsalo después de copiar los archivos al otro PC

cd /d "%~dp0"

echo ========================================
echo Ejecutando MO and Recipes
echo ========================================
echo.

REM Verificar que existe la página
if not exist "pages\mo_and_recipes.py" (
    echo [ERROR] No se encuentra pages\mo_and_recipes.py
    echo.
    echo Asegúrate de estar en la carpeta correcta.
    pause
    exit /b 1
)

REM Ejecutar Streamlit
echo Iniciando Streamlit...
echo.
echo La aplicación se abrirá en: http://localhost:8501
echo.
echo Presiona Ctrl+C para detener la aplicación.
echo.

streamlit run pages\mo_and_recipes.py
