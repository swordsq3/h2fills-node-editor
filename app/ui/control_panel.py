"""
Control Panel — Run / Step / Pause / Reset 버튼 및 시뮬레이션 파라미터 입력.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import dearpygui.dearpygui as dpg

if TYPE_CHECKING:
    from app.engine.orchestrator import Orchestrator


class ControlPanel:
    def __init__(self, orchestrator: "Orchestrator") -> None:
        self._orc = orchestrator
        self._build()

    def _build(self) -> None:
        with dpg.window(label="시뮬레이션 제어", tag="ctrl_panel",
                        width=350, height=220, pos=(10, 30)):
            dpg.add_text("시뮬레이션 파라미터")
            dpg.add_separator()
            dpg.add_input_float(label="dt [s]", tag="inp_dt",
                                default_value=self._orc.time_ctrl.dt,
                                min_value=0.01, max_value=10.0, step=0.1)
            dpg.add_input_float(label="t_end [s]", tag="inp_tend",
                                default_value=self._orc.time_ctrl.t_end,
                                min_value=10.0, max_value=3600.0, step=10.0)
            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_button(label="▶ Run",   callback=self._on_run,   width=70)
                dpg.add_button(label="⏸ Pause", callback=self._on_pause, width=70)
                dpg.add_button(label="⏭ Step",  callback=self._on_step,  width=70)
                dpg.add_button(label="↺ Reset", callback=self._on_reset, width=70)
            dpg.add_separator()
            dpg.add_text("t = 0.00 s", tag="lbl_time")
            dpg.add_progress_bar(tag="pb_progress", default_value=0.0, width=-1)

    def _on_run(self) -> None:
        self._orc.time_ctrl.dt = dpg.get_value("inp_dt")
        self._orc.time_ctrl.t_end = dpg.get_value("inp_tend")
        self._orc.start()

    def _on_pause(self) -> None:
        self._orc.pause()

    def _on_step(self) -> None:
        self._orc.time_ctrl.dt = dpg.get_value("inp_dt")
        self._orc.step_once()

    def _on_reset(self) -> None:
        self._orc.reset()
        dpg.set_value("lbl_time", "t = 0.00 s")
        dpg.set_value("pb_progress", 0.0)

    def update_status(self) -> None:
        t = self._orc.current_time
        dpg.set_value("lbl_time", f"t = {t:.2f} s")
        dpg.set_value("pb_progress", self._orc.time_ctrl.progress)
