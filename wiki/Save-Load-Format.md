# 저장·불러오기 형식

## JSON 파일 스키마

```json
{
  "version": "2.0",
  "meta": {
    "title":       "700bar 기본 충전",
    "author":      "홍길동",
    "description": "Supply → PreCooler → Valve → Tank 기본 회로"
  },
  "nodes": [
    {
      "type":   "supply",
      "id":     "supply_0",
      "pos":    [40, 80],
      "params": {
        "P_MPa": 87.5,
        "T_K":   293.15
      }
    },
    {
      "type":   "tank",
      "id":     "tank_0",
      "pos":    [900, 80],
      "params": {
        "V_L":    120.0,
        "P0_MPa": 5.0,
        "T0_K":   293.15
      }
    }
  ],
  "links": [
    {
      "src_node": "supply_0",
      "src_port": "P_MPa",
      "dst_node": "precooler_0",
      "dst_port": "P_in_MPa"
    }
  ]
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `version` | string | 스키마 버전 (`"2.0"`) |
| `meta` | object | 모델 메타데이터 (선택) |
| `meta.title` | string | 모델 제목 |
| `meta.author` | string | 작성자 |
| `meta.description` | string | 설명 |
| `nodes[].type` | string | `NODE_CLASSES` 키와 일치 |
| `nodes[].id` | string | 노드 고유 ID |
| `nodes[].pos` | [x, y] | 에디터 캔버스 좌표 |
| `nodes[].params` | object | 노드 파라미터 (노드마다 다름) |
| `links[].src_node` | string | 출력 노드 ID |
| `links[].src_port` | string | 출력 포트 이름 |
| `links[].dst_node` | string | 입력 노드 ID |
| `links[].dst_port` | string | 입력 포트 이름 |

---

## SaveManager (app/infra/save_manager.py)

### 저장 (`save`)

```python
mgr = SaveManager()
mgr.save("scenarios/my_graph.json", graph_dict)
```

**순환 백업**: 저장 시 기존 파일을 `.bak1` → `.bak2` → `.bak3` 로 순환:
```
graph.json      ← 새 파일
graph.json.bak1 ← 이전 버전
graph.json.bak2 ← 2단계 이전
graph.json.bak3 ← 3단계 이전 (가장 오래된 백업)
```

### 불러오기 (`load`)

```python
data = mgr.load("scenarios/my_graph.json")
# 자동으로 버전 마이그레이션 적용
```

### 자동 저장 (`autosave_if_due`)

60초마다 `~/.h2sim_autosave.json` 에 자동 저장:

```python
# tick() 에서 매 프레임 호출
mgr.autosave_if_due(lambda: editor._build_save_dict())
```

### 최근 파일 (`get_recent`)

```python
recent_paths = mgr.get_recent()   # 최대 8개
# ~/.h2sim_recent.json 에 자동 유지
```

---

## 버전 마이그레이션

`app/infra/save_manager.py` 의 `_MIGRATORS` 딕셔너리에 마이그레이션 함수를 등록합니다:

```python
def _migrate_2_0(data: dict) -> dict:
    """v2.0 → v3.0: HeatBuffer 노드에 cp 필드 추가."""
    for node in data.get("nodes", []):
        if node.get("type") == "heat_buffer":
            node.setdefault("params", {}).setdefault("cp", 4186.0)
    data["version"] = "3.0"
    return data

_MIGRATORS: dict[str, callable] = {
    "1.0": _migrate_1_0,
    "2.0": _migrate_2_0,   # ← 새 마이그레이션 추가
}
```

마이그레이션은 체인으로 적용됩니다: `v1.0 → v2.0 → v3.0`

---

## 시나리오 템플릿

`scenarios/` 폴더의 JSON 파일은 메뉴 "파일 > 템플릿 불러오기" 에서 접근할 수 있습니다.

| 파일 | 내용 |
|------|------|
| `template_basic_charge.json` | Supply → PreCooler → Valve → Tank |
| `template_with_scope.json` | 위 회로 + Scope 모니터링 |
| `template_mux_scope.json` | MUX 신호 합성 + Scope |
| `default_700bar.json` | 700bar 충전 기본값 |

새 템플릿 추가: JSON 파일을 `scenarios/` 폴더에 저장하고 `h2_node_editor.py` 의 `_build_menubar()` 메뉴 항목에 추가합니다.
