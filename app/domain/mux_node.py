"""
MuxSimNode — 최대 4개 스칼라 신호를 하나의 버스로 묶어 출력.
입력: in0..in3  →  출력: ch0..ch3 (그대로 전달)
"""
from __future__ import annotations
from typing import Any

from app.domain.sim_node_abc import SimNode
from app.engine.node_context import NodeContext


class MuxSimNode(SimNode):
    NUM_CHANNELS = 4

    def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:
        return {
            f"ch{i}": float(inputs.get(f"in{i}", float("nan")))
            for i in range(self.NUM_CHANNELS)
        }
