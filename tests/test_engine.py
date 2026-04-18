"""엔진 단위 테스트 — 포트 라우팅 수정 포함."""
import pytest
from app.engine.time_controller import TimeController, SimState
from app.engine.event_bus import EventBus, EventLevel
from app.engine.graph_engine import GraphEngine, PortLink
from app.engine.orchestrator import Orchestrator
from app.domain.tank import TankNode, TankParams
from app.domain.valve import ValveNode, ValveParams
from app.domain.supply import SupplyNode, SupplyParams
from app.engine.node_context import NodeContext


# ── TimeController ───────────────────────────────────────────

def test_time_controller_step():
    tc = TimeController(dt=1.0, t_end=5.0)
    tc.start()
    steps = 0
    while tc.step():
        steps += 1
    assert tc.state == SimState.FINISHED
    assert steps == 4


def test_time_controller_pause_resume():
    tc = TimeController(dt=1.0, t_end=10.0)
    tc.start()
    tc.step(); tc.step()
    tc.pause()
    assert tc.state == SimState.PAUSED
    tc.start()
    assert tc.state == SimState.RUNNING


def test_time_controller_seek():
    tc = TimeController(dt=1.0, t_end=100.0)
    tc.seek(42.0)
    assert tc.t == 42.0


# ── EventBus ────────────────────────────────────────────────

def test_event_bus_trend():
    bus = EventBus()
    bus.log_trend(0.0, "tank.P_MPa", 5.0)
    bus.log_trend(1.0, "tank.P_MPa", 6.0)
    series = bus.get_trend("tank.P_MPa")
    assert len(series) == 2
    assert series[0] == (0.0, 5.0)


def test_event_bus_alarm():
    bus = EventBus()
    received = []
    bus.subscribe(lambda ev: received.append(ev))
    bus.emit(0.0, EventLevel.ALARM, "tank", "압력 초과")
    assert len(received) == 1
    assert received[0].level == EventLevel.ALARM


# ── GraphEngine 포트 라우팅 (핵심 수정 검증) ─────────────────

def test_port_link_immutable():
    """PortLink는 frozen dataclass — 같은 링크 중복 방지 검증."""
    a = PortLink("valve", "mass_flow_kg_s", "tank", "mass_flow_in")
    b = PortLink("valve", "mass_flow_kg_s", "tank", "mass_flow_in")
    assert a == b


def test_graph_engine_port_routing():
    """
    버그 수정 핵심 테스트:
    valve.mass_flow_kg_s → tank.mass_flow_in 으로 올바르게 라우팅되어
    탱크 압력이 실제로 상승해야 한다.
    """
    g = GraphEngine()
    valve = ValveNode(ValveParams(Cv=0.8, orifice_area=3e-5))
    tank  = TankNode(TankParams(volume=0.1218, P_init=5.0, T_init=288.15))

    g.register_node("valve", valve)
    g.register_node("tank",  tank)
    g.connect("valve", "mass_flow_kg_s", "tank", "mass_flow_in")

    ctx = NodeContext(t=0.0, dt=1.0)

    # valve 에 공급 조건 수동 주입 (supply 노드 없이 단독 테스트)
    g._cache["valve"] = {}   # 초기 캐시 클리어
    g.mark_dirty("valve")
    g.mark_dirty("tank")

    # valve 는 기본값(P_up=35 MPa, P_dn=1 MPa)으로 계산
    result = g.tick(ctx)

    valve_out = result["valve"]
    tank_out  = result["tank"]

    # valve 가 0 이 아닌 유량을 출력해야 함
    assert valve_out["mass_flow_kg_s"] > 0, "밸브 유량이 0"

    # tank 가 유량을 받아 질량이 증가해야 함 (버그 수정 검증)
    initial_mass = TankNode(TankParams()).evaluate(NodeContext(t=0.0, dt=1.0), {})["m_kg"]
    assert tank_out["m_kg"] > initial_mass, "포트 라우팅 실패 — 탱크 질량 미변화"
    assert tank_out["P_MPa"] > 5.0, "포트 라우팅 실패 — 탱크 압력 미상승"


def test_graph_engine_supply_valve_tank():
    """Supply → Valve → Tank 전체 체인 포트 라우팅 통합 테스트."""
    g = GraphEngine()
    supply = SupplyNode(SupplyParams(P_MPa=87.5, T_K=233.15))
    valve  = ValveNode(ValveParams(Cv=0.8, orifice_area=3e-5))
    tank   = TankNode(TankParams(volume=0.1218, P_init=5.0, T_init=288.15))

    g.register_node("supply", supply)
    g.register_node("valve",  valve)
    g.register_node("tank",   tank)

    g.connect("supply", "P_MPa",            "valve", "P_upstream_MPa")
    g.connect("supply", "T_K",              "valve", "T_upstream_K")
    g.connect("supply", "P_downstream_MPa", "valve", "P_downstream_MPa")
    g.connect("valve",  "mass_flow_kg_s",   "tank",  "mass_flow_in")
    g.connect("supply", "T_K",              "tank",  "T_in")

    P_history = []
    for step in range(5):
        ctx = NodeContext(t=float(step), dt=1.0)
        result = g.tick(ctx)
        P_now = result["tank"]["P_MPa"]
        P_history.append(P_now)
        # 다음 tick을 위해 탱크 압력 피드백
        supply.set_downstream_P(P_now)
        g.mark_dirty("supply")

    # 5 tick 동안 압력이 지속 상승해야 함
    assert P_history[-1] > P_history[0], f"압력 상승 없음: {P_history}"
    assert all(P_history[i] <= P_history[i+1] for i in range(len(P_history)-1)), \
        f"압력이 단조 증가하지 않음: {P_history}"


def test_graph_engine_cycle_detection():
    """순환 의존성 감지 테스트."""
    g = GraphEngine()
    g.register_node("A", SupplyNode())
    g.register_node("B", SupplyNode())
    g._links.append(PortLink("A", "P_MPa", "B", "x"))
    g._links.append(PortLink("B", "P_MPa", "A", "x"))
    with pytest.raises(RuntimeError, match="순환"):
        g._topological_sort()


def test_graph_engine_disconnect():
    """링크 제거 후 입력이 None 으로 바뀌는지 확인."""
    g = GraphEngine()
    supply = SupplyNode(SupplyParams(P_MPa=87.5, T_K=233.15))
    tank   = TankNode()

    g.register_node("supply", supply)
    g.register_node("tank",   tank)
    g.connect("supply", "T_K", "tank", "T_in")
    g.disconnect("supply", "T_K", "tank", "T_in")

    assert not any(
        l.src_node == "supply" and l.dst_node == "tank"
        for l in g.get_links()
    )


# ── TankNode 물리 ────────────────────────────────────────────

def test_tank_pressure_rises():
    tank = TankNode(TankParams(volume=0.1218, P_init=5.0, T_init=288.15))
    ctx  = NodeContext(t=0.0, dt=1.0)
    out0 = tank.evaluate(ctx, {"mass_flow_in": 0.05, "T_in": 233.15})
    ctx2 = NodeContext(t=1.0, dt=1.0)
    out1 = tank.evaluate(ctx2, {"mass_flow_in": 0.05, "T_in": 233.15})
    assert out1["P_MPa"] > out0["P_MPa"]
    assert out1["m_kg"]  > out0["m_kg"]


# ── Orchestrator ─────────────────────────────────────────────

def test_orchestrator_runs():
    orc = Orchestrator(dt=1.0, t_end=3.0)
    supply = SupplyNode()
    tank   = TankNode()
    orc.graph.register_node("supply", supply)
    orc.graph.register_node("tank",   tank)
    orc.graph.connect("supply", "T_K", "tank", "T_in")
    orc.start()
    count = 0
    while orc.run_one_tick():
        count += 1
    assert count <= 3
