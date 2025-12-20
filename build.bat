@echo off
REM Build INTAI.exe

pyinstaller --noconfirm --icon=assets/app_icon.ico --name INTAI main.py ^
  --add-data "config/config.json;config" ^
  --add-data "config/config_default.json;config" ^
  --add-data "tesseract/tesseract.exe;tesseract" ^
  --add-data "tesseract/tessdata;tesseract/tessdata" ^
  --hidden-import=core.run_arena ^
  --hidden-import=core.run_aram ^
  --hidden-import=core.run_test

echo Build complete. Check the dist folder for INTAI.exe.
pause