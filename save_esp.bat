@echo off
cd /d "C:\Users\Clemens Li\git\ESP32"

echo Sende Interrupt an ESP32...
mpremote connect COM4 exec "raise KeyboardInterrupt" 2>nul

echo Starte Sicherung ESP32 -> lokal...
rshell -p COM4 rsync /pyboard .

echo Fertig.
pause