$py   = 'C:\Users\user\anaconda\envs\h2sim\python.exe'
$proj = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path $py)) { Write-Host '[ERROR] Run setup.ps1 first.' -ForegroundColor Red; Read-Host; exit 1 }
& $py -m pytest "$proj\tests\test_precooler.py::test_print_comparison_table" -v -s --rootdir="$proj"
Read-Host 'Press Enter'
