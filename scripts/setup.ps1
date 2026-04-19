$proj = Split-Path $PSScriptRoot -Parent
$envYml = "$proj\environment.yml"
if ((conda env list) -match 'h2sim') {
    Write-Host '[INFO] Updating h2sim env...' -ForegroundColor Yellow
    conda env update -n h2sim -f $envYml --prune
} else {
    Write-Host '[INFO] Creating h2sim env...' -ForegroundColor Yellow
    conda env create -f $envYml
}
if ($LASTEXITCODE -ne 0) { Write-Host '[ERROR] Conda failed.' -ForegroundColor Red; Read-Host; exit 1 }

# 폰트를 ASCII 경로로 복사 (DearPyGui는 한글 경로 폰트 로드 불가)
$fontSrc = "$proj\res\fonts\NanumGothicCoding-Regular.ttf"
$fontDst = "$env:LOCALAPPDATA\h2sim\fonts\NanumGothicCoding-Regular.ttf"
if (Test-Path $fontSrc) {
    New-Item -ItemType Directory -Force -Path (Split-Path $fontDst) | Out-Null
    Copy-Item $fontSrc $fontDst -Force
    Write-Host '[OK] Font copied to ASCII path.' -ForegroundColor Green
}

Write-Host '[OK] Setup complete! Use scripts\run.ps1 to launch.' -ForegroundColor Green
Read-Host 'Press Enter'
