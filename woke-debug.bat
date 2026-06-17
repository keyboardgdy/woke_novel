@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Preparing frontend: cd frontend ^&^& npm install ^&^& npm run build
pushd "%~dp0frontend"
echo Installing frontend dependencies: npm install
call npm install
if errorlevel 1 (
  echo.
  echo Frontend dependency install failed. Check the errors above.
  popd
  pause
  exit /b 1
)
echo Building frontend: npm run build
call npm run build
if errorlevel 1 (
  echo.
  echo Frontend build failed. Check the errors above.
  popd
  pause
  exit /b 1
)
popd
python "%~dp0woke_launcher.py" %*
echo.
echo Launcher log: "%~dp0logs\woke_launcher.log"
echo Backend log: "%~dp0logs\woke_server.log"
pause
