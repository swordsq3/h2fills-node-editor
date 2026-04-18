"""기본 엔진 단위 테스트."""
import pytest
from app.engine.time_controller import TimeController, SimState
from app.engine.event_bus import EventBus, EventLevel
from app.engine.orchestrator import Orchestrator
from app.domain.tank import TankNode, TankParams
from app.engine.node_context import NodeContext


def test_time_controller_step():
    tc = TimeController(dt=1.0, t_end=5.0)
    tc.start()
    steps = 0
    while tc.step():
        steps += 1
    assert tc.state == SimState.FINISHED
    assert steps == 4


def test_event_bus_trend():
    bus = EventBus()
    bus.log_trend(0.0, "tank.P_MPa", 5.0)
    bus.log_trend(1.0, "tank.P_MPa", 6.0)
    series = bus.get_trend("tank.P_MPa")
    assert len(series) == 2
    assert series[0] == (0.0, 5.0)


def test_tank_pressure_rises():
    tank = TankNode(TankParams(volume=0.1218, P_init=5.0, T_init=288.15))
    ctx = NodeContext(t=0.0, dt=1.0)
    out0 = tank.evaluate(ctx, {"mass_flow_in": 0.05, "T_in": 233.15})
    ctx2 = NodeContext(t=1.0, dt=1.0)
    out1 = tank.evaluate(ctx2, {"mass_flow_in": 0.05, "T_in": 233.15})
    assert out1["P_MPa"] > out0["P_MPa"]
    assert out1["m_kg"] > out0["m_kg"]


def test_orchestrator_runs():
    orc = Orchestrator(dt=1.0, t_end=3.0)
    tank = TankNode()
    orc.graph.register_node("tank", tank)
    orc.graph._topological_sort()
    orc.start()
    count = 0
    while orc.run_one_tick():
        count += 1
    assert count <= 3
