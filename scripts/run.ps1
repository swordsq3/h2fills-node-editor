$py   = 'C:\Users\user\anaconda\envs\h2sim\python.exe'
$proj = Split-Path $PSScriptRoot -Parent
$tmp  = "$env:LOCALAPPDATA\h2sim\launcher.py"

if (-not (Test-Path $py)) {
    Write-Host '[ERROR] h2sim 환경 없음. setup.ps1 먼저 실행하세요.' -ForegroundColor Red
    Read-Host; exit 1
}

# 한글 경로를 Python 인자로 직접 전달하면 실패하므로 임시 런처를 이용
New-Item -ItemType Directory -Force -Path (Split-Path $tmp) | Out-Null
@"
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
proj = r'$proj'
sys.path.insert(0, proj)
os.chdir(proj)
from h2sim_main import main
main()
"@ | Out-File -FilePath $tmp -Encoding utf8

& $py $tmp
if ($LASTEXITCODE -ne 0) { Read-Host 'Press Enter to close' }
