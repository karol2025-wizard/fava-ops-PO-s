@echo off
echo Organizando archivos de documentacion...

REM Crear carpeta docs si no existe
if not exist "docs" mkdir docs

REM Mover archivos .md excepto README.md
for %%f in (*.md) do (
    if not "%%f"=="README.md" (
        move "%%f" "docs\" >nul 2>&1
        echo Movido: %%f
    )
)

REM Mover archivos .txt de documentacion
if exist "COMANDOS_RAPIDOS.txt" (
    move "COMANDOS_RAPIDOS.txt" "docs\" >nul 2>&1
    echo Movido: COMANDOS_RAPIDOS.txt
)

if exist "INSTRUCCIONES_GIT.txt" (
    move "INSTRUCCIONES_GIT.txt" "docs\" >nul 2>&1
    echo Movido: INSTRUCCIONES_GIT.txt
)

echo.
echo ¡Organizacion completada!
echo Todos los archivos de documentacion estan ahora en la carpeta 'docs'
pause
