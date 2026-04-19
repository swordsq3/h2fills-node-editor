# 새 UI 노드 추가하기

이 가이드는 물리 모델 없이 **UI 전용 노드**(예: 상수 소스, 게인, 수식 블록)를 추가하는 방법을 설명합니다.

> 물리 모델도 같이 추가하려면 [새 물리 모델 추가](Creating-a-Physics-Model) 페이지를 먼저 읽으세요.

---

## H2DpgNode 기본 클래스 이해

```python
# app/nodes/h2_nodes.py
class H2DpgNode(ABC):

    NODE_TYPE: str                    # "my_node" — 고유 문자열 ID
    COLOR: tuple[int,int,int,int]     # 타이틀바 RGBA 색상
    INPUTS:  list[PortMeta]           # 입력 포트 목록
    OUTPUTS: list[PortMeta]           # 출력 포트 목록

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.dpg_tag = f"dpg_node_{node_id}"   # DPG 태그

    # ── 반드시 구현해야 하는 메서드 ─────────────────────────────
    @abstractmethod
    def _build_params(self) -> None:
        """노드 본체에 그릴 파라미터 위젯 (dpg.add_* 호출)."""

    @abstractmethod
    def get_domain_node(self) -> SimNode:
        """엔진에 등록할 SimNode 반환."""

    # ── 선택적 오버라이드 ────────────────────────────────────
    def to_json(self) -> dict:
        """저장 시 직렬화. 부모 호출 후 params 키 추가."""
    def from_json(self, data: dict) -> None:
        """불러오기 시 복원."""
    def update_status(self, *args) -> None:
        """시뮬레이션 중 노드 본체 값 갱신 (TankNode 참고)."""
```

---

## PortMeta 정의

```python
PortMeta(name, label, kind)
# name  : 내부 키 (그래프 연결에 사용)  예: "P_MPa"
# label : UI에 표시되는 텍스트          예: "P [MPa]"
# kind  : "in" 또는 "out"
```

---

## 예시: Gain(증폭) 노드

```python
# app/nodes/h2_nodes.py 에 추가

class GainDpgNode(H2DpgNode):
    """
    단일 실수 신호를 k 배 증폭하는 노드.
    입력: value_in  / 출력: value_out
    """
    NODE_TYPE = "gain"
    COLOR     = (80, 130, 200, 230)   # 파랑 계열

    INPUTS  = [PortMeta("value_in",  "입력",  "in")]
    OUTPUTS = [PortMeta("value_out", "출력",  "out")]

    def __init__(self, node_id: str) -> None:
        super().__init__(node_id)
        self._k = 1.0

    # ── 파라미터 UI ────────────────────────────────────────
    def _build_params(self) -> None:
        dpg.add_input_float(
            label="k (배율)", tag=f"{self.node_id}_k",
            default_value=self._k, width=80,
            callback=lambda: setattr(self, "_k",
                                     dpg.get_value(f"{self.node_id}_k")))

    # ── 도메인 노드 ────────────────────────────────────────
    def get_domain_node(self):
        return _GainSimNode(self._k)

    # ── 직렬화 ─────────────────────────────────────────────
    def to_json(self) -> dict:
        d = super().to_json()
        d["params"] = {"k": self._k}
        return d

    def from_json(self, data: dict) -> None:
        super().from_json(data)
        self._k = data.get("params", {}).get("k", 1.0)
        if dpg.does_item_exist(f"{self.node_id}_k"):
            dpg.set_value(f"{self.node_id}_k", self._k)


# 대응하는 도메인 모델 (간단한 경우 같은 파일에 작성 가능)
class _GainSimNode(SimNode):
    def __init__(self, k: float) -> None:
        self._k = k

    def evaluate(self, ctx, inputs):
        return {"value_out": inputs.get("value_in", 0.0) * self._k}
```

---

## 포트 태그 규칙

DPG 아이템 태그는 **자동으로** 다음 형식으로 생성됩니다:

```
노드 태그   : dpg_node_{node_id}
출력 포트   : dpg_{node_id}_out_{port_name}
입력 포트   : dpg_{node_id}_in_{port_name}
```

예시 (node_id = "gain_0", port_name = "value_out"):
```
dpg_gain_0_out_value_out
```

이 태그는 `jump_lines.py` 와 `command_history.py` 에서 좌표 계산·링크 복원에 사용되므로 **변경하면 안 됩니다**.

---

## 링크 색상 추가

`app/ui/link_styler.py` 의 `_PORT_COLORS` 리스트에 포트 이름 키워드를 추가합니다:

```python
_PORT_COLORS: list[tuple[str, tuple]] = [
    ...
    ("value",  (120, 120, 180, 220)),   # 보라-회색: 일반 실수 신호
]
```

우선순위는 **리스트 순서**이므로 더 구체적인 키워드를 앞에 배치합니다.

---

## 노드 아이콘 추가

`app/ui/icon_loader.py` 에서 그리기 함수를 추가합니다:

```python
def _draw_gain(draw_list: int, x: int, y: int,
               s: int, color: tuple) -> None:
    # 삼각형 게인 심볼 그리기
    pts = [(x + s//4, y + s//4),
           (x + s//4, y + 3*s//4),
           (x + 3*s//4, y + s//2)]
    dpg.draw_polygon(pts, color=color, fill=color, parent=draw_list)

# _MAKERS 딕셔너리에 등록
_MAKERS["gain"] = _draw_gain
```

---

## 등록 완료 체크리스트

- [ ] `app/nodes/h2_nodes.py` — 클래스 작성
- [ ] `NODE_CLASSES["gain"] = GainDpgNode` 추가
- [ ] `PALETTE` 에 항목 추가 `{"type": "gain", "label": "Gain", "icon": "gain"}`
- [ ] `app/ui/icon_loader.py` — 아이콘 등록
- [ ] `app/ui/link_styler.py` — 포트 색상 추가 (필요시)
- [ ] `tests/` — 동작 검증 테스트 추가
