"""
Supply Bank Node — 고정 공급 조건(압력·온도)을 출력하는 소스 노드.
입력 없음 / 출력: P_MPa, T_K, P_downstream_MPa (탱크 피드백용)

탱크 현재 압력을 하류 압력으로 매 tick 갱신해
ValveNode 가 정확한 차압으로 유량을 계산하게 한다.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from app.domain.sim_node_abc import SimNode
from app.engine.node_context import NodeContext


@dataclass
class SupplyParams:
    P_MPa: float = 87.5    # 공급 뱅크 압력 [MPa]
    T_K:   float = 233.15  # 프리쿨러 출구 온도 [K] (−40°C)


class SupplyNode(SimNode):
    def __init__(self, params: SupplyParams | None = None) -> None:
        self.params = params or SupplyParams()
        self._downstream_P: float = 5.0   # 초기 차량 탱크 압력 [MPa]

    def set_downstream_P(self, P_MPa: float) -> None:
        """메인 루프에서 탱크 현재 압력을 피드백으로 주입."""
        self._downstream_P = P_MPa

    def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:
        if ctx.logger:
            ctx.logger.log_trend(ctx.t, "supply.P_MPa", self.params.P_MPa)

        return {
            "P_MPa":              self.params.P_MPa,
            "T_K":                self.params.T_K,
            "P_downstream_MPa":   self._downstream_P,
        }

    def serialize(self) -> dict:
        return {"P_MPa": self.params.P_MPa, "T_K": self.params.T_K}

    def deserialize(self, data: dict) -> None:
        self.params = SupplyParams(**data)
