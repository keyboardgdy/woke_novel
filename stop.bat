@echo off
chcp 65001 > nul
setlocal

set "WOKE_ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'SilentlyContinue';" ^
  "$root = [System.IO.Path]::GetFullPath($env:WOKE_ROOT).TrimEnd('\');" ^
  "$targets = @();" ^
  "$processes = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and (($_.CommandLine -match 'woke_launcher\.py') -or ($_.CommandLine -match 'app_server\.main')) -and ($_.CommandLine.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0) };" ^
  "$targets += $processes | ForEach-Object { [int]$_.ProcessId };" ^
  "$targets += Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8787 -State Listen | Select-Object -ExpandProperty OwningProcess;" ^
  "$targets = $targets | Where-Object { $_ -and $_ -ne $PID } | Sort-Object -Unique;" ^
  "if (-not $targets) { Write-Host 'No woke service process found.'; exit 0 }" ^
  "foreach ($pidToStop in $targets) { Write-Host ('Stopping PID ' + $pidToStop + '...'); & taskkill /PID $pidToStop /T /F | Out-Host }"

endlocal
