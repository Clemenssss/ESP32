@echo off
cd /d "C:\Users\Clemens Li\git\ESP32"

echo Starte Backup von COM4...

:: Alle .py Dateien vom Board holen
:: Wir iterieren durch die Liste der Dateien und ziehen sie einzeln
for /f "tokens=*" %%f in ('ampy -p COM4 ls') do (
    echo Kopiere %%f ...
    ampy -p COM4 get %%f %%f
)

echo.
echo Sync abgeschlossen.
echo.

:: Git Workflow
git add .
git status
set /p msg="Enter commit message: "
git commit -m "%msg%"
git push origin main

echo.
echo Alles erledigt!
pause