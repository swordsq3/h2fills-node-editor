"""
H2FillS Node Editor — 메인 진입점 (Simulink-style white theme)

사용법:
  python h2sim_main.py                        # GUI 실행
  python h2sim_main.py --headless --model X.json [--out results.csv] [--dt 1.0] [--tend 300]
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import dearpygui.dearpygui as dpg

from app.engine.orchestrator  import Orchestrator
from app.ui.font_manager      import setup_fonts
from app.ui.icon_loader       import setup_icons
from app.ui.h2_node_editor    import H2NodeEditor
from app.ui.scope_view        import ScopeView


def _apply_simulink_theme() -> None:
    """전역 Simulink 화이트 테마 — 흰색 캔버스, 어두운 텍스트/테두리."""
    with dpg.theme(tag="global_light"):
        with dpg.theme_component(dpg.mvAll):
            # ── ImGui 위젯 레이어 ─────────────────────────────────
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,       (245, 245, 245, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,        (240, 240, 240, 255))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,        (250, 250, 250, 255))
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg,      (220, 220, 225, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,        (210, 210, 215, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (195, 195, 210, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,  (180, 180, 205, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Text,           (20,  20,  20,  255))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,   (130, 130, 130, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border,         (160, 160, 165, 255))
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow,   (0,   0,   0,   0  ))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,        (200, 200, 205, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,  (175, 178, 195, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed,(210,210,215,255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    (225, 225, 228, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,  (170, 170, 175, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered,(150,150,160,255))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (120,120,135,255))
            dpg.add_theme_color(dpg.mvThemeCol_Button,         (200, 200, 210, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  (180, 190, 220, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   (155, 165, 205, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Header,         (195, 210, 235, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,  (175, 195, 230, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,   (155, 175, 215, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Separator,      (160, 160, 165, 255))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,      (40,  100, 220, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,     (120, 160, 220, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive,(80, 130, 210, 255))
            # ── ImNodes 캔버스 ────────────────────────────────────
            dpg.add_theme_color(dpg.mvNodeCol_GridBackground,
                                (255, 255, 255, 255), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_GridLine,
                                (205, 205, 210, 200), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackground,
                                (252, 252, 252, 245), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundHovered,
                                (240, 245, 255, 255), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundSelected,
                                (225, 235, 255, 255), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeOutline,
                                (55,  55,  75,  220), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_Pin,
                                (80,  80,  100, 220), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_PinHovered,
                                (30,  80,  200, 255), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_BoxSelector,
                                (80,  80,  200,  50), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_BoxSelectorOutline,
                                (60,  60,  180, 180), category=dpg.mvThemeCat_Nodes)
            # ── ImNodes 스타일 vars ───────────────────────────────
            dpg.add_theme_style(dpg.mvNodeStyleVar_NodeBorderThickness, 1.5,
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_style(dpg.mvNodeStyleVar_NodeCornerRounding,  3.0,
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_style(dpg.mvNodeStyleVar_GridSpacing,        32.0,
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_style(dpg.mvNodeStyleVar_PinCircleRadius,     5.0,
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_style(dpg.mvNodeStyleVar_PinOffset,           0.0,
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_style(dpg.mvNodeStyleVar_LinkThickness,       2.0,
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_style(dpg.mvNodeStyleVar_LinkLineSegmentsPerLength, 0,
                                category=dpg.mvThemeCat_Nodes)
    dpg.bind_theme("global_light")


def _load_default_graph(editor: H2NodeEditor) -> None:
    """기본 Supply → PreCooler → Valve → Tank 그래프."""
    from app.ui.link_styler import apply_link_theme
    g = editor

    g._add_node("supply",    (40,  80),  "supply_0")
    g._add_node("precooler", (340, 80),  "precooler_0")
    g._add_node("valve",     (640, 80),  "valve_0")
    g._add_node("tank",      (900, 80),  "tank_0")

    def link(sn, sp, dn, dp):
        try:
            g._orc.graph.connect(sn, sp, dn, dp)
            src = f"dpg_{sn}_out_{sp}"
            dst = f"dpg_{dn}_in_{dp}"
            if dpg.does_item_exist(src) and dpg.does_item_exist(dst):
                lid = dpg.add_node_link(src, dst, parent=H2NodeEditor.EDITOR_TAG)
                g._links.append((sn, sp, dn, dp))
                g._dpg_links[lid] = (sn, sp, dn, dp)
                apply_link_theme(lid, sp)
        except Exception as e:
            print(f"[WARN] link {sn}.{sp}→{dn}.{dp}: {e}", flush=True)

    link("supply_0",    "P_MPa",            "precooler_0", "P_in_MPa")
    link("supply_0",    "T_K",              "precooler_0", "T_in_K")
    link("precooler_0", "P_out_MPa",        "valve_0",     "P_upstream_MPa")
    link("precooler_0", "T_out_K",          "valve_0",     "T_upstream_K")
    link("supply_0",    "P_downstream_MPa", "valve_0",     "P_downstream_MPa")
    link("valve_0",     "mass_flow_kg_s",   "tank_0",      "mass_flow_in")
    link("precooler_0", "T_out_K",          "tank_0",      "T_in")


def main() -> None:
    dpg.create_context()
    setup_fonts()
    setup_icons()

    # Simulink 화이트 테마 적용 (폰트 바인딩 이후, build 이전)
    _apply_simulink_theme()

    dpg.create_viewport(
        title="H2FillS — Hydrogen Charging Simulation",
        width=1600, height=900,
    )
    dpg.setup_dearpygui()

    orc    = Orchestrator(dt=1.0, t_end=300.0)
    editor = H2NodeEditor(orc)
    editor.build()

    # 점프선 오버레이 초기화 (viewport 표시 전에 drawlist 등록)
    editor._jump.ensure_init()

    # 기본 그래프
    _load_default_graph(editor)

    scope = ScopeView(orc.bus, parent_tag="scope_window")

    dpg.show_viewport()

    while dpg.is_dearpygui_running():
        editor.tick()
        scope.refresh()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


def headless(model_path: str, out_csv: str | None,
             dt: float, t_end: float) -> None:
    """GUI 없이 시뮬레이션 실행 후 CSV 출력 (SIM-010)."""
    import csv
    from app.engine.orchestrator   import Orchestrator
    from app.engine.node_context   import NodeContext
    from app.infra.save_manager    import SaveManager
    from app.nodes.h2_nodes        import NODE_CLASSES

    print(f"[Headless] 모델: {model_path}", flush=True)
    data = SaveManager().load(model_path)

    orc = Orchestrator(dt=dt, t_end=t_end)

    # 노드 등록
    node_objs: dict = {}
    for nd in data.get("nodes", []):
        ntype = nd.get("type")
        nid   = nd.get("id")
        if ntype not in NODE_CLASSES:
            continue
        cls  = NODE_CLASSES[ntype]
        node = cls(nid)
        # from_json에는 dpg가 필요하므로 도메인 노드만 등록
        dom  = node.get_domain_node()
        orc.graph.register_node(nid, dom)
        node_objs[nid] = dom

    # 링크 연결
    for lk in data.get("links", []):
        try:
            orc.graph.connect(
                lk["src_node"], lk["src_port"],
                lk["dst_node"], lk["dst_port"])
        except Exception as e:
            print(f"[WARN] {e}", flush=True)

    # 실행
    orc.start()
    step = 0
    while orc.is_running:
        ctx = NodeContext(t=orc.current_time, dt=orc.time_ctrl.dt,
                          logger=orc.bus)
        orc.graph.tick(ctx)
        still = orc.time_ctrl.step()
        step += 1
        if step % 50 == 0:
            print(f"  t = {orc.current_time:.1f} s", flush=True)
        if not still:
            break

    print(f"[Headless] 완료. t = {orc.current_time:.1f} s", flush=True)

    # CSV 저장
    if out_csv:
        scope_data: dict[str, tuple[list, list]] = {}
        for nid, dom in node_objs.items():
            if hasattr(dom, "get_series"):
                for i in range(4):
                    ts, vs = dom.get_series(f"ch{i}")
                    if ts:
                        scope_data[f"{nid}_ch{i}"] = (list(ts), list(vs))
        if scope_data:
            first_times = next(iter(scope_data.values()))[0]
            with open(out_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["time"] + list(scope_data.keys()))
                for i, t in enumerate(first_times):
                    row = [t] + [
                        vs[i] if i < len(vs) else ""
                        for (_, vs) in scope_data.values()
                    ]
                    w.writerow(row)
            print(f"[Headless] CSV: {out_csv}", flush=True)
        else:
            print("[Headless] 스코프 데이터 없음 — CSV 생략", flush=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="H2FillS Simulation")
    ap.add_argument("--headless", action="store_true",
                    help="GUI 없이 실행")
    ap.add_argument("--model",   default=None,
                    help="모델 JSON 경로 (headless 전용)")
    ap.add_argument("--out",     default=None,
                    help="CSV 출력 경로 (headless 전용)")
    ap.add_argument("--dt",      type=float, default=1.0,
                    help="시뮬레이션 타임스텝 (초)")
    ap.add_argument("--tend",    type=float, default=300.0,
                    help="시뮬레이션 종료 시각 (초)")
    args = ap.parse_args()

    if args.headless:
        if not args.model:
            print("[오류] --headless 사용 시 --model 필수", flush=True)
            sys.exit(1)
        headless(args.model, args.out, args.dt, args.tend)
    else:
        main()
