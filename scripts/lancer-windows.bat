@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
    echo Preparation du logiciel : Python 3.12 doit etre installe.
    py -3.12 -m venv .venv
    if errorlevel 1 goto erreur
)
.venv\Scripts\python.exe -c "import PySide6, ortools, reportlab" >nul 2>&1
if errorlevel 1 (
    echo Telechargement initial des bibliotheques. Internet requis une seule fois.
    .venv\Scripts\python.exe -m pip install -e .
    if errorlevel 1 goto erreur
)
.venv\Scripts\python.exe -m gardeplan
if errorlevel 1 goto erreur
exit /b 0
:erreur
echo.
echo Le lancement a echoue. Conservez les donnees et consultez le message ci-dessus.
pause
exit /b 1
