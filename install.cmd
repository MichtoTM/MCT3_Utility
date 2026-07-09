@echo off
cd /d "%~dp0"
pip install -r requirements.txt
pip install -e .

@echo on
echo Installation effectuée avec succès.
pause