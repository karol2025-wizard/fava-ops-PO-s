# Script para ejecutar Streamlit evitando problemas de política de ejecución
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Cambiando al directorio: $scriptPath" -ForegroundColor Green
Write-Host ""

# Verificar si existe el venv
if (Test-Path "venv\Scripts\python.exe") {
    Write-Host "Ejecutando Streamlit desde el entorno virtual..." -ForegroundColor Green
    & "venv\Scripts\python.exe" -m streamlit run home.py
} else {
    Write-Host "ERROR: No se encontró el entorno virtual (venv)" -ForegroundColor Red
    Write-Host "Por favor, crea un entorno virtual primero:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    pause
}
