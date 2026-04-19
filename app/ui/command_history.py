"""
command_history.py — Undo/Redo Command Pattern (UX-005).
지원 커맨드: 노드 추가/삭제, 링크 추가/삭제, 일괄 커맨드.
최대 100 단계 히스토리.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import dearpygui.dearpygui as dpg
from app.ui.link_styler import apply_link_theme

if TYPE_CHECKING:
    from app.ui.h2_node_editor import H2NodeEditor


# ── 기본 커맨드 ABC ───────────────────────────────────────────────

class Command(ABC):
    @abstractmethod
    def execute(self, ed: "H2NodeEditor") -> None: ...
    @abstractmethod
    def undo(self, ed: "H2NodeEditor") -> None: ...


# ── 노드 추가 ─────────────────────────────────────────────────────

class AddNodeCmd(Command):
    def __init__(self, node_type: str,
                 pos: tuple[int, int] | None = None,
                 node_id: str | None = None) -> None:
        self.node_type = node_type
        self.pos       = pos
        self.node_id   = node_id   # execute 후 확정

    def execute(self, ed: "H2NodeEditor") -> None:
        node = ed._add_node(self.node_type, self.pos, self.node_id)
        self.node_id = node.node_id

    def undo(self, ed: "H2NodeEditor") -> None:
        if self.node_id:
            ed._remove_node(self.node_id)


# ── 노드 삭제 ─────────────────────────────────────────────────────

class RemoveNodeCmd(Command):
    def __init__(self, node_id: str) -> None:
        self.node_id      = node_id
        self._saved_json: dict | None = None
        self._saved_links: list[tuple] = []

    def execute(self, ed: "H2NodeEditor") -> None:
        if self.node_id not in ed._nodes:
            return
        node = ed._nodes[self.node_id]
        self._saved_json  = node.to_json()
        self._saved_links = [
            (sn, sp, dn, dp) for sn, sp, dn, dp in ed._links
            if sn == self.node_id or dn == self.node_id
        ]
        ed._remove_node(self.node_id)

    def undo(self, ed: "H2NodeEditor") -> None:
        if not self._saved_json:
            return
        from app.nodes.h2_nodes import NODE_CLASSES
        ntype = self._saved_json.get("type", "")
        if ntype not in NODE_CLASSES:
            return
        pos  = tuple(self._saved_json.get("pos", [200, 200]))
        node = ed._add_node(ntype, pos, self.node_id)
        node.from_json(self._saved_json)
        for sn, sp, dn, dp in self._saved_links:
            _restore_link(ed, sn, sp, dn, dp)


# ── 링크 추가 ─────────────────────────────────────────────────────

class AddLinkCmd(Command):
    def __init__(self, sn: str, sp: str, dn: str, dp: str) -> None:
        self.sn = sn; self.sp = sp; self.dn = dn; self.dp = dp
        self._lid: int | None = None

    def execute(self, ed: "H2NodeEditor") -> None:
        src_attr = f"dpg_{self.sn}_out_{self.sp}"
        dst_attr = f"dpg_{self.dn}_in_{self.dp}"
        if not (dpg.does_item_exist(src_attr) and dpg.does_item_exist(dst_attr)):
            return
        if (self.sn, self.sp, self.dn, self.dp) in ed._links:
            return
        try:
            ed._orc.graph.connect(self.sn, self.sp, self.dn, self.dp)
        except RuntimeError as e:
            dpg.set_value("status_msg", f"[오류] {e}")
            return
        self._lid = dpg.add_node_link(src_attr, dst_attr, parent=ed.EDITOR_TAG)
        ed._links.append((self.sn, self.sp, self.dn, self.dp))
        ed._dpg_links[self._lid] = (self.sn, self.sp, self.dn, self.dp)
        apply_link_theme(self._lid, self.sp)

    def undo(self, ed: "H2NodeEditor") -> None:
        if self._lid is not None:
            ed._remove_link_by_dpg_id(self._lid)
            self._lid = None
        else:
            lnk = (self.sn, self.sp, self.dn, self.dp)
            if lnk in ed._links:
                ed._links.remove(lnk)
                try: ed._orc.graph.disconnect(*lnk)
                except Exception: pass


# ── 링크 삭제 ─────────────────────────────────────────────────────

class RemoveLinkCmd(Command):
    def __init__(self, dpg_link_id: int) -> None:
        self._lid  = dpg_link_id
        self._info: tuple | None = None

    def execute(self, ed: "H2NodeEditor") -> None:
        self._info = ed._dpg_links.get(self._lid)
        ed._remove_link_by_dpg_id(self._lid)

    def undo(self, ed: "H2NodeEditor") -> None:
        if self._info:
            _restore_link(ed, *self._info)


# ── 일괄 커맨드 ───────────────────────────────────────────────────

class BatchCmd(Command):
    """여러 커맨드를 하나의 Undo 단계로 묶는다."""

    def __init__(self, cmds: list[Command]) -> None:
        self._cmds = cmds

    def execute(self, ed: "H2NodeEditor") -> None:
        for cmd in self._cmds:
            cmd.execute(ed)

    def undo(self, ed: "H2NodeEditor") -> None:
        for cmd in reversed(self._cmds):
            cmd.undo(ed)


# ── 링크 복원 헬퍼 ────────────────────────────────────────────────

def _restore_link(ed: "H2NodeEditor",
                  sn: str, sp: str, dn: str, dp: str) -> None:
    """링크를 그래프 엔진 + DPG UI 양쪽에 복원."""
    src_attr = f"dpg_{sn}_out_{sp}"
    dst_attr = f"dpg_{dn}_in_{dp}"
    if not (dpg.does_item_exist(src_attr) and dpg.does_item_exist(dst_attr)):
        return
    if (sn, sp, dn, dp) in ed._links:
        return
    try:
        ed._orc.graph.connect(sn, sp, dn, dp)
        lid = dpg.add_node_link(src_attr, dst_attr, parent=ed.EDITOR_TAG)
        ed._links.append((sn, sp, dn, dp))
        ed._dpg_links[lid] = (sn, sp, dn, dp)
        apply_link_theme(lid, sp)
    except Exception:
        pass


# ── 히스토리 관리자 ───────────────────────────────────────────────

class CommandHistory:
    """Undo/Redo 스택 (최대 max_size 단계)."""

    def __init__(self, max_size: int = 100) -> None:
        self._undo: list[Command] = []
        self._redo: list[Command] = []
        self._max  = max_size

    def execute(self, cmd: Command, ed: "H2NodeEditor") -> None:
        cmd.execute(ed)
        self._undo.append(cmd)
        if len(self._undo) > self._max:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self, ed: "H2NodeEditor") -> bool:
        if not self._undo:
            return False
        cmd = self._undo.pop()
        cmd.undo(ed)
        self._redo.append(cmd)
        return True

    def redo(self, ed: "H2NodeEditor") -> bool:
        if not self._redo:
            return False
        cmd = self._redo.pop()
        cmd.execute(ed)
        self._undo.append(cmd)
        return True

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_count(self) -> int:
        return len(self._undo)

    @property
    def redo_count(self) -> int:
        return len(self._redo)
