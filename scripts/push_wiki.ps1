# push_wiki.ps1 — 위키 파일을 GitHub Wiki 레포에 푸시
#
# 사전 준비 (최초 1회만):
#   1. https://github.com/swordsq3/h2fills-node-editor/wiki 방문
#   2. "Create the first page" 클릭 → 제목 "Home", 내용 아무거나 입력 후 저장
#   3. 이 스크립트 실행: scripts\push_wiki.ps1
#
# 이후 wiki/ 폴더 파일을 수정하면 다시 이 스크립트를 실행해 업데이트

$ErrorActionPreference = "Stop"

$proj      = Split-Path $PSScriptRoot -Parent
$wikiDir   = Join-Path $proj "wiki"
$tmpDir    = Join-Path $env:TEMP "h2wiki_push"
$wikiRepo  = "https://github.com/swordsq3/h2fills-node-editor.wiki.git"
$py        = "C:\Users\user\anaconda\envs\h2sim\python.exe"

Write-Host "=== H2FillS Wiki 푸시 스크립트 ===" -ForegroundColor Cyan

# Python으로 git 자격증명 가져오기
$cred = & $py -c @"
import subprocess
result = subprocess.run(
    ['git', 'credential', 'fill'],
    input='protocol=https\nhost=github.com\n',
    capture_output=True, text=True
)
lines = dict(line.split('=',1) for line in result.stdout.strip().splitlines() if '=' in line)
print(lines.get('password',''))
"@
$cred = $cred.Trim()

if (-not $cred) {
    Write-Host "[오류] GitHub 자격증명을 가져올 수 없습니다." -ForegroundColor Red
    Write-Host "git credential manager에 GitHub 계정이 등록되어 있는지 확인하세요."
    Read-Host; exit 1
}

$wikiRepoAuth = "https://swordsq3:$cred@github.com/swordsq3/h2fills-node-editor.wiki.git"

# 임시 디렉토리 정리 후 클론
if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }

Write-Host "위키 레포 클론 중..." -ForegroundColor Yellow
try {
    git clone $wikiRepoAuth $tmpDir 2>&1 | Out-Null
} catch {
    Write-Host "[오류] 위키 레포 클론 실패." -ForegroundColor Red
    Write-Host "아직 위키를 초기화하지 않았다면:"
    Write-Host "  1. https://github.com/swordsq3/h2fills-node-editor/wiki 방문"
    Write-Host "  2. 'Create the first page' 클릭 후 저장"
    Write-Host "  3. 이 스크립트 재실행"
    Read-Host; exit 1
}

# wiki/ 폴더 내용 복사
Write-Host "위키 파일 복사 중..." -ForegroundColor Yellow
Get-ChildItem $wikiDir -Filter "*.md" | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $tmpDir $_.Name) -Force
    Write-Host "  + $($_.Name)"
}

# 커밋 & 푸시
Push-Location $tmpDir
git config user.name  "swordsq3"
git config user.email "fjurt77uy@gmail.com"
git add -A

$status = git status --porcelain
if (-not $status) {
    Write-Host "변경 사항 없음 — 최신 상태입니다." -ForegroundColor Green
    Pop-Location; exit 0
}

$date = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "docs: 위키 업데이트 ($date)"
git push origin master 2>&1
Pop-Location

Write-Host ""
Write-Host "완료! 위키 확인:" -ForegroundColor Green
Write-Host "  https://github.com/swordsq3/h2fills-node-editor/wiki" -ForegroundColor Cyan
Read-Host "Press Enter to close"
