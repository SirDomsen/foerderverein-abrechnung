@echo off
title Foerderverein Grundschule - Web und Smartphone Server
cls

echo ======================================================================
echo   Foerderverein Grundschule - Abrechnungs-Manager (Web und Smartphone)
echo ======================================================================
echo.

:: Lokale IP-Adresse ermitteln
for /f "tokens=*" %%i in ('python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2^>nul') do set LOCAL_IP=%%i

if "%LOCAL_IP%"=="" (
    set LOCAL_IP=127.0.0.1
)

:: Pruefen, ob Port 8080 noch blockiert ist und alte Instanz beenden
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr /I "ABH LISTENING" 2^>nul') do taskkill /F /PID %%a >nul 2>&1

echo   [+] Server wird gestartet...
echo.
echo   * Am Computer im Browser:
echo       http://localhost:8080
echo.
echo   * Auf dem SMARTPHONE im selben WLAN:
echo       http://%LOCAL_IP%:8080
echo.
echo ======================================================================
echo   Tipp: Im Browser auf Handy-Link klicken fuer den QR-Code!
echo ======================================================================
echo.

python app_web.py

pause
