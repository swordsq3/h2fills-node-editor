"""
Simulation Orchestrator — 세션 시작/정지, 실행 모드 제어.
TimeController + GraphEngine + EventBus 를 조율한다.
"""
from __future__ import annotations
from app.engine.time_controller import TimeController
from app.engine.graph_engine import GraphEngine
from app.engine.event_bus import EventBus, EventLevel
from app.engine.node_context import NodeContext


class Orchestrator:
    def __init__(self, dt: float = 1.0, t_end: float = 600.0) -> None:
        self.time_ctrl = TimeController(dt=dt, t_end=t_end)
        self.graph = GraphEngine()
        self.bus = EventBus()

    def reset(self) -> None:
        self.time_ctrl.reset()
        self.bus.reset()
        for node in self.graph._nodes.values():
            if hasattr(node, "reset"):
                node.reset()

    def run_one_tick(self) -> bool:
        """한 tick 실행. 계속 실행 가능하면 True."""
        ctx = NodeContext(
            t=self.time_ctrl.t,
            dt=self.time_ctrl.dt,
            logger=self.bus,
        )
        self.graph.tick(ctx)
        return self.time_ctrl.step()

    def start(self) -> None:
        self.time_ctrl.start()
        self.bus.emit(self.time_ctrl.t, EventLevel.INFO, "Orchestrator", "시뮬레이션 시작")

    def pause(self) -> None:
        self.time_ctrl.pause()
        self.bus.emit(self.time_ctrl.t, EventLevel.INFO, "Orchestrator", "일시 정지")

    def step_once(self) -> None:
        """STEP 모드: 한 tick 만 실행."""
        self.time_ctrl.start()
        self.run_one_tick()
        self.time_ctrl.pause()

    @property
    def current_time(self) -> float:
        return self.time_ctrl.t

    @property
    def is_running(self) -> bool:
        return self.time_ctrl.is_running
