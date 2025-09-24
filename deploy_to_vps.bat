@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Wrapper to run the PowerShell deploy script and keep window open, capturing output
set LOGFILE=d:\ahmed2025\deploy_to_vps_bat.log

echo ==== %DATE% %TIME% | Start BAT ==== >> "%LOGFILE%"
powershell -NoProfile -ExecutionPolicy Bypass -File "d:\ahmed2025\deploy_to_vps.ps1" >> "%LOGFILE%" 2>&1
set EXITCODE=%ERRORLEVEL%

echo. >> "%LOGFILE%"
if %EXITCODE% NEQ 0 (
  echo Deploy script failed with exit code %EXITCODE%. >> "%LOGFILE%"
  echo Deploy script failed with exit code %EXITCODE%.
) else (
  echo Deploy completed successfully. >> "%LOGFILE%"
  echo Deploy completed successfully.
)

echo.
echo Log files:

echo   - PowerShell: d:\ahmed2025\deploy_to_vps.log

echo   - Batch:      d:\ahmed2025\deploy_to_vps_bat.log

echo.
echo Press any key to close this window...
pause >nul
endlocal