@echo off
echo ========================================
echo CONFIGURAR FIREWALL PARA STREAMLIT
echo ========================================
echo.
echo Este script agregara una regla al firewall de Windows
echo para permitir conexiones en el puerto 8504.
echo.
echo IMPORTANTE: Debes ejecutar este script como Administrador
echo.
pause

REM Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: Este script debe ejecutarse como Administrador
    echo.
    echo Solucion:
    echo 1. Clic derecho en este archivo
    echo 2. Selecciona "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo.
echo Agregando regla al firewall...
echo.

REM Agregar regla de firewall
netsh advfirewall firewall add rule name="Streamlit MO and Recipes" dir=in action=allow protocol=TCP localport=8504

if %errorLevel% equ 0 (
    echo.
    echo [OK] Regla de firewall agregada exitosamente
    echo.
    echo El puerto 8504 ahora esta abierto para conexiones entrantes.
    echo Otras PCs en tu red pueden acceder a la aplicacion.
) else (
    echo.
    echo [ERROR] No se pudo agregar la regla de firewall
    echo.
    echo Puedes agregarla manualmente:
    echo 1. Abre "Firewall de Windows Defender"
    echo 2. Configuracion avanzada
    echo 3. Reglas de entrada -^> Nueva regla
    echo 4. Puerto -^> TCP -^> 8504
    echo 5. Permitir conexion
)

echo.
pause
