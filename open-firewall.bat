@echo off
echo ============================================
echo  Opening firewall for AlamatPintar (port 8000)
echo ============================================
echo.
echo Right-click this file and select "Run as administrator"
echo.
pause

netsh advfirewall firewall add rule name="AlamatPintar" dir=in action=allow protocol=TCP localport=8000

echo.
echo Done! Your brother can now access:
echo   http://26.223.39.149:8000
echo.
pause
