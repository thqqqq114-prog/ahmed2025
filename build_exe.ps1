# PowerShell script to build Windows executable using PyInstaller
# Usage: Right-click -> Run with PowerShell, or: powershell -ExecutionPolicy Bypass -File build_exe.ps1

$ErrorActionPreference = "Stop"

# Ensure venv optional
# python -m venv .venv; .\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install pyinstaller -r requirements.txt

# Clean previous dist/build
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }

# Optional: icon path if available
$iconPath = Join-Path "app" "ui" "app.ico"
$iconArg = ""
if (Test-Path $iconPath) { $iconArg = "--icon `"$iconPath`"" }

# Build
pyinstaller --noconsole --name FarmApp `
  --add-data "app\\data\\farm.db;app\\data" `
  --add-data "app\\ui\\style.qss;app\\ui" `
  --add-data "app\\ui\\icons.qss;app\\ui" `
  $iconArg `
  -p app `
  app\\main.py

Write-Host "Build complete. See dist\\FarmApp"