$py   = 'C:\Users\user\anaconda\envs\h2sim\python.exe'
$proj = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path $py)) { Write-Host '[ERROR] Run setup.ps1 first.' -ForegroundColor Red; Read-Host; exit 1 }
& $py -m pytest "$proj\tests" -v --tb=short --rootdir="$proj"
if ($LASTEXITCODE -eq 0) { Write-Host '[PASS] All tests passed!' -ForegroundColor Green } else { Write-Host '[FAIL] Some tests failed.' -ForegroundColor Red }
Read-Host 'Press Enter'
