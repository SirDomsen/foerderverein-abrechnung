@echo off
title Förderverein Abrechnungs-Manager - EXE Builder
cd /d "%~dp0\.."
echo ======================================================================
echo   Erstelle eigenstaendige Windows .EXE (PyInstaller)
echo ======================================================================
echo.
pyinstaller --clean build_tools\AbrechnungsManager.spec
echo.
echo Fertig! Die fertige .exe liegt im Ordner dist\
pause
