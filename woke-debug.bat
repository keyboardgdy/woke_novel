@echo off
chcp 65001 > nul
cd /d "%~dp0"
python "%~dp0woke_launcher.py" %*
echo.
echo 启动器日志: "%~dp0logs\woke_launcher.log"
echo 后端日志: "%~dp0logs\woke_server.log"
pause
