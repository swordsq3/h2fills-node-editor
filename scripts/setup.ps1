$proj = Split-Path $PSScriptRoot -Parent
$envYml = "$proj\environment.yml"
if ((conda env list) -match 'h2sim') {
    Write-Host '[INFO] Updating h2sim env...' -ForegroundColor Yellow
    conda env update -n h2sim -f $envYml --prune
} else {
    Write-Host '[INFO] Creating h2sim env...' -ForegroundColor Yellow
    conda env create -f $envYml
}
if ($LASTEXITCODE -eq 0) { Write-Host '[OK] Done!' -ForegroundColor Green } else { Write-Host '[ERROR] Failed.' -ForegroundColor Red }
Read-Host 'Press Enter'
