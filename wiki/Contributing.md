# 기여 가이드

## 개발 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/swordsq3/h2fills-node-editor.git
cd h2fills-node-editor

# 2. Conda 환경 생성
conda env create -f environment.yml    # 최초 1회
conda activate h2sim

# 3. 실행 확인
python h2sim_main.py

# 4. 테스트 실행
pytest tests/ -v
```

---

## 브랜치 전략

```
main                   ← 안정 릴리스
feature/precooler-node ← 현재 개발 브랜치
feature/<기능명>        ← 새 기능 브랜치
fix/<버그명>            ← 버그 수정 브랜치
```

---

## 코드 컨벤션

### Python 스타일

- **타입 힌트** 필수: `def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:`
- **독스트링**: 물리 수식·단위 반드시 명시
- **한국어 주석 허용**: 물리 의미 설명은 한국어 OK
- `from __future__ import annotations` 모든 파일 상단에 포함
- 라인 길이: 88자 이하 권장

### 파일 명명

| 종류 | 규칙 | 예시 |
|------|------|------|
| 도메인 모델 | `snake_case.py` | `heat_buffer.py` |
| UI 노드 클래스 | `PascalCaseDpgNode` | `HeatBufferDpgNode` |
| SimNode 클래스 | `PascalCaseNode` | `HeatBufferNode` |
| 포트 이름 | `snake_case` (단위 포함) | `P_MPa`, `T_out_K`, `mass_flow_kg_s` |
| NODE_TYPE | `snake_case` | `"heat_buffer"` |

### 포트 이름 규칙

포트 이름은 `링크 색상 자동 매핑`에 사용됩니다 (`link_styler.py`):

| 키워드 포함 | 색상 |
|------------|------|
| `mass_flow`, `mdot` | 녹색 |
| `P_down` | 연파랑 |
| `P` | 파랑 |
| `T` | 빨강 |
| `Q_removed` | 주황 |
| `SOC`, `m_kg` | 회색 |
| `ch`, `in` (MUX) | 보라 |

---

## 테스트 작성

```python
# tests/test_<모듈명>.py

from app.domain.heat_buffer import HeatBufferNode
from app.engine.node_context import NodeContext
from app.engine.event_bus import EventBus


def make_ctx(t=0.0, dt=1.0):
    return NodeContext(t=t, dt=dt, logger=EventBus())


def test_물리_법칙_이름_명확하게():
    """테스트 이름은 검증하는 물리 현상을 설명."""
    node = HeatBufferNode(m_kg=1.0, cp=1000.0, T0_K=300.0)
    out  = node.evaluate(make_ctx(dt=1.0), {"Q_in_kW": 1.0})
    # ΔT = 1000 J / (1 kg × 1000 J/kgK) = 1 K
    assert abs(out["T_out_K"] - 301.0) < 1e-6
```

**테스트 실행:**
```bash
pytest tests/ -v                         # 전체
pytest tests/test_precooler.py -v -s     # 특정 파일
pytest tests/ -k "test_물리"              # 키워드 필터
scripts\test.bat                         # Windows 배치
scripts\compare.bat                      # 비교 테스트
```

---

## 새 노드 추가 PR 체크리스트

```
[ ] app/domain/<node>.py        — SimNode 구현, 단위 포함 독스트링
[ ] app/nodes/h2_nodes.py       — H2DpgNode 서브클래스
[ ] NODE_CLASSES 등록           — 고유한 NODE_TYPE 문자열
[ ] PALETTE 등록                — 레이블, 아이콘 지정
[ ] to_json() / from_json()     — 파라미터 직렬화 완전성
[ ] get_domain_node()           — UI → 도메인 파라미터 동기화
[ ] app/ui/icon_loader.py       — 아이콘 추가 (선택)
[ ] app/ui/link_styler.py       — 포트 색상 추가 (선택)
[ ] tests/test_<node>.py        — 물리 검증 테스트
[ ] 문서 업데이트                — 이 위키의 아키텍처 표 업데이트
```

---

## 커밋 메시지 형식

```
<type>: <한국어 설명>

<선택: 상세 설명>

Co-Authored-By: <이름> <이메일>
```

type 종류:
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 기능 변경 없는 코드 개선
- `test`: 테스트 추가/수정
- `docs`: 문서
- `chore`: 빌드·설정 변경

예시:
```
feat: HeatBuffer 노드 추가 (열 저장 모델)

- NTU 열교환기 모델 기반 집중 파라미터
- m_kg, cp UI 파라미터 직렬화 지원
- test_heat_buffer.py 단위 테스트 포함
```
