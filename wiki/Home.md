# H2FillS Node Editor — 위키 홈

**H2FillS**는 수소 충전 프로세스를 Simulink 스타일의 노드 에디터로 시각화·시뮬레이션하는 Python 데스크톱 앱입니다.

---

## 빠른 시작

```bash
# 1. 환경 생성 (최초 1회)
scripts\setup.bat          # Windows CMD
# 또는
scripts\setup.ps1          # PowerShell

# 2. 실행
scripts\run.bat
# 또는
scripts\run.ps1

# 3. Headless CLI 실행
conda activate h2sim
python h2sim_main.py --headless --model scenarios/default_700bar.json --out out.csv
```

---

## 위키 목차

| 페이지 | 설명 |
|--------|------|
| [아키텍처](Architecture) | 전체 코드 구조, 모듈 역할, 데이터 흐름 |
| [새 물리 모델 추가](Creating-a-Physics-Model) | 도메인 시뮬레이션 노드 만들기 (Step-by-step) |
| [새 UI 노드 추가](Creating-a-UI-Node) | DearPyGui 노드 위젯 만들기 (Step-by-step) |
| [시뮬레이션 엔진](Simulation-Engine) | DAG 실행기, TimeController, EventBus |
| [저장·불러오기 형식](Save-Load-Format) | JSON 스키마, 버전 마이그레이션, 자동 저장 |
| [키보드 단축키](Keyboard-Shortcuts) | 모든 단축키·마우스 조작 |
| [Headless CLI](Headless-CLI) | GUI 없이 시뮬레이션 실행 |
| [Undo/Redo 시스템](Undo-Redo-System) | Command Pattern 구현 상세 |
| [기여 가이드](Contributing) | 코드 컨벤션, 테스트 실행 |

---

## 기술 스택

| 항목 | 버전 |
|------|------|
| Python | 3.11 |
| DearPyGui | 1.11.1 |
| NumPy | ≥ 1.24 |
| fpdf2 | ≥ 2.7 (보고서 생성) |
| Conda env | `h2sim` |

---

## 지원 노드 (기본 제공)

| 노드 | 역할 |
|------|------|
| **Supply** | 수소 공급원 — 고정 압력·온도 출력 |
| **PreCooler** | 예냉기 — NTU 열교환기 모델 |
| **Valve** | 밸브 — 교착류/아음속 오리피스 유량 계산 |
| **Tank** | 탱크 — 집중 파라미터 모델 (P, T, m, SOC) |
| **MUX** | 신호 멀티플렉서 — 4채널 벡터 버스 |
| **Scope** | 스코프 — 시계열 데이터 시각화 |
