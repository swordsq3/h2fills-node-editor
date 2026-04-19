# Undo/Redo 시스템

## 개요

`app/ui/command_history.py` 에 Command Pattern 으로 구현된 Undo/Redo 시스템입니다.

- **최대 100단계** 히스토리 유지
- **Ctrl+Z** / **Ctrl+Y** 단축키 및 툴바 **↩ / ↪** 버튼 지원
- `AddNodeCmd`, `RemoveNodeCmd`, `AddLinkCmd`, `RemoveLinkCmd`, `BatchCmd` 지원

---

## 클래스 구조

```
Command (ABC)
├── AddNodeCmd         노드 추가
├── RemoveNodeCmd      노드 삭제 (연결된 링크도 저장·복원)
├── AddLinkCmd         링크 추가
├── RemoveLinkCmd      링크 삭제
└── BatchCmd           여러 커맨드를 하나의 Undo 단계로 묶음

CommandHistory
├── execute(cmd, editor)   커맨드 실행 + undo 스택에 push
├── undo(editor)           undo 스택에서 pop, redo 스택에 push
└── redo(editor)           redo 스택에서 pop, 재실행
```

---

## Command ABC

```python
class Command(ABC):
    @abstractmethod
    def execute(self, ed: H2NodeEditor) -> None: ...
    @abstractmethod
    def undo(self, ed: H2NodeEditor) -> None: ...
```

`execute` 는 **처음 실행**과 **Redo** 에서 모두 호출됩니다.  
따라서 멱등성(idempotent)을 보장하거나, 상태를 커맨드 객체 내부에 저장해야 합니다.

---

## 예시: 커스텀 커맨드 작성

파라미터를 변경하는 Undo 가능한 커맨드:

```python
# app/ui/command_history.py 에 추가

class ChangeParamCmd(Command):
    """노드 파라미터 변경 커맨드."""

    def __init__(self, node_id: str, param_key: str,
                 old_val: float, new_val: float) -> None:
        self.node_id   = node_id
        self.param_key = param_key
        self.old_val   = old_val
        self.new_val   = new_val

    def execute(self, ed: H2NodeEditor) -> None:
        self._apply(ed, self.new_val)

    def undo(self, ed: H2NodeEditor) -> None:
        self._apply(ed, self.old_val)

    def _apply(self, ed: H2NodeEditor, val: float) -> None:
        node = ed._nodes.get(self.node_id)
        if node is None:
            return
        # DPG 위젯 업데이트
        tag = f"{self.node_id}_{self.param_key}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, val)
        # 도메인 모델 동기화
        dom = node.get_domain_node()
        if hasattr(dom, self.param_key):
            setattr(dom, self.param_key, val)
```

에디터에서 호출:
```python
old = dpg.get_value(f"{node_id}_P_MPa")
new_val = 90.0
editor._history.execute(
    ChangeParamCmd(node_id, "P_MPa", old, new_val),
    editor,
)
```

---

## BatchCmd — 여러 조작을 하나로 묶기

삭제 시 노드와 그에 연결된 링크를 동시에 하나의 Undo 단계로 처리:

```python
cmds = []
for lnk_id in standalone_links:
    cmds.append(RemoveLinkCmd(lnk_id))
for nid in node_ids:
    cmds.append(RemoveNodeCmd(nid))

editor._history.execute(BatchCmd(cmds), editor)
```

Undo 시 역순(reversed)으로 각 커맨드의 `undo()` 가 호출됩니다.

---

## 상태 확인

```python
history = editor._history

history.can_undo       # bool
history.can_redo       # bool
history.undo_count     # int — 상태바 "Undo: N" 표시에 사용
history.redo_count     # int

history.clear()        # 새 그래프 로드 시 초기화
```

---

## RemoveNodeCmd — 링크 복원

노드를 삭제하면 연결된 링크도 함께 저장됩니다. Undo 시 노드와 링크가 모두 복원됩니다.

```python
class RemoveNodeCmd(Command):
    def execute(self, ed):
        self._saved_json  = node.to_json()
        self._saved_links = [...]   # 연결된 모든 링크 저장
        ed._remove_node(node_id)

    def undo(self, ed):
        node = ed._add_node(type, pos, node_id)
        node.from_json(self._saved_json)
        for sn, sp, dn, dp in self._saved_links:
            _restore_link(ed, sn, sp, dn, dp)  # 링크 복원
```
