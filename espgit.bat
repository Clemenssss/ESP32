@echo off
setlocal
cd /d "C:\Users\Clemens Li\git\ESP32"

set PORT=COM4

echo === 1) Backup vom ESP32 ===
mpremote connect %PORT% fs cp -r :. .
if errorlevel 1 (
    echo Backup fehlgeschlagen - Abbruch.
    pause
    exit /b 1
)

echo.
echo === 2) Git Status ===
git status

echo.
git add .
set /p msg="Enter commit message: "
if "%msg%"=="" (
    echo Kein Kommentar eingegeben - Commit abgebrochen.
    pause
    exit /b 1
)

git commit -m "%msg%"
git push origin main

echo.
echo Fertig.
pause