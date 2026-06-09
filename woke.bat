@echo off
chcp 65001 > nul
cd /d "%~dp0"
start "" /b pythonw "%~dp0woke_launcher.py" %*
