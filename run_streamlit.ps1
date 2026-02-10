# Script para ejecutar Streamlit evitando problemas de política de ejecución
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Cambiando al directorio: $scriptPath" -ForegroundColor Green
Write-Host ""

# Obtener IP local
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IMPORTANTE: Para acceder desde otras PCs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
if ($localIP) {
    Write-Host "El servidor estará disponible en:" -ForegroundColor Green
    Write-Host "  - Local: http://localhost:8502/" -ForegroundColor Yellow
    Write-Host "  - Red:   http://$localIP:8502/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Solo se muestra MO and Recipes - sin menú de navegación." -ForegroundColor Green
} else {
    Write-Host "No se pudo obtener la IP local automáticamente." -ForegroundColor Red
    Write-Host "Ejecuta 'ipconfig' para ver tu IP y usa: http://TU_IP:8502/" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si existe el venv
if (Test-Path "venv\Scripts\python.exe") {
    Write-Host "Ejecutando Streamlit desde el entorno virtual..." -ForegroundColor Green
    & "venv\Scripts\python.exe" -m streamlit run mo_only.py --server.address=0.0.0.0 --server.port=8502
} else {
    Write-Host "ERROR: No se encontró el entorno virtual (venv)" -ForegroundColor Red
    Write-Host "Por favor, crea un entorno virtual primero:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    pause
}
