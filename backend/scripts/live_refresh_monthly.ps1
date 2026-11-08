# Monthly E168 live refresh on this computer (10th of each month): newest public government figures and news up to the
# last complete month, frozen E168 model, owner gate, served automatically. The XLM-R news scorer runs in the OpenVINO python.
# Register it once (owner decision) with:
#   schtasks /Create /TN "aiPHeed monthly refresh" /SC MONTHLY /D 10 /ST 06:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\admin\aipheed_e145\backend\scripts\live_refresh_monthly.ps1"
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$py = if ($env:AIPHEED_PYTHON) { $env:AIPHEED_PYTHON } else { "C:\Users\admin\aipheed\backend\venv\Scripts\python.exe" }
$env:PYTHONPATH = $backend
$env:PYTHONIOENCODING = "utf-8"
Set-Location $backend
$log = Join-Path $backend "data\e168\live_raw\monthly_task.log"
& $py -m app.e168.live_refresh run *>> $log
