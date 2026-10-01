@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "$con = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if ($con) { $con.OwningProcess | Sort-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"
cd docs
start "GearUp web" python -m http.server 8765
timeout /t 1 >nul
start http://127.0.0.1:8765/index.html
