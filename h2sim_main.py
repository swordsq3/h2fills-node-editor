"""
H2FillS Node Editor — 메인 진입점 (MVP Stage 1)
  - Valve → Tank 포트 수준 연결
  - 고정 공급 조건 노드(SupplyNode)로 valve 입력 주입
  - Control Panel + Scope View 렌더
"""
import dearpygui.dearpygui as dpg

from app.engine.orchestrator import Orchestrator
from app.engine.node_context import NodeContext
from app.engine.event_bus import EventLevel
from app.domain.tank import TankNode, TankParams
from app.domain.valve import ValveNode, ValveParams
from app.domain.supply import SupplyNode, SupplyParams
from app.domain.precooler import PreCoolerNode, PreCoolerParams
from app.ui.control_panel import ControlPanel
from app.ui.scope_view import ScopeView


def build_graph(orc: Orchestrator) -> None:
    """
    Supply → PreCooler → Valve → Tank 포트 체인.

    포트 매핑:
      supply.P_MPa          → precooler.P_in_MPa
      supply.T_K            → precooler.T_in_K          (고온 공급 가스)
      precooler.P_out_MPa   → valve.P_upstream_MPa
      precooler.T_out_K     → valve.T_upstream_K        (냉각된 가스)
      precooler.mass_flow_kg_s → valve 입력 없음(valve 자체 계산)
      supply.P_downstream_MPa → valve.P_downstream_MPa  (탱크 현재압 피드백)
      valve.mass_flow_kg_s  → precooler.mass_flow_kg_s  (역방향 피드백용 — 1tick 지연)
      valve.mass_flow_kg_s  → tank.mass_flow_in
      precooler.T_out_K     → tank.T_in
    """
    supply    = SupplyNode(SupplyParams(P_MPa=87.5, T_K=300.0))   # 공급측 300 K (프리쿨러 전)
    precooler = PreCoolerNode(PreCoolerParams(UA=800.0, T_coolant_K=218.15, dP_MPa=0.5))
    valve     = ValveNode(ValveParams(Cv=0.8, orifice_area=3e-5))
    tank      = TankNode(TankParams(volume=0.1218, P_init=5.0, T_init=288.15))

    g = orc.graph
    g.register_node("supply",    supply)
    g.register_node("precooler", precooler)
    g.register_node("valve",     valve)
    g.register_node("tank",      tank)

    # supply → precooler
    g.connect("supply",    "P_MPa", "precooler", "P_in_MPa")
    g.connect("supply",    "T_K",   "precooler", "T_in_K")

    # precooler → valve
    g.connect("precooler", "P_out_MPa",      "valve", "P_upstream_MPa")
    g.connect("precooler", "T_out_K",        "valve", "T_upstream_K")

    # supply 피드백(탱크 현재압) → valve 하류
    g.connect("supply",    "P_downstream_MPa", "valve", "P_downstream_MPa")

    # valve → tank
    g.connect("valve",     "mass_flow_kg_s",  "tank",      "mass_flow_in")
    g.connect("precooler", "T_out_K",         "tank",      "T_in")

    # valve → precooler 유량 피드백은 순환 방지를 위해 DAG 링크 대신
    # 메인루프에서 1-tick 지연으로 precooler.update_mdot_feedback() 호출

    orc.time_ctrl.dt    = 1.0
    orc.time_ctrl.t_end = 300.0


def main() -> None:
    dpg.create_context()
    dpg.create_viewport(
        title="H2FillS Node Editor — 수소충전 시뮬레이션",
        width=1600, height=900
    )
    dpg.setup_dearpygui()

    orc = Orchestrator(dt=1.0, t_end=300.0)
    build_graph(orc)

    ctrl  = ControlPanel(orc)
    scope = ScopeView(orc.bus)

    dpg.show_viewport()

    while dpg.is_dearpygui_running():
        if orc.is_running:
            # 1-tick 지연 피드백: 이전 tick 결과로 다음 tick 입력 갱신
            tank_out   = orc.graph.get_output("tank")
            valve_out  = orc.graph.get_output("valve")
            supply_node    = orc.graph._nodes.get("supply")
            precooler_node = orc.graph._nodes.get("precooler")

            if tank_out and supply_node:
                supply_node.set_downstream_P(tank_out.get("P_MPa", 5.0))
            if valve_out and precooler_node:
                precooler_node.update_mdot_feedback(valve_out.get("mass_flow_kg_s", 0.0))

            orc.graph.mark_dirty("supply")
            still_running = orc.run_one_tick()

            if not still_running:
                orc.bus.emit(
                    orc.current_time,
                    EventLevel.INFO,
                    "Main",
                    "시뮬레이션 완료"
                )

            scope.refresh()
            ctrl.update_status()

        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
