@echo off
title AlamatPintar Setup
echo =============================================
echo  AlamatPintar — One-Click Setup
echo =============================================
echo.
echo This will:
echo  1. Open Windows Firewall for port 8000
echo  2. Start your address parser API
echo  3. Create a public tunnel URL for your brother
echo.
echo Make sure you RUN THIS AS ADMINISTRATOR.
echo.
pause

echo.
echo [1/3] Opening firewall for port 8000...
netsh advfirewall firewall add rule name="AlamatPintar" dir=in action=allow protocol=TCP localport=8000
echo Done!

echo.
echo [2/3] Starting the API server...
start "AlamatPintar API" cmd /c "python -m uvicorn api:app --host 0.0.0.0 --port 8000 --app-dir C:\Users\amarasraf\address-parser"
timeout /t 3 /nobreak >nul

echo [3/3] Creating public tunnel...
start "AlamatPintar Tunnel" cmd /c "C:\Users\amarasraf\address-parser\cloudflared.exe tunnel --url http://localhost:8000 --protocol http2"

echo.
echo =============================================
echo  Your brother can now access at the URL
echo  shown in the Tunnel window.
echo.
echo  (It takes ~10 seconds to connect)
echo =============================================
echo.
pause
