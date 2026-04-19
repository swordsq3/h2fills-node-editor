"""
Valve / Orifice Node (순수 함수 노드)
입력: P_upstream [MPa], P_downstream [MPa], open_fraction [0–1]
출력: mass_flow [kg/s]

임계 유동(choked flow) + 아음속 유동 근사.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math

from app.domain.sim_node_abc import SimNode
from app.engine.node_context import NodeContext

GAMMA_H2 = 1.405
R_H2 = 4124.0


@dataclass
class ValveParams:
    Cv: float = 0.5              # 유량계수 [무차원]
    orifice_area: float = 2e-6   # [m²] — ~0.1 kg/s @ 87 MPa/245 K 목표
    rho_ref: float = 0.0899      # kg/m³ at STP


class ValveNode(SimNode):
    def __init__(self, params: ValveParams | None = None) -> None:
        self.params = params or ValveParams()

    def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:
        P_up = float(inputs.get("P_upstream_MPa", 35.0)) * 1e6   # Pa
        P_dn = float(inputs.get("P_downstream_MPa", 1.0)) * 1e6
        T_up = float(inputs.get("T_upstream_K", 300.0))
        open_frac = float(inputs.get("open_fraction", 1.0))

        if P_up <= P_dn or open_frac <= 0:
            return {"mass_flow_kg_s": 0.0}

        g = GAMMA_H2
        P_crit = P_up * (2 / (g + 1)) ** (g / (g - 1))
        rho_up = P_up / (R_H2 * T_up)
        A = self.params.orifice_area * open_frac

        if P_dn <= P_crit:
            # 임계(choked) 유동
            mdot = A * self.params.Cv * P_up * math.sqrt(
                g / (R_H2 * T_up) * (2 / (g + 1)) ** ((g + 1) / (g - 1))
            )
        else:
            # 아음속 유동
            ratio = P_dn / P_up
            mdot = A * self.params.Cv * math.sqrt(
                2 * rho_up * P_up * (g / (g - 1)) * (ratio ** (2 / g) - ratio ** ((g + 1) / g))
            )

        if ctx.logger:
            ctx.logger.log_trend(ctx.t, "valve.mdot_kg_s", mdot)

        return {"mass_flow_kg_s": mdot}
