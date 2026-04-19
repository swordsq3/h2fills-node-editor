# 시뮬레이션 엔진

## 전체 구조

```
Orchestrator
├── TimeController    시뮬레이션 시계 (dt, t_end, state)
├── GraphEngine       노드 DAG 실행기
│   ├── register_node(nid, sim_node)
│   ├── connect(sn, sp, dn, dp)
│   └── tick(ctx) → 위상 정렬 후 각 노드 evaluate()
└── EventBus          이벤트·트렌드 로거
```

---

## GraphEngine (app/engine/graph_engine.py)

### 핵심 동작

1. **위상 정렬 (Kahn's algorithm)**: 노드 간 의존성을 분석해 실행 순서 결정
2. **Dirty 전파**: 연결된 출력 변경 시 하위 노드를 `dirty` 세트에 추가
3. **포트-레벨 라우팅**: 각 노드의 `evaluate()` 호출 시 입력 딕셔너리를 연결 정보로 구성

```python
# 내부 데이터 구조
self._nodes:   dict[nid, SimNode]
self._edges:   list[(src_nid, src_port, dst_nid, dst_port)]
self._outputs: dict[nid, dict[port, value]]   # 마지막 출력 캐시
self._dirty:   set[nid]                        # 재계산 필요 노드
```

### tick() 흐름

```python
def tick(self, ctx: NodeContext) -> None:
    order = self._topo_sort()          # 의존성 순서
    for nid in order:
        if nid not in self._dirty:
            continue
        inputs = self._gather_inputs(nid)   # 연결된 출력값 수집
        outputs = self._nodes[nid].evaluate(ctx, inputs)
        self._outputs[nid] = outputs
        self._propagate_dirty(nid)     # 하위 노드 dirty 마킹
```

### 연결 / 해제

```python
graph.connect("supply_0", "P_MPa", "precooler_0", "P_in_MPa")
graph.disconnect("supply_0", "P_MPa", "precooler_0", "P_in_MPa")
graph.disconnect_node("tank_0")   # 해당 노드의 모든 연결 제거
```

---

## TimeController (app/engine/time_controller.py)

```python
class SimState(Enum):
    IDLE     = "idle"
    RUNNING  = "running"
    PAUSED   = "paused"
    FINISHED = "finished"

class TimeController:
    dt:    float    # 타임스텝 [s]
    t_end: float    # 종료 시각 [s]
    t:     float    # 현재 시각 [s] (read-only 권장)

    def start(self) -> None           # IDLE/PAUSED → RUNNING
    def pause(self) -> None           # RUNNING → PAUSED
    def reset(self) -> None           # → IDLE, t = 0
    def step(self) -> bool            # t += dt; True = 계속, False = 완료
    @property
    def is_running(self) -> bool
    @property
    def progress(self) -> float       # 0.0 ~ 1.0
```

---

## NodeContext (app/engine/node_context.py)

`evaluate()` 호출 시 모든 노드에 전달되는 읽기 전용 객체:

```python
@dataclass
class NodeContext:
    t:        float       # 현재 시각 [s]
    dt:       float       # 타임스텝 [s]
    logger:   EventBus    # 이벤트·트렌드 로거
    scenario: dict = {}   # 추가 파라미터 (향후 확장용)
```

---

## EventBus (app/engine/event_bus.py)

시뮬레이션 중 이벤트 발행 및 트렌드(시계열) 기록:

```python
bus.emit(t, EventLevel.INFO, "Supply", "충전 시작")
bus.trend(t, "tank/P_MPa", 35.0)   # 시계열 기록

# 구독
bus.subscribe(EventLevel.WARNING, callback_fn)

# 트렌드 읽기 (그래프 플롯용)
times, values = bus.get_trend("tank/P_MPa")
```

`EventLevel`: `DEBUG < INFO < WARNING < ERROR`

---

## 백그라운드 스레드 (_SimRunner)

`h2_node_editor.py` 내장 클래스. `threading.RLock` 으로 그래프 상태를 보호합니다:

```
백그라운드 스레드:
  while not stop:
      with lock:
          still = orc.run_one_tick()
      if not still: break
      time.sleep(0.001)   # GIL 양보

메인 스레드 (매 렌더 프레임):
  if lock.acquire(blocking=False):
      apply_feedback()          # 역전파
      update_nodes_display()    # DPG 위젯 갱신
      lock.release()
```

> **주의**: DPG API 호출은 **반드시 메인 스레드**에서만 해야 합니다.
> 도메인 노드의 `evaluate()` 는 DPG를 호출하지 않으므로 백그라운드 실행 안전.

---

## 물리 모델 (app/domain/)

| 파일 | 모델 | 주요 입력 | 주요 출력 |
|------|------|-----------|-----------|
| `supply.py` | 고정 공급원 | — | P_MPa, T_K |
| `precooler.py` | NTU 열교환기 | P_in, T_in, mdot | P_out, T_out, Q_removed |
| `valve.py` | 오리피스 유량 | P_up, T_up, P_down, Cv | mass_flow_kg_s |
| `tank.py` | 집중 파라미터 | mass_flow_in, T_in | P_MPa, T_K, m_kg, SOC |
| `mux_node.py` | 패스스루 | in0~in3 | ch0~ch3 |
| `scope_node.py` | 로거 | ch0~ch3 | (없음; 내부 기록) |
