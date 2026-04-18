"""
H2FillS Node Editor — 메인 진입점 (MVP Stage 1~2)
  - DearPyGui 뷰포트 생성
  - Orchestrator (TimeController + GraphEngine + EventBus) 초기화
  - TankNode + ValveNode 연결
  - Control Panel + Scope View 렌더
  - 메인 루프에서 매 프레임 시뮬레이션 tick 진행
"""
import dearpygui.dearpygui as dpg

from app.engine.orchestrator import Orchestrator
from app.domain.tank import TankNode, TankParams
from app.domain.valve import ValveNode, ValveParams
from app.ui.control_panel import ControlPanel
from app.ui.scope_view import ScopeView


SUPPLY_PRESSURE_MPA = 87.5   # 공급 뱅크 압력
SUPPLY_TEMP_K = 233.15        # 프리쿨러 출구 온도 (-40°C)


def build_graph(orc: Orchestrator) -> None:
    """기본 시나리오: ValveNode → TankNode"""
    valve = ValveNode(ValveParams(Cv=0.8, orifice_area=3e-5))
    tank = TankNode(TankParams(volume=0.1218, P_init=5.0, T_init=288.15))

    orc.graph.register_node("valve", valve)
    orc.graph.register_node("tank", tank)
    orc.graph.connect("valve", "tank")

    orc.time_ctrl.dt = 1.0
    orc.time_ctrl.t_end = 300.0


def main() -> None:
    dpg.create_context()
    dpg.create_viewport(title="H2FillS Node Editor — 수소충전 시뮬레이션",
                        width=1600, height=900)
    dpg.setup_dearpygui()

    orc = Orchestrator(dt=1.0, t_end=300.0)
    build_graph(orc)

    ctrl = ControlPanel(orc)
    scope = ScopeView(orc.bus)

    dpg.show_viewport()

    while dpg.is_dearpygui_running():
        if orc.is_running:
            # valve 입력을 고정 공급 조건으로 주입
            valve_node = orc.graph._nodes.get("valve")
            tank_node = orc.graph._nodes.get("tank")
            if valve_node and tank_node:
                # upstream: supply bank / downstream: 차량 탱크 현재 압력
                orc.graph._cache["valve_input"] = {
                    "P_upstream_MPa": SUPPLY_PRESSURE_MPA,
                    "P_downstream_MPa": tank_node._P,
                    "T_upstream_K": SUPPLY_TEMP_K,
                    "open_fraction": 1.0,
                }

            still_running = orc.run_one_tick()
            if not still_running:
                orc.bus.emit(orc.current_time,
                             __import__("app.engine.event_bus", fromlist=["EventLevel"]).EventLevel.INFO,
                             "Main", "시뮬레이션 완료")

            scope.refresh()
            ctrl.update_status()

        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
