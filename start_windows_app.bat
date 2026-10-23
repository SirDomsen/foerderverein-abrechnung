@echo off
title Foerderverein Grundschule - Windows Abrechnungs-Manager
cls

echo ======================================================================
echo   Foerderverein Grundschule - Abrechnungs-Manager (Windows)
echo ======================================================================
echo.
echo   [+] Starte Windows Desktop-App...
echo.

python app_windows.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Es gab einen Fehler beim Starten der Desktop-App.
    pause
)
