@echo off
REM Build INTAI.exe

pyinstaller --noconfirm --uac-admin --icon=assets/app_icon.ico --name INTAI main.py ^
  --add-data "config/config.json;config" ^
  --hidden-import=core.run_arena ^
  --hidden-import=core.run_aram ^
  --hidden-import=core.run_test ^
  --hidden-import=core.run_yuumi_sr

REM Wait for files to be released
timeout /t 2

REM Create a ZIP archive of the dist folder (place ZIP inside dist)
powershell -NoProfile -Command "if (Test-Path 'dist') { Remove-Item -Force -ErrorAction SilentlyContinue 'dist\\INTAI.zip'; Compress-Archive -Path 'dist\\*' -DestinationPath 'dist\\INTAI.zip' -Force }"

echo Build complete. Check the dist folder for INTAI.exe.
pause