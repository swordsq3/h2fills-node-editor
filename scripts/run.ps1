$py   = 'C:\Users\user\anaconda\envs\h2sim\python.exe'
$proj = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path $py)) { Write-Host '[ERROR] Run setup.ps1 first.' -ForegroundColor Red; Read-Host; exit 1 }
& $py "$proj\h2sim_main.py"
if ($LASTEXITCODE -ne 0) { Read-Host 'Press Enter' }
