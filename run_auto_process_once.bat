@echo off
REM Process pending production entries once and exit

cd /d "%~dp0"

echo Processing pending production entries...
python auto_process_production.py --mode once --limit 50

pause

