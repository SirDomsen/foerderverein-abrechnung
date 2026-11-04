@echo off
title Förderverein Abrechnung - Universelle Offline PWA starten
cd /d "%~dp0"
cls

echo ======================================================================
echo   Förderverein Grundschule – Universelle Offline-App (PWA)
echo ======================================================================
echo.
echo   [+] Öffne lokale Web-App im Standard-Browser...
echo.

start "" "apps\pwa\index.html"

exit
