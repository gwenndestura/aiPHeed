# Daily FINAL cycle on this computer (app.final.cycle): checks the official sources that are due, and on a quarter's issue day
# (1 Feb, 1 May, 1 Aug, 1 Nov, Philippine time) collects and scores the news, rebuilds the panels as of the cut-off, issues the
# new forecast with the frozen FINAL model and records it in the forecast history. Running it more often changes nothing.
# This machine has what the data stage needs (the XLM-R news scorer in the OpenVINO python, the source archives).
# Register it once (owner decision) with:
#   schtasks /Create /TN "aiPHeed FINAL daily cycle" /SC DAILY /ST 06:30 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\admin\aipheed_fmc\backend\scripts\final_daily_cycle.ps1"
# After an issue, commit backend/data/final (history, issue folder, run log) so the deployed site serves it.
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$py = if ($env:AIPHEED_PYTHON) { $env:AIPHEED_PYTHON } else { "C:\Users\admin\aipheed\backend\venv\Scripts\python.exe" }
$env:PYTHONPATH = $backend
$env:PYTHONIOENCODING = "utf-8"
Set-Location $backend
$log = Join-Path $backend "data\final\daily_task.log"
& $py -m app.final.cycle run *>> $log
& $py -m app.final.dbsync *>> $log
