# 아키텍처

## 디렉토리 구조

```
h2fills-node-editor/
│
├── h2sim_main.py          ← 진입점 (GUI + headless CLI)
├── __init__.py            ← 버전 (2.0.0)
├── requirements.txt       ← 의존성
├── setup.py               ← 패키지 설정
│
├── app/
│   ├── domain/            ← 물리 시뮬레이션 모델 (순수 Python, DPG 없음)
│   │   ├── sim_node_abc.py   ABC: SimNode
│   │   ├── supply.py
│   │   ├── precooler.py
│   │   ├── valve.py
│   │   ├── tank.py
│   │   ├── mux_node.py
│   │   └── scope_node.py
│   │
│   ├── engine/            ← 실행 엔진
│   │   ├── graph_engine.py   DAG 실행기 (위상 정렬 + dirty 전파)
│   │   ├── orchestrator.py   세션 제어 (start/pause/reset)
│   │   ├── time_controller.py 시뮬레이션 시계
│   │   ├── node_context.py   틱마다 노드에 전달되는 컨텍스트
│   │   └── event_bus.py      이벤트·트렌드 로거
│   │
│   ├── nodes/             ← DPG 노드 위젯 래퍼
│   │   └── h2_nodes.py       H2DpgNode 기반 클래스 + 6개 구현
│   │
│   ├── ui/                ← 사용자 인터페이스
│   │   ├── h2_node_editor.py  메인 에디터 윈도우
│   │   ├── command_history.py Undo/Redo (Command Pattern)
│   │   ├── jump_lines.py      직선+교차 점프선 오버레이
│   │   ├── link_styler.py     포트 타입별 링크 색상
│   │   ├── scope_view.py      스코프 뷰 창
│   │   ├── font_manager.py    한국어 폰트 등록
│   │   └── icon_loader.py     SVG 아이콘 로더
│   │
│   └── infra/             ← 인프라
│       └── save_manager.py   JSON 저장/불러오기 + 백업 + 마이그레이션
│
├── scenarios/             ← 예제 그래프 JSON
├── res/
│   ├── fonts/             ← NanumGothicCoding
│   └── icons/             ← SVG 아이콘 (supply, valve, ...)
├── tests/                 ← 단위 테스트
│   ├── test_engine.py
│   └── test_precooler.py
└── scripts/               ← 실행 스크립트 (.bat / .ps1)
```

---

## 레이어 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                  h2sim_main.py                      │  ← 진입점
├─────────────────────────────────────────────────────┤
│             app/ui/h2_node_editor.py                │  ← UI 조율
│  (메뉴·툴바·팔레트·캔버스·저장·Undo/Redo·검증)        │
├───────────────────────┬─────────────────────────────┤
│   app/nodes/h2_nodes  │   app/ui/ 나머지              │
│   (DPG 위젯 래퍼)      │   (jump_lines, link_styler)  │
├───────────────────────┴─────────────────────────────┤
│             app/engine/ (실행 엔진)                   │
│   Orchestrator → GraphEngine → TimeController       │
├─────────────────────────────────────────────────────┤
│             app/domain/ (물리 모델)                   │
│   SimNode ABC → Supply, PreCooler, Valve, Tank...   │
└─────────────────────────────────────────────────────┘
```

---

## 데이터 흐름 (1 시뮬레이션 틱)

```
1. editor.tick()
   └─ _SimRunner 백그라운드 스레드:
      └─ orc.run_one_tick()
         ├─ NodeContext(t, dt, logger) 생성
         ├─ GraphEngine.tick(ctx)
         │   ├─ 위상 정렬으로 실행 순서 결정
         │   ├─ Supply.evaluate(ctx, inputs) → outputs
         │   ├─ PreCooler.evaluate(ctx, inputs) → outputs
         │   ├─ Valve.evaluate(ctx, inputs) → outputs
         │   └─ Tank.evaluate(ctx, inputs) → outputs
         └─ TimeController.step() → still_running: bool

2. 메인 스레드 (매 렌더 프레임):
   ├─ _apply_feedback()   # 탱크 압력 → 공급원 배압 역전파
   ├─ _update_nodes_display()  # DPG 위젯 값 갱신
   └─ _update_status_bar()     # t, 진행률 갱신
```

---

## 주요 인터페이스

### SimNode (app/domain/sim_node_abc.py)
```python
class SimNode(ABC):
    @abstractmethod
    def evaluate(self, ctx: NodeContext,
                 inputs: dict[str, Any]) -> dict[str, Any]: ...
    def reset(self) -> None: ...
```

### H2DpgNode (app/nodes/h2_nodes.py)
```python
class H2DpgNode(ABC):
    NODE_TYPE: str
    COLOR: tuple[int, int, int, int]
    INPUTS: list[PortMeta]
    OUTPUTS: list[PortMeta]

    def build(self, editor_tag: str, pos: tuple) -> None: ...
    def to_json(self) -> dict: ...
    def from_json(self, data: dict) -> None: ...
    def get_domain_node(self) -> SimNode: ...
    def close(self) -> None: ...
```
