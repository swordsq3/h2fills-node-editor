"""
H2FillS Node Editor UI — Simulink-style white theme.
  - 상단: 메뉴바 (파일/편집/시뮬레이션/보기) + 툴바
  - 왼쪽: 팔레트 패널 (클릭 추가 + 드래그-드롭)
  - 중앙: DearPyGui node_editor (흰색 캔버스, 직선+점프선)
  - 하단: 강화 상태바 (노드 수, 링크 수, Undo 가능 여부)
  - UX-005: Undo/Redo (Ctrl+Z/Y, 100단계)
  - UX-012: Quick Insert (Ctrl+Space)
  - MOD-001: Pre-flight validation
  - ARCH-004: 백그라운드 시뮬레이션 스레드
  - MOD-005: 모델 메타데이터
  - DATA-009: CSV 결과 내보내기
"""
from __future__ import annotations

import csv
import itertools
import json
import os
import queue as _q
import threading
import time
from typing import Any

import dearpygui.dearpygui as dpg

from app.engine.orchestrator import Orchestrator
from app.engine.event_bus    import EventLevel
from app.ui.icon_loader      import get_icon_tag
from app.ui.link_styler      import apply_link_theme
from app.ui.jump_lines       import JumpLineOverlay
from app.infra.save_manager  import SaveManager
from app.nodes.h2_nodes      import H2DpgNode, NODE_CLASSES, PALETTE
from app.ui.command_history  import (
    CommandHistory, AddNodeCmd, RemoveNodeCmd,
    AddLinkCmd, RemoveLinkCmd, BatchCmd,
)


# ── 백그라운드 시뮬레이션 러너 ────────────────────────────────────

class _SimRunner:
    """백그라운드 스레드에서 시뮬레이션 틱을 실행 (ARCH-004)."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop   = threading.Event()
        self._done   = threading.Event()
        self._lock   = threading.RLock()

    def start(self, tick_fn) -> None:
        self._stop.clear()
        self._done.clear()
        self._thread = threading.Thread(
            target=self._loop, args=(tick_fn,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def is_done(self) -> bool:
        return self._done.is_set()

    def lock(self):
        return self._lock

    def _loop(self, tick_fn) -> None:
        while not self._stop.is_set():
            with self._lock:
                still = tick_fn()
            if not still:
                self._done.set()
                break
            time.sleep(0.001)  # GIL 양보


# ── 메인 에디터 ───────────────────────────────────────────────────

class H2NodeEditor:
    EDITOR_TAG = "h2_node_editor"
    LEFT_W     = 148
    TOOLBAR_H  = 36
    STATUS_H   = 28

    def __init__(self, orchestrator: Orchestrator) -> None:
        self._orc        = orchestrator
        self._nodes:     dict[str, H2DpgNode] = {}
        self._links:     list[tuple[str, str, str, str]] = []
        self._dpg_links: dict[int, tuple[str, str, str, str]] = {}
        self._counter    = itertools.count()
        self._built      = False
        self._jump       = JumpLineOverlay()
        self._save_mgr   = SaveManager()
        self._history    = CommandHistory()
        self._sim_runner = _SimRunner()
        self._meta: dict[str, str] = {
            "title": "제목 없음", "author": "", "description": ""}

    # ── 빌드 ────────────────────────────────────────────────────

    def build(self) -> None:
        vw = dpg.get_viewport_width()
        vh = dpg.get_viewport_height()

        with dpg.window(tag="main_win", label="H2FillS",
                        width=vw, height=vh, pos=[0, 0],
                        no_title_bar=True, no_resize=True,
                        no_move=True, menubar=True,
                        no_scrollbar=True, no_scroll_with_mouse=True):
            self._build_menubar()
            self._build_toolbar()
            self._build_body()

        dpg.set_primary_window("main_win", True)
        self._built = True

    # ── 메뉴바 ──────────────────────────────────────────────────

    def _build_menubar(self) -> None:
        with dpg.menu_bar():
            # ── 파일 ─────────────────────────────────────────
            with dpg.menu(label="파일"):
                dpg.add_menu_item(label="새로 만들기  Ctrl+N",
                                  callback=self._on_new)
                dpg.add_separator()
                dpg.add_menu_item(label="저장 (JSON)  Ctrl+S",
                                  callback=self._on_save)
                dpg.add_menu_item(label="불러오기 (JSON)  Ctrl+O",
                                  callback=self._on_load)
                dpg.add_separator()
                with dpg.menu(label="템플릿 불러오기"):
                    dpg.add_menu_item(
                        label="기본 700bar 충전",
                        callback=lambda: self._load_template(
                            "template_basic_charge.json"))
                    dpg.add_menu_item(
                        label="스코프 모니터링",
                        callback=lambda: self._load_template(
                            "template_with_scope.json"))
                    dpg.add_menu_item(
                        label="MUX + 스코프",
                        callback=lambda: self._load_template(
                            "template_mux_scope.json"))
                dpg.add_separator()
                with dpg.menu(label="최근 파일", tag="recent_menu"):
                    dpg.add_menu_item(label="(없음)",
                                      tag="recent_placeholder",
                                      enabled=False)
                dpg.add_separator()
                dpg.add_menu_item(label="모델 정보...",
                                  callback=self._on_model_info)
                dpg.add_menu_item(label="결과 내보내기 (CSV)",
                                  callback=self._on_export_csv)

            # ── 편집 ─────────────────────────────────────────
            with dpg.menu(label="편집"):
                dpg.add_menu_item(label="실행 취소  Ctrl+Z",
                                  tag="menu_undo",
                                  callback=self._on_undo)
                dpg.add_menu_item(label="다시 실행  Ctrl+Y",
                                  tag="menu_redo",
                                  callback=self._on_redo)
                dpg.add_separator()
                dpg.add_menu_item(label="블록 빠른 추가  Ctrl+Space",
                                  callback=self._on_quick_insert)
                dpg.add_separator()
                dpg.add_menu_item(label="모두 삭제",
                                  callback=self._on_new)

            # ── 시뮬레이션 ────────────────────────────────────
            with dpg.menu(label="시뮬레이션"):
                dpg.add_menu_item(label="Run",   callback=self._on_run)
                dpg.add_menu_item(label="Pause", callback=self._on_pause)
                dpg.add_menu_item(label="Step",  callback=self._on_step)
                dpg.add_separator()
                dpg.add_menu_item(label="Reset", callback=self._on_reset)

            # ── 보기 ─────────────────────────────────────────
            with dpg.menu(label="보기"):
                dpg.add_menu_item(label="스코프 창",
                                  callback=self._on_open_scope)

        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if not dpg.does_item_exist("recent_menu"):
            return
        for child in dpg.get_item_children("recent_menu", 1) or []:
            dpg.delete_item(child)
        recent = self._save_mgr.get_recent()
        if not recent:
            dpg.add_menu_item(label="(없음)", parent="recent_menu",
                              enabled=False)
        else:
            for path in recent:
                label = os.path.basename(path)
                dpg.add_menu_item(
                    label=label, parent="recent_menu",
                    callback=lambda s, a, u=path: self._load_from_path(u))

    # ── 툴바 ────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        with dpg.group(horizontal=True, tag="toolbar_group"):
            dpg.add_button(label="  Run  ", callback=self._on_run,
                           width=90, height=self.TOOLBAR_H, tag="tb_run")
            dpg.add_button(label=" Pause ", callback=self._on_pause,
                           width=90, height=self.TOOLBAR_H, tag="tb_pause")
            dpg.add_button(label=" Step  ", callback=self._on_step,
                           width=90, height=self.TOOLBAR_H, tag="tb_step")
            dpg.add_button(label=" Reset ", callback=self._on_reset,
                           width=90, height=self.TOOLBAR_H, tag="tb_reset")

            _apply_button_theme("tb_run",   (40,  160,  60, 255))
            _apply_button_theme("tb_pause", (200, 130,  20, 255))
            _apply_button_theme("tb_step",  (40,  100, 180, 255))
            _apply_button_theme("tb_reset", (100, 100, 100, 255))

            dpg.add_spacer(width=8)
            dpg.add_button(label=" ↩ ", callback=self._on_undo,
                           width=40, height=self.TOOLBAR_H, tag="tb_undo")
            dpg.add_button(label=" ↪ ", callback=self._on_redo,
                           width=40, height=self.TOOLBAR_H, tag="tb_redo")
            _apply_button_theme("tb_undo", (90, 90, 120, 255))
            _apply_button_theme("tb_redo", (90, 90, 120, 255))

            dpg.add_spacer(width=16)
            dpg.add_text("t = 0.0 s", tag="tb_time",
                         color=(30, 120, 60, 255))
            dpg.add_spacer(width=8)
            dpg.add_progress_bar(tag="tb_prog", default_value=0.0,
                                 width=260, height=self.TOOLBAR_H - 8,
                                 overlay="0%")

    # ── 본문 ────────────────────────────────────────────────────

    def _build_body(self) -> None:
        vw = dpg.get_viewport_width()
        vh = dpg.get_viewport_height()
        body_h = vh - self.STATUS_H - self.TOOLBAR_H - 48

        with dpg.group(horizontal=True):
            # 팔레트
            with dpg.child_window(tag="palette_win",
                                  width=self.LEFT_W, height=body_h,
                                  border=True):
                dpg.add_text("컴포넌트", color=(50, 50, 80, 255))
                dpg.add_separator()
                dpg.add_spacer(height=4)
                for item in PALETTE:
                    self._build_palette_item(item)

            # 노드 에디터 캔버스
            with dpg.child_window(tag="editor_win",
                                  width=vw - self.LEFT_W - 20,
                                  height=body_h,
                                  border=False,
                                  no_scrollbar=True,
                                  no_scroll_with_mouse=True,
                                  payload_type="NODE_TYPE",
                                  drop_callback=self._on_node_drop):
                with dpg.node_editor(
                    tag=self.EDITOR_TAG,
                    callback=self._on_link,
                    delink_callback=self._on_delink,
                    minimap=True,
                    minimap_location=dpg.mvNodeMiniMap_Location_BottomRight,
                ):
                    pass

                # ImNodes 링크 투명화 → jump_lines.py 가 대신 그림
                try:
                    with dpg.theme(tag="ne_link_theme"):
                        with dpg.theme_component(dpg.mvNodeEditor):
                            dpg.add_theme_style(
                                dpg.mvNodeStyleVar_LinkLineSegmentsPerLength,
                                0, category=dpg.mvThemeCat_Nodes)
                            dpg.add_theme_color(
                                dpg.mvNodeCol_Link, (0, 0, 0, 0),
                                category=dpg.mvThemeCat_Nodes)
                            dpg.add_theme_color(
                                dpg.mvNodeCol_LinkHovered, (0, 0, 0, 0),
                                category=dpg.mvThemeCat_Nodes)
                            dpg.add_theme_color(
                                dpg.mvNodeCol_LinkSelected, (60, 120, 220, 60),
                                category=dpg.mvThemeCat_Nodes)
                    dpg.bind_item_theme(self.EDITOR_TAG, "ne_link_theme")
                except Exception:
                    pass

        # 강화 상태바 (UX-011)
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("Ready", tag="status_msg",
                         color=(160, 100, 20, 255))
            dpg.add_spacer(width=16)
            dpg.add_text("Nodes: 0", tag="sb_nodes",
                         color=(80, 80, 100, 255))
            dpg.add_spacer(width=8)
            dpg.add_text("Links: 0", tag="sb_links",
                         color=(80, 80, 100, 255))
            dpg.add_spacer(width=8)
            dpg.add_text("Undo: 0", tag="sb_undo",
                         color=(100, 80, 140, 255))
            dpg.add_spacer(width=16)
            dpg.add_text(
                "Ctrl+Scroll:줌  |  Mid-drag:이동  |  Del:삭제  "
                "|  Ctrl+Z:취소  |  Ctrl+Space:블록추가",
                color=(130, 130, 135, 255))

        # 키/마우스 핸들러
        with dpg.handler_registry(tag="editor_handlers"):
            dpg.add_key_press_handler(
                key=dpg.mvKey_Delete, callback=self._on_delete_selected)
            dpg.add_key_press_handler(
                key=dpg.mvKey_Z, callback=self._on_key_z)
            dpg.add_key_press_handler(
                key=dpg.mvKey_Y, callback=self._on_key_y)
            dpg.add_key_press_handler(
                key=dpg.mvKey_Spacebar, callback=self._on_key_space)
            dpg.add_key_press_handler(
                key=dpg.mvKey_N, callback=self._on_key_n)
            dpg.add_key_press_handler(
                key=dpg.mvKey_S, callback=self._on_key_s)
            dpg.add_key_press_handler(
                key=dpg.mvKey_O, callback=self._on_key_o)
            dpg.add_mouse_double_click_handler(
                callback=self._on_double_click)

    def _build_palette_item(self, item: dict) -> None:
        node_type = item["type"]
        label     = item["label"]
        icon_tag  = get_icon_tag(item["icon"])

        def _add_cb(s, a, u=node_type):
            self._history.execute(AddNodeCmd(u), self)
            self._refresh_statusbar()

        with dpg.group(horizontal=False):
            with dpg.group(horizontal=True):
                if icon_tag:
                    btn = dpg.add_image_button(
                        icon_tag, width=36, height=36,
                        callback=_add_cb, tag=f"btn_{node_type}")
                    with dpg.drag_payload(parent=btn,
                                          payload_type="NODE_TYPE",
                                          drag_data=node_type):
                        dpg.add_text(f"+ {label}")
                else:
                    btn = dpg.add_button(label="+", width=36, height=36,
                                         callback=_add_cb)
                dpg.add_text(label, color=(30, 30, 50, 255))
            dpg.add_spacer(height=6)

    # ── 노드 추가/삭제 ───────────────────────────────────────────

    def _add_node(self, node_type: str,
                  pos: tuple[int, int] | None = None,
                  node_id: str | None = None) -> H2DpgNode:
        if node_id is None:
            node_id = f"{node_type}_{next(self._counter)}"
        if node_id in self._nodes:
            return self._nodes[node_id]
        if pos is None:
            n   = len(self._nodes)
            pos = (200 + (n % 4) * 230, 80 + (n // 4) * 270)

        cls  = NODE_CLASSES[node_type]
        node = cls(node_id)
        node.build(self.EDITOR_TAG, pos)
        self._nodes[node_id] = node
        self._orc.graph.register_node(node_id, node.get_domain_node())
        return node

    def _on_node_drop(self, sender, app_data, user_data=None) -> None:
        node_type = app_data if isinstance(app_data, str) else ""
        if node_type not in NODE_CLASSES:
            return
        try:
            mp     = dpg.get_mouse_pos(local=False)
            ew_min = dpg.get_item_rect_min("editor_win")
            x = max(20, int(mp[0] - ew_min[0]))
            y = max(20, int(mp[1] - ew_min[1]))
        except Exception:
            n = len(self._nodes)
            x, y = 200 + (n % 4) * 230, 80 + (n // 4) * 270
        self._history.execute(AddNodeCmd(node_type, (x, y)), self)
        dpg.set_value("status_msg", f"+ {node_type} 추가됨")
        self._refresh_statusbar()

    def _on_delete_selected(self) -> None:
        sel_links = list(dpg.get_selected_links(self.EDITOR_TAG))
        sel_nodes = list(dpg.get_selected_nodes(self.EDITOR_TAG))

        node_ids: set[str] = set()
        for dpg_node_tag in sel_nodes:
            alias = dpg.get_item_alias(dpg_node_tag)
            node_ids.add(alias.replace("dpg_node_", "", 1))

        cmds = []
        # 선택된 링크 중 삭제될 노드에 연결되지 않은 것만 RemoveLinkCmd
        for lnk_id in sel_links:
            info = self._dpg_links.get(lnk_id)
            if info:
                sn, sp, dn, dp = info
                if sn not in node_ids and dn not in node_ids:
                    cmds.append(RemoveLinkCmd(lnk_id))
        for nid in node_ids:
            if nid in self._nodes:
                cmds.append(RemoveNodeCmd(nid))

        if cmds:
            self._history.execute(BatchCmd(cmds), self)
            self._refresh_statusbar()

    def _remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            return
        to_rm = [(sn, sp, dn, dp) for sn, sp, dn, dp in self._links
                 if sn == node_id or dn == node_id]
        for lnk in to_rm:
            self._links.remove(lnk)
            try: self._orc.graph.disconnect(*lnk)
            except Exception: pass
        self._nodes[node_id].close()
        self._orc.graph.disconnect_node(node_id)
        del self._nodes[node_id]

    # ── 링크 콜백 ────────────────────────────────────────────────

    def _on_link(self, sender, app_data) -> None:
        src_attr_id, dst_attr_id = app_data
        src_alias = dpg.get_item_alias(src_attr_id) or str(src_attr_id)
        dst_alias = dpg.get_item_alias(dst_attr_id) or str(dst_attr_id)

        sn, sp = self._parse_port_alias(src_alias, "out")
        dn, dp = self._parse_port_alias(dst_alias, "in")
        if not all([sn, sp, dn, dp]):
            return

        self._history.execute(AddLinkCmd(sn, sp, dn, dp), self)
        self._refresh_statusbar()

    def _on_delink(self, sender, app_data) -> None:
        self._history.execute(RemoveLinkCmd(app_data), self)
        self._refresh_statusbar()

    def _remove_link_by_dpg_id(self, dpg_link_id: int) -> None:
        info = self._dpg_links.pop(dpg_link_id, None)
        if info:
            sn, sp, dn, dp = info
            if (sn, sp, dn, dp) in self._links:
                self._links.remove((sn, sp, dn, dp))
            try: self._orc.graph.disconnect(sn, sp, dn, dp)
            except Exception: pass
        if dpg.does_item_exist(dpg_link_id):
            dpg.delete_item(dpg_link_id)

    @staticmethod
    def _parse_port_alias(alias: str, kind: str) -> tuple[str, str]:
        try:
            parts     = alias.split(f"_{kind}_", 1)
            node_part = parts[0].replace("dpg_", "", 1)
            port_name = parts[1]
            return node_part, port_name
        except (IndexError, ValueError):
            return "", ""

    # ── Undo/Redo ────────────────────────────────────────────────

    def _on_undo(self) -> None:
        if self._history.undo(self):
            dpg.set_value("status_msg", "실행 취소")
        self._refresh_statusbar()

    def _on_redo(self) -> None:
        if self._history.redo(self):
            dpg.set_value("status_msg", "다시 실행")
        self._refresh_statusbar()

    def _on_key_z(self) -> None:
        if (dpg.is_key_down(dpg.mvKey_LControl)
                or dpg.is_key_down(dpg.mvKey_RControl)):
            self._on_undo()

    def _on_key_y(self) -> None:
        if (dpg.is_key_down(dpg.mvKey_LControl)
                or dpg.is_key_down(dpg.mvKey_RControl)):
            self._on_redo()

    def _on_key_space(self) -> None:
        if (dpg.is_key_down(dpg.mvKey_LControl)
                or dpg.is_key_down(dpg.mvKey_RControl)):
            self._on_quick_insert()

    def _on_key_n(self) -> None:
        if (dpg.is_key_down(dpg.mvKey_LControl)
                or dpg.is_key_down(dpg.mvKey_RControl)):
            self._on_new()

    def _on_key_s(self) -> None:
        if (dpg.is_key_down(dpg.mvKey_LControl)
                or dpg.is_key_down(dpg.mvKey_RControl)):
            self._on_save()

    def _on_key_o(self) -> None:
        if (dpg.is_key_down(dpg.mvKey_LControl)
                or dpg.is_key_down(dpg.mvKey_RControl)):
            self._on_load()

    # ── Quick Insert (UX-012) ────────────────────────────────────

    def _on_quick_insert(self) -> None:
        win_tag = "quick_insert_win"
        if dpg.does_item_exist(win_tag):
            try:
                dpg.show_item(win_tag)
                dpg.focus_item("qi_search")
            except Exception:
                pass
            return

        try:
            mp = dpg.get_mouse_pos(local=False)
            px, py = int(mp[0]), int(mp[1])
        except Exception:
            px, py = 400, 300

        with dpg.window(tag=win_tag,
                        label="블록 빠른 추가 (Ctrl+Space)",
                        pos=[px, py], width=240, height=320,
                        no_scrollbar=False):
            dpg.add_input_text(
                tag="qi_search", hint="블록 이름 검색...",
                width=-1,
                callback=lambda s, a: self._populate_qi_list(a))
            dpg.add_separator()
            with dpg.group(tag="qi_list"):
                self._populate_qi_list("")

    def _populate_qi_list(self, filter_text: str) -> None:
        if not dpg.does_item_exist("qi_list"):
            return
        for child in dpg.get_item_children("qi_list", 1) or []:
            dpg.delete_item(child)
        fl = filter_text.lower()
        for item in PALETTE:
            if fl in item["label"].lower() or fl in item["type"].lower():
                t = item["type"]
                dpg.add_button(
                    label=item["label"], parent="qi_list", width=-1,
                    callback=lambda s, a, u=t: self._qi_add(u))

    def _qi_add(self, node_type: str) -> None:
        try:
            mp     = dpg.get_mouse_pos(local=False)
            ew_min = dpg.get_item_rect_min("editor_win")
            x = max(20, int(mp[0] - ew_min[0]))
            y = max(20, int(mp[1] - ew_min[1]))
        except Exception:
            n = len(self._nodes)
            x, y = 200 + (n % 4) * 230, 80 + (n // 4) * 270
        self._history.execute(AddNodeCmd(node_type, (x, y)), self)
        dpg.set_value("status_msg", f"+ {node_type} 추가됨")
        self._refresh_statusbar()
        try:
            dpg.hide_item("quick_insert_win")
        except Exception:
            pass

    # ── 시뮬레이션 제어 ─────────────────────────────────────────

    def _on_run(self) -> None:
        # MOD-001: Pre-flight validation
        errors = self._validate_graph()
        if errors:
            dpg.set_value("status_msg", f"[검증 오류] {errors[0]}")
            self._show_validation_errors(errors)
            return

        self._rebuild_graph_from_ui()
        self._orc.start()
        self._sim_runner.start(self._orc.run_one_tick)
        dpg.set_value("status_msg", "Running...")

    def _on_pause(self) -> None:
        self._sim_runner.stop()
        self._orc.pause()
        dpg.set_value("status_msg", "Paused")

    def _on_step(self) -> None:
        errors = self._validate_graph()
        if errors:
            dpg.set_value("status_msg", f"[검증 오류] {errors[0]}")
            return
        self._rebuild_graph_from_ui()
        self._orc.step_once()
        self._apply_feedback()
        self._update_nodes_display()
        self._update_status_bar()

    def _on_reset(self) -> None:
        self._sim_runner.stop()
        self._orc.reset()
        self._rebuild_graph_from_ui()
        dpg.set_value("tb_time",    "t = 0.0 s")
        dpg.set_value("tb_prog",    0.0)
        dpg.set_value("status_msg", "Reset")
        try:
            dpg.configure_item("tb_prog", overlay="0%")
        except Exception:
            pass

    # ── Pre-flight validation (MOD-001) ─────────────────────────

    def _validate_graph(self) -> list[str]:
        errors: list[str] = []
        if not self._nodes:
            errors.append("그래프가 비어 있습니다.")
            return errors

        connected_dst = {(dn, dp) for _, _, dn, dp in self._links}
        connected_src = {(sn, sp) for sn, sp, _, _ in self._links}
        connected_nodes = set()
        for sn, _, dn, _ in self._links:
            connected_nodes.add(sn)
            connected_nodes.add(dn)

        for nid, node in self._nodes.items():
            # 고립 노드 검사 (1개 이상 노드 존재 시)
            if len(self._nodes) > 1 and nid not in connected_nodes:
                errors.append(f"'{nid}': 연결 없는 고립 노드")
            # 필수 입력 포트 연결 확인 (tank, valve, precooler)
            if node.NODE_TYPE in ("tank", "valve", "precooler"):
                for port in node.INPUTS:
                    if (nid, port.name) not in connected_dst:
                        errors.append(
                            f"'{nid}': 입력 포트 '{port.label}' 미연결")

        return errors

    def _show_validation_errors(self, errors: list[str]) -> None:
        win_tag = "validation_win"
        if dpg.does_item_exist(win_tag):
            dpg.delete_item(win_tag)
        with dpg.window(tag=win_tag, label="검증 오류",
                        width=420, height=220, pos=[300, 200],
                        modal=False):
            dpg.add_text("시뮬레이션 실행 전 오류를 수정하세요:",
                         color=(200, 60, 40, 255))
            dpg.add_separator()
            for e in errors[:10]:
                dpg.add_text(f"  • {e}", color=(180, 60, 40, 255))
            dpg.add_separator()
            dpg.add_button(
                label="닫기",
                callback=lambda: dpg.delete_item(win_tag))

    def _rebuild_graph_from_ui(self) -> None:
        g = self._orc.graph
        for nid, dpg_node in self._nodes.items():
            g._nodes[nid] = dpg_node.get_domain_node()
        g._dirty.update(g._nodes.keys())

    def _apply_feedback(self) -> None:
        g = self._orc.graph
        for nid, node in self._nodes.items():
            if node.NODE_TYPE == "tank":
                out = g.get_output(nid)
                if out:
                    for sid, snode in self._nodes.items():
                        if snode.NODE_TYPE == "supply":
                            dom = g._nodes.get(sid)
                            if dom and hasattr(dom, "set_downstream_P"):
                                dom.set_downstream_P(out.get("P_MPa", 5.0))
            if node.NODE_TYPE == "valve":
                out = g.get_output(nid)
                if out:
                    for pid, pnode in self._nodes.items():
                        if pnode.NODE_TYPE == "precooler":
                            dom = g._nodes.get(pid)
                            if dom and hasattr(dom, "update_mdot_feedback"):
                                dom.update_mdot_feedback(
                                    out.get("mass_flow_kg_s", 0.0))
        for nid, node in self._nodes.items():
            if node.NODE_TYPE == "supply":
                g.mark_dirty(nid)

    def _update_nodes_display(self) -> None:
        g = self._orc.graph
        for nid, node in self._nodes.items():
            if node.NODE_TYPE == "tank" and hasattr(node, "update_status"):
                out = g.get_output(nid)
                if out:
                    node.update_status(out.get("P_MPa", 0),
                                       out.get("T_K",   0),
                                       out.get("SOC",   0))
            elif node.NODE_TYPE == "scope" and hasattr(node, "update_plot"):
                domain = g._nodes.get(nid)
                if domain:
                    node.update_plot(domain)
                    win_tag = f"scope_detail_{nid}"
                    if dpg.does_item_exist(win_tag):
                        self._refresh_scope_detail(nid, domain)

    def _update_status_bar(self) -> None:
        t   = self._orc.current_time
        prg = self._orc.time_ctrl.progress
        dpg.set_value("tb_time", f"t = {t:.1f} s")
        dpg.set_value("tb_prog", prg)
        try:
            dpg.configure_item("tb_prog", overlay=f"{prg*100:.0f}%")
        except Exception:
            pass

    def _refresh_statusbar(self) -> None:
        try:
            dpg.set_value("sb_nodes",
                          f"Nodes: {len(self._nodes)}")
            dpg.set_value("sb_links",
                          f"Links: {len(self._links)}")
            dpg.set_value("sb_undo",
                          f"Undo: {self._history.undo_count}")
        except Exception:
            pass

    # ── 저장/불러오기 ────────────────────────────────────────────

    def _build_save_dict(self) -> dict:
        return {
            "version": "2.0",
            "meta":    dict(self._meta),
            "nodes":   [n.to_json() for n in self._nodes.values()],
            "links": [
                {"src_node": sn, "src_port": sp,
                 "dst_node": dn, "dst_port": dp}
                for sn, sp, dn, dp in self._links
            ],
        }

    def _on_save(self) -> None:
        dpg.add_file_dialog(
            label="그래프 저장",
            default_path=os.path.join(os.getcwd(), "scenarios"),
            default_filename="graph.json",
            file_count=1,
            callback=self._do_save,
            tag="save_dialog",
            width=620, height=420,
            save=True,
        )

    def _do_save(self, sender, app_data) -> None:
        path = app_data.get("file_path_name", "")
        if not path:
            return
        if not path.endswith(".json"):
            path += ".json"
        try:
            self._save_mgr.save(path, self._build_save_dict())
            dpg.set_value("status_msg",
                          f"저장: {os.path.basename(path)}")
            self._refresh_recent_menu()
        except Exception as e:
            dpg.set_value("status_msg", f"[저장 오류] {e}")

    def _on_load(self) -> None:
        dpg.add_file_dialog(
            label="그래프 불러오기",
            default_path=os.path.join(os.getcwd(), "scenarios"),
            file_count=1,
            callback=self._do_load,
            tag="load_dialog",
            width=620, height=420,
            extensions=[".json", ".*"],
        )

    def _do_load(self, sender, app_data) -> None:
        path = app_data.get("file_path_name", "")
        if not path or not os.path.isfile(path):
            return
        self._load_from_path(path)

    def _load_from_path(self, path: str) -> None:
        try:
            data = self._save_mgr.load(path)
        except Exception as e:
            dpg.set_value("status_msg", f"[불러오기 오류] {e}")
            return
        self._on_new()
        self._apply_graph_data(data)
        dpg.set_value("status_msg",
                      f"불러오기: {os.path.basename(path)}")
        self._refresh_recent_menu()

    def _load_template(self, filename: str) -> None:
        base = os.path.join(
            os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))),
            "scenarios")
        path = os.path.join(base, filename)
        if not os.path.isfile(path):
            dpg.set_value("status_msg",
                          f"[오류] 템플릿 없음: {filename}")
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            dpg.set_value("status_msg", f"[템플릿 오류] {e}")
            return
        self._on_new()
        self._apply_graph_data(data)
        dpg.set_value("status_msg", f"템플릿: {filename}")

    def _apply_graph_data(self, data: dict) -> None:
        # 메타데이터 복원
        meta = data.get("meta", {})
        if meta:
            self._meta.update(meta)

        for nd in data.get("nodes", []):
            ntype = nd.get("type")
            nid   = nd.get("id")
            pos   = nd.get("pos", [200, 200])
            if ntype not in NODE_CLASSES:
                continue
            node = self._add_node(ntype, tuple(pos), node_id=nid)
            node.from_json(nd)

        for lk in data.get("links", []):
            sn, sp = lk["src_node"], lk["src_port"]
            dn, dp = lk["dst_node"], lk["dst_port"]
            src_attr = f"dpg_{sn}_out_{sp}"
            dst_attr = f"dpg_{dn}_in_{dp}"
            if (dpg.does_item_exist(src_attr)
                    and dpg.does_item_exist(dst_attr)):
                try:
                    self._orc.graph.connect(sn, sp, dn, dp)
                    lid = dpg.add_node_link(
                        src_attr, dst_attr, parent=self.EDITOR_TAG)
                    self._links.append((sn, sp, dn, dp))
                    self._dpg_links[lid] = (sn, sp, dn, dp)
                    apply_link_theme(lid, sp)
                except Exception:
                    pass

        self._refresh_statusbar()

    def _on_new(self) -> None:
        self._sim_runner.stop()
        self._orc.reset()
        for nid in list(self._nodes.keys()):
            self._remove_node(nid)
        self._links.clear()
        self._dpg_links.clear()
        self._history.clear()
        dpg.set_value("status_msg", "새 그래프")
        self._refresh_statusbar()

    # ── 모델 정보 (MOD-005) ──────────────────────────────────────

    def _on_model_info(self) -> None:
        win_tag = "model_info_win"
        if dpg.does_item_exist(win_tag):
            dpg.delete_item(win_tag)
        with dpg.window(tag=win_tag, label="모델 정보",
                        width=420, height=240, pos=[300, 200]):
            dpg.add_input_text(
                label="제목", tag="mi_title", width=260,
                default_value=self._meta.get("title", ""))
            dpg.add_input_text(
                label="작성자", tag="mi_author", width=260,
                default_value=self._meta.get("author", ""))
            dpg.add_input_text(
                label="설명", tag="mi_desc", width=260, height=70,
                multiline=True,
                default_value=self._meta.get("description", ""))
            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_button(label="저장",
                               callback=self._save_model_info)
                dpg.add_button(
                    label="닫기",
                    callback=lambda: dpg.delete_item(win_tag))

    def _save_model_info(self) -> None:
        try:
            self._meta["title"]       = dpg.get_value("mi_title")
            self._meta["author"]      = dpg.get_value("mi_author")
            self._meta["description"] = dpg.get_value("mi_desc")
            dpg.set_value("status_msg",
                          f"모델 정보 저장: {self._meta['title']}")
            if dpg.does_item_exist("model_info_win"):
                dpg.delete_item("model_info_win")
        except Exception as e:
            dpg.set_value("status_msg", f"[오류] {e}")

    # ── CSV 내보내기 (DATA-009) ──────────────────────────────────

    def _on_export_csv(self) -> None:
        dpg.add_file_dialog(
            label="CSV 내보내기",
            default_path=os.getcwd(),
            default_filename="simulation_results.csv",
            save=True,
            callback=self._do_export_csv,
            width=620, height=420,
        )

    def _do_export_csv(self, sender, app_data) -> None:
        path = app_data.get("file_path_name", "")
        if not path:
            return
        if not path.endswith(".csv"):
            path += ".csv"

        scope_data: dict[str, tuple[list, list]] = {}
        for nid, node in self._nodes.items():
            if node.NODE_TYPE == "scope":
                domain = self._orc.graph._nodes.get(nid)
                if domain:
                    for i in range(4):
                        times, vals = domain.get_series(f"ch{i}")
                        if times:
                            scope_data[f"{nid}_ch{i}"] = (
                                list(times), list(vals))

        if not scope_data:
            dpg.set_value("status_msg", "[내보내기] 스코프 데이터 없음")
            return

        first_times = next(iter(scope_data.values()))[0]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["time"] + list(scope_data.keys()))
                for i, t in enumerate(first_times):
                    row: list[Any] = [t]
                    for ts, vs in scope_data.values():
                        row.append(vs[i] if i < len(vs) else "")
                    writer.writerow(row)
            dpg.set_value("status_msg",
                          f"CSV 저장: {os.path.basename(path)}")
        except Exception as e:
            dpg.set_value("status_msg", f"[CSV 오류] {e}")

    # ── Scope 더블클릭 팝업 ──────────────────────────────────────

    def _on_double_click(self, sender, app_data) -> None:
        for nid, node in self._nodes.items():
            if node.NODE_TYPE == "scope":
                try:
                    if dpg.is_item_hovered(node.dpg_tag):
                        self._open_scope_detail(nid, node)
                        return
                except Exception:
                    pass

    def _open_scope_detail(self, nid: str, node) -> None:
        win_tag = f"scope_detail_{nid}"
        if dpg.does_item_exist(win_tag):
            try: dpg.focus_item(win_tag)
            except Exception: pass
            domain = self._orc.graph._nodes.get(nid)
            if domain:
                self._refresh_scope_detail(nid, domain)
            return

        with dpg.window(tag=win_tag,
                        label=f"스코프 상세 — {nid}",
                        width=720, height=460, pos=[180, 130]):
            dpg.add_text(
                "더블클릭으로 열림 | 시뮬레이션 중 실시간 업데이트",
                color=(120, 120, 130, 255))
            with dpg.plot(tag=f"sdp_{nid}",
                          height=400, width=700, no_menus=False):
                dpg.add_plot_legend(
                    location=dpg.mvPlot_Location_NorthEast)
                dpg.add_plot_axis(dpg.mvXAxis, label="t [s]",
                                  tag=f"sdp_xax_{nid}")
                dpg.add_plot_axis(dpg.mvYAxis, label="값",
                                  tag=f"sdp_yax_{nid}")
                for i in range(4):
                    dpg.add_line_series([], [], label=f"ch{i}",
                                        tag=f"sdp_s{i}_{nid}",
                                        parent=f"sdp_yax_{nid}")
        domain = self._orc.graph._nodes.get(nid)
        if domain:
            self._refresh_scope_detail(nid, domain)

    def _refresh_scope_detail(self, nid: str, domain) -> None:
        for i in range(4):
            s_tag = f"sdp_s{i}_{nid}"
            if not dpg.does_item_exist(s_tag):
                continue
            times, vals = domain.get_series(f"ch{i}")
            pairs = [(t, v) for t, v in zip(times, vals) if v == v]
            if pairs:
                ts, vs = zip(*pairs)
                dpg.set_value(s_tag, [list(ts), list(vs)])
            else:
                dpg.set_value(s_tag, [[], []])
        try:
            dpg.fit_axis_data(f"sdp_xax_{nid}")
            dpg.fit_axis_data(f"sdp_yax_{nid}")
        except Exception:
            pass

    # ── 스코프 뷰 창 ─────────────────────────────────────────────

    def _on_open_scope(self) -> None:
        if dpg.does_item_exist("scope_window"):
            dpg.show_item("scope_window")
        else:
            from app.ui.scope_view import ScopeView
            ScopeView(self._orc.bus, parent_tag="scope_window")

    # ── 메인 루프 tick (ARCH-004) ────────────────────────────────

    def tick(self) -> None:
        # 점프선 오버레이 매 프레임 갱신
        self._jump.update(self._links)

        if not self._orc.is_running:
            return

        # 백그라운드 스레드와 동기화하여 UI 업데이트
        if self._sim_runner._lock.acquire(blocking=False):
            try:
                self._apply_feedback()
                self._update_nodes_display()
            finally:
                self._sim_runner._lock.release()

        self._update_status_bar()
        self._save_mgr.autosave_if_due(self._build_save_dict)

        if self._sim_runner.is_done:
            self._orc.pause()
            self._sim_runner.stop()
            self._orc.bus.emit(
                self._orc.current_time,
                EventLevel.INFO, "Editor", "시뮬레이션 완료")
            dpg.set_value("status_msg", "시뮬레이션 완료")


# ── 헬퍼: 버튼 색상 테마 ──────────────────────────────────────────

def _apply_button_theme(btn_tag: str,
                        color: tuple[int, int, int, int]) -> None:
    r, g, b, a = color
    theme_tag = f"_btn_theme_{btn_tag}"
    with dpg.theme(tag=theme_tag):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,
                                (r, g, b, 220))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,
                                (min(r+40,255), min(g+40,255),
                                 min(b+40,255), 220))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,
                                (min(r+60,255), min(g+60,255),
                                 min(b+60,255), 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,
                                (255, 255, 255, 255))
    dpg.bind_item_theme(btn_tag, theme_tag)
