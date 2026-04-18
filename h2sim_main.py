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
from app.ui.control_panel import ControlPanel
from app.ui.scope_view import ScopeView


def build_graph(orc: Orchestrator) -> None:
    """
    공급뱅크(Supply) → 밸브(Valve) → 차량 탱크(Tank) 연결.

    포트 매핑:
      supply.P_MPa          → valve.P_upstream_MPa
      supply.T_K            → valve.T_upstream_K
      tank.P_MPa            → valve.P_downstream_MPa   (피드백)
      valve.mass_flow_kg_s  → tank.mass_flow_in
      supply.T_K            → tank.T_in
    """
    supply = SupplyNode(SupplyParams(P_MPa=87.5, T_K=233.15))
    valve  = ValveNode(ValveParams(Cv=0.8, orifice_area=3e-5))
    tank   = TankNode(TankParams(volume=0.1218, P_init=5.0, T_init=288.15))

    g = orc.graph
    g.register_node("supply", supply)
    g.register_node("valve",  valve)
    g.register_node("tank",   tank)

    # supply → valve
    g.connect("supply", "P_MPa", "valve", "P_upstream_MPa")
    g.connect("supply", "T_K",   "valve", "T_upstream_K")

    # valve → tank
    g.connect("valve", "mass_flow_kg_s", "tank", "mass_flow_in")

    # supply 온도 → tank (유입 가스 온도)
    g.connect("supply", "T_K", "tank", "T_in")

    # 탱크 현재 압력 → valve 하류 압력 (피드백 루프는 한 tick 지연으로 처리)
    # 주의: 순환 감지를 피하기 위해 이전 tick 캐시를 직접 참조
    # 이는 SupplyNode가 매 tick 탱크 압력을 읽어 valve 하류로 전달하는 방식으로 처리됨

    orc.time_ctrl.dt   = 1.0
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
            # 탱크 현재 압력을 valve 하류 입력으로 피드백 (1 tick 지연)
            tank_output = orc.graph.get_output("tank")
            if tank_output:
                supply_node = orc.graph._nodes.get("supply")
                if supply_node:
                    supply_node.set_downstream_P(tank_output.get("P_MPa", 5.0))

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
