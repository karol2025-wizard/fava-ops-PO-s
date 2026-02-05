# Script PowerShell para generar el .exe
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build de mo_and_recipes.exe" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si PyInstaller está instalado
try {
    python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller no encontrado"
    }
} catch {
    Write-Host "PyInstaller no está instalado. Instalando..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error al instalar PyInstaller" -ForegroundColor Red
        Read-Host "Presiona Enter para salir"
        exit 1
    }
}

Write-Host ""
Write-Host "Limpiando builds anteriores..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }

Write-Host ""
Write-Host "Construyendo ejecutable..." -ForegroundColor Green
pyinstaller mo_and_recipes.spec --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Error al construir el ejecutable" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Build completado exitosamente!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "El ejecutable se encuentra en: dist\mo_and_recipes.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANTE: Para usar el .exe en otra PC, necesitas:" -ForegroundColor Yellow
Write-Host "1. Copiar el archivo dist\mo_and_recipes.exe"
Write-Host "2. Copiar la carpeta dist\mo_and_recipes (si existe) con todos sus archivos"
Write-Host "3. Asegurarte de que la PC destino tenga las credenciales necesarias"
Write-Host "   (archivo .streamlit/secrets.toml o configurar las variables de entorno)"
Write-Host ""
Read-Host "Presiona Enter para salir"
