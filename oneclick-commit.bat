@echo off
setlocal ENABLEDELAYEDEXPANSION
set "REPO=d:\ahmed2025"
set "MSG=feat(licensing): add desktop licensing and root-domain API integration"

echo Staging changes...
git -C "%REPO%" add -A

echo Committing...
git -C "%REPO%" commit -m "%MSG%"

echo Determining current branch...
for /f "delims=" %%b in ('git -C "%REPO%" rev-parse --abbrev-ref HEAD') do set BRANCH=%%b

echo Pushing to origin/!BRANCH! (fast mode) ...
git -C "%REPO%" -c http.version=HTTP/2 -c protocol.version=2 -c pack.threads=0 -c pack.compression=1 push origin !BRANCH!

echo Done.
pause