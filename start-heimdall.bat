@echo off
title Heimdall Setup
echo =============================================
echo  Heimdall — One-Click Setup
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
netsh advfirewall firewall add rule name="Heimdall" dir=in action=allow protocol=TCP localport=8000
echo Done!

echo.
echo [2/3] Starting the API server...
start "Heimdall API" cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir C:\Users\amarasraf\Documents\Pearl_Abyss_Studio\Projects\Heimdall"
timeout /t 3 /nobreak >nul

echo [3/3] Creating public tunnel...
start "Heimdall Tunnel" cmd /k "ssh -o StrictHostKeyChecking=accept-new -R 80:127.0.0.1:8000 nokey@localhost.run"

echo.
echo =============================================
echo  Your brother can now access at the URL
echo  shown in the Tunnel window.
echo.
echo  (It takes ~10 seconds to connect)
echo =============================================
echo.
pause
