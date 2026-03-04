@echo off
setlocal

if not exist dist mkdir dist

python -m PyInstaller --noconfirm --clean --windowed --onefile --name MDMControlDesktop ui_app.py

if %errorlevel% neq 0 (
  echo Build failed.
  exit /b %errorlevel%
)

echo Build complete. EXE at dist\MDMControlDesktop.exe
