"""
ScopeSimNode — 스코프 도메인 노드.
최대 4개 채널의 시계열 데이터를 누적 기록한다.
"""
from __future__ import annotations
from typing import Any

from app.domain.sim_node_abc import SimNode
from app.engine.node_context import NodeContext

_MAX_HISTORY = 2000


class ScopeSimNode(SimNode):
    MAX_CHANNELS = 4

    def __init__(self) -> None:
        self._times: list[float] = []
        self._signals: dict[str, list[float]] = {
            f"ch{i}": [] for i in range(self.MAX_CHANNELS)
        }

    def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:
        self._times.append(ctx.t)
        if len(self._times) > _MAX_HISTORY:
            self._times.pop(0)
        for i in range(self.MAX_CHANNELS):
            key = f"ch{i}"
            val = float(inputs.get(key, float("nan")))
            self._signals[key].append(val)
            if len(self._signals[key]) > _MAX_HISTORY:
                self._signals[key].pop(0)
        return {}

    def get_series(self, ch: str) -> tuple[list[float], list[float]]:
        """Returns (times, values) copies for the given channel key."""
        return self._times[:], self._signals.get(ch, [])[:]

    def reset(self) -> None:
        self._times.clear()
        for v in self._signals.values():
            v.clear()
