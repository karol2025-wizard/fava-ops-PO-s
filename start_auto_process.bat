@echo off
REM Auto-Process Production Service
REM This batch file starts the automatic production processing service

cd /d "%~dp0"

echo ========================================
echo Auto-Process Production Service
echo ========================================
echo.
echo Starting automatic production processing...
echo This will monitor the database and update MRPeasy automatically.
echo Press Ctrl+C to stop.
echo.

python auto_process_production.py --mode continuous --interval 30

pause

