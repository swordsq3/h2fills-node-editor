"""
Scope / Trend View — DearPyGui 기반 실시간 그래프 위젯.
EventBus 의 trend 데이터를 주기적으로 읽어 플롯을 갱신한다.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import dearpygui.dearpygui as dpg

if TYPE_CHECKING:
    from app.engine.event_bus import EventBus


class ScopeView:
    SIGNALS = ["tank.P_MPa", "tank.T_K", "tank.m_kg", "tank.SOC", "valve.mdot_kg_s"]
    COLORS = {
        "tank.P_MPa":      (255, 100, 100),
        "tank.T_K":        (100, 200, 255),
        "tank.m_kg":       (150, 255, 150),
        "tank.SOC":        (255, 220, 50),
        "valve.mdot_kg_s": (200, 150, 255),
    }

    def __init__(self, bus: "EventBus", parent_tag: str = "scope_window") -> None:
        self._bus = bus
        self._plot_tags: dict[str, int] = {}
        self._parent = parent_tag
        self._build()

    def _build(self) -> None:
        with dpg.window(label="스코프 / 트렌드 뷰", tag=self._parent,
                        width=700, height=500, pos=(850, 30)):
            with dpg.plot(label="시뮬레이션 트렌드", height=460, width=-1):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="시각 [s]", tag="scope_x")
                with dpg.plot_axis(dpg.mvYAxis, label="값", tag="scope_y"):
                    for sig in self.SIGNALS:
                        tag = dpg.add_line_series([], [], label=sig,
                                                  parent="scope_y")
                        self._plot_tags[sig] = tag

    def refresh(self) -> None:
        """매 프레임 또는 매 tick 후 호출해 그래프 갱신."""
        for sig, tag in self._plot_tags.items():
            series = self._bus.get_trend(sig)
            if not series:
                continue
            xs, ys = zip(*series)
            dpg.set_value(tag, [list(xs), list(ys)])
        dpg.fit_axis_data("scope_x")
