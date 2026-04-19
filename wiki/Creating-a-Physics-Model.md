# 새 물리 모델 추가하기

이 가이드는 새로운 물리 시뮬레이션 노드(도메인 모델)를 처음부터 추가하는 방법을 설명합니다.
예시로 **열 저장 탱크(HeatBuffer)** 노드를 구현합니다.

---

## Step 1 — 도메인 모델 작성 (`app/domain/`)

```python
# app/domain/heat_buffer.py
from __future__ import annotations
from app.domain.sim_node_abc import SimNode
from app.engine.node_context import NodeContext
from typing import Any


class HeatBufferNode(SimNode):
    """
    단순 열 버퍼: Q_in [kW] 을 받아 온도를 적분.
    T(t+dt) = T(t) + (Q_in / (m_kg * cp)) * dt
    """

    def __init__(self, m_kg: float = 10.0, cp: float = 4186.0,
                 T0_K: float = 293.15) -> None:
        self.m_kg  = m_kg    # 물질 질량 [kg]
        self.cp    = cp      # 비열 [J/kg·K]
        self._T    = T0_K    # 현재 온도 [K]

    # ── 필수 구현 ─────────────────────────────────────────────

    def evaluate(self, ctx: NodeContext,
                 inputs: dict[str, Any]) -> dict[str, Any]:
        Q_in = inputs.get("Q_in_kW", 0.0) * 1000.0  # kW → W
        dT   = (Q_in / (self.m_kg * self.cp)) * ctx.dt
        self._T = max(200.0, self._T + dT)           # 하한 클램프
        ctx.logger.trend(ctx.t, "HeatBuffer/T_K", self._T)
        return {
            "T_out_K": self._T,
        }

    def reset(self) -> None:
        self._T = 293.15
```

**규칙:**
- `evaluate(ctx, inputs)` → `dict` 반환 (출력 포트 이름 : 값)
- `inputs` 키는 나중에 연결선으로 연결될 입력 포트 이름과 일치해야 합니다
- `ctx.dt` (초)를 이용해 시간 적분
- `ctx.logger.trend(t, name, value)` 로 시계열 기록 (선택)
- 물리 상수 검증은 `__init__`에서 처리

---

## Step 2 — UI 노드 래퍼 등록 (`app/nodes/h2_nodes.py`)

파일 하단의 `NODE_CLASSES` 딕셔너리와 `PALETTE` 리스트에 추가합니다.

### 2-1 PortMeta 정의 및 클래스 작성

```python
# app/nodes/h2_nodes.py 에 추가
from app.domain.heat_buffer import HeatBufferNode

class HeatBufferDpgNode(H2DpgNode):
    NODE_TYPE = "heat_buffer"
    COLOR     = (200, 80, 40, 230)   # 주황-빨강 계열

    INPUTS  = [
        PortMeta("Q_in_kW",  "Q_in [kW]", "in"),
    ]
    OUTPUTS = [
        PortMeta("T_out_K",  "T_out [K]", "out"),
    ]

    def __init__(self, node_id: str) -> None:
        super().__init__(node_id)
        self._domain = HeatBufferNode()

    # ── 파라미터 UI (노드 본체에 표시) ─────────────────────
    def _build_params(self) -> None:
        dpg.add_input_float(
            label="m [kg]", tag=f"{self.node_id}_m",
            default_value=10.0, min_value=0.1, max_value=1000.0,
            width=100,
            callback=self._sync_params)
        dpg.add_input_float(
            label="cp [J/kgK]", tag=f"{self.node_id}_cp",
            default_value=4186.0, min_value=100.0, max_value=10000.0,
            width=100,
            callback=self._sync_params)

    def _sync_params(self) -> None:
        self._domain.m_kg = dpg.get_value(f"{self.node_id}_m")
        self._domain.cp   = dpg.get_value(f"{self.node_id}_cp")

    # ── 직렬화 ─────────────────────────────────────────────
    def to_json(self) -> dict:
        d = super().to_json()
        d["params"] = {
            "m_kg": self._domain.m_kg,
            "cp":   self._domain.cp,
        }
        return d

    def from_json(self, data: dict) -> None:
        super().from_json(data)
        p = data.get("params", {})
        if "m_kg" in p:
            self._domain.m_kg = p["m_kg"]
            dpg.set_value(f"{self.node_id}_m", p["m_kg"])
        if "cp" in p:
            self._domain.cp = p["cp"]
            dpg.set_value(f"{self.node_id}_cp", p["cp"])

    def get_domain_node(self):
        self._sync_params()
        return self._domain
```

### 2-2 NODE_CLASSES & PALETTE 등록

```python
# app/nodes/h2_nodes.py 하단

NODE_CLASSES: dict[str, type[H2DpgNode]] = {
    "supply":      SupplyDpgNode,
    "precooler":   PreCoolerDpgNode,
    "valve":       ValveDpgNode,
    "tank":        TankDpgNode,
    "mux":         MuxDpgNode,
    "scope":       ScopeDpgNode,
    "heat_buffer": HeatBufferDpgNode,   # ← 추가
}

PALETTE: list[dict] = [
    # ... 기존 항목들 ...
    {"type": "heat_buffer", "label": "열 버퍼",  "icon": "pipe"},  # ← 추가
]
```

---

## Step 3 — 아이콘 추가 (선택)

`app/ui/icon_loader.py` 에서 새 아이콘을 그리거나 `res/icons/` 에 SVG 파일을 추가합니다.

```python
# app/ui/icon_loader.py 내 _MAKERS 딕셔너리에 추가
_MAKERS: dict[str, Callable] = {
    ...
    "heat_buffer": _draw_generic_rect,   # 기존 함수 재사용 가능
}
```

---

## Step 4 — 테스트 작성 (`tests/`)

```python
# tests/test_heat_buffer.py
from app.domain.heat_buffer import HeatBufferNode
from app.engine.node_context import NodeContext
from app.engine.event_bus import EventBus

def test_heat_buffer_heats_up():
    node = HeatBufferNode(m_kg=1.0, cp=1000.0, T0_K=300.0)
    bus  = EventBus()
    ctx  = NodeContext(t=0.0, dt=1.0, logger=bus)

    out = node.evaluate(ctx, {"Q_in_kW": 1.0})  # 1 kW × 1 s = 1 kJ
    # ΔT = 1000 J / (1 kg × 1000 J/kgK) = 1 K
    assert abs(out["T_out_K"] - 301.0) < 0.01

def test_heat_buffer_reset():
    node = HeatBufferNode(T0_K=300.0)
    node._T = 400.0
    node.reset()
    assert node._T == 293.15
```

```bash
conda activate h2sim
pytest tests/test_heat_buffer.py -v
```

---

## 체크리스트

- [ ] `app/domain/heat_buffer.py` — `SimNode.evaluate()` 구현
- [ ] `app/nodes/h2_nodes.py` — `H2DpgNode` 서브클래스 + `NODE_CLASSES` + `PALETTE`
- [ ] `to_json()` / `from_json()` — 파라미터 저장/복원
- [ ] `get_domain_node()` — UI 파라미터 → 도메인 객체 동기화
- [ ] `tests/` — 단위 테스트 (물리 검증)
- [ ] `app/ui/icon_loader.py` — 아이콘 등록 (선택)
