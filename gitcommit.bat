:: Batch script to commit and push to GitHub
cd /d "C:\Users\Clemens Li\git\ESP32"

:: Display status before adding files
git status

git add .

:: Prompt for commit message
set /p msg="Enter commit message: "

git commit -m "%msg%"

git push origin main

echo.
echo Process complete. Press any key to close.
pause