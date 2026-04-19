# Headless CLI 모드

GUI 없이 커맨드라인에서 시뮬레이션을 실행하는 방법입니다.  
배치 처리, CI/CD 파이프라인, 서버 환경에 적합합니다.

---

## 기본 사용법

```bash
conda activate h2sim
python h2sim_main.py --headless --model <모델.json> [옵션]
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--headless` | — | **필수**: GUI 없이 실행 |
| `--model PATH` | — | **필수**: 그래프 JSON 파일 경로 |
| `--out PATH` | (없음) | CSV 결과 출력 경로 |
| `--dt FLOAT` | `1.0` | 시뮬레이션 타임스텝 [s] |
| `--tend FLOAT` | `300.0` | 시뮬레이션 종료 시각 [s] |

---

## 예시

### 기본 실행

```bash
python h2sim_main.py --headless \
    --model scenarios/template_basic_charge.json
```

출력:
```
[Headless] 모델: scenarios/template_basic_charge.json
  t = 50.0 s
  t = 100.0 s
  ...
[Headless] 완료. t = 300.0 s
```

### CSV 결과 저장

```bash
python h2sim_main.py --headless \
    --model scenarios/template_mux_scope.json \
    --out results/charge_result.csv \
    --dt 0.5 \
    --tend 600
```

CSV 형식:
```csv
time,scope_0_ch0,scope_0_ch1,scope_0_ch2,scope_0_ch3
0.0,5.0,293.15,0.0,0.0
0.5,5.12,293.2,0.05,0.001
...
```

### 배치 처리 (PowerShell)

```powershell
$models = Get-ChildItem scenarios/*.json
foreach ($m in $models) {
    $out = "results/$($m.BaseName).csv"
    python h2sim_main.py --headless --model $m --out $out --tend 300
}
```

---

## 제한 사항

- DPG UI 위젯이 생성되지 않으므로 `from_json()` 의 `dpg.set_value()` 호출이 스킵됩니다
- 노드 파라미터는 JSON 의 `params` 필드에서 직접 로드되므로, **저장 파일에 파라미터가 올바르게 직렬화**되어 있어야 합니다
- Scope 노드에 연결된 채널의 데이터만 CSV에 기록됩니다. 다른 출력값(P, T 등)을 기록하려면 Scope 노드를 연결하세요

---

## 스크립트 파일 실행

```bat
REM Windows CMD
scripts\run.bat              ← GUI 실행
```

```powershell
# PowerShell
scripts\run.ps1              # GUI 실행
```

headless 배치용 예시 스크립트 (`scripts/batch_run.ps1`):

```powershell
$py = 'C:\Users\user\anaconda\envs\h2sim\python.exe'
& $py h2sim_main.py --headless --model scenarios/default_700bar.json --out out/result.csv
Write-Host "완료: out/result.csv"
```
