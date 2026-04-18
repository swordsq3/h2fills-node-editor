"""
Pre-Cooler Node — Effectiveness-NTU 열교환기 모델.

수소 충전 시 공급 가스를 냉각하여 차량 탱크의 과열을 방지한다.
SAE J2601 기준: 공급 가스 온도 ≤ −40°C (233.15 K)

물리 모델 (단일 패스 향류 열교환기, 이상기체 가정):
  NTU         = UA / (mdot * cp_H2)
  effectiveness = 1 - exp(-NTU)          [냉각수 유량 >> 수소 유량 가정]
  T_out       = T_in - ε * (T_in - T_coolant)
  Q_removed   = mdot * cp_H2 * (T_in - T_out)   [W]
  P_out       = P_in - dP                [압력 강하 선형 근사]

포트:
  입력: mass_flow_kg_s, T_in_K, P_in_MPa
  출력: T_out_K, P_out_MPa, Q_removed_W, mass_flow_kg_s (pass-through)
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any

from app.domain.sim_node_abc import SimNode
from app.engine.node_context import NodeContext
from app.engine.event_bus import EventLevel

CP_H2   = 14_307.0   # J/(kg·K), 수소 정압비열 (300 K 기준)


@dataclass
class PreCoolerParams:
    UA: float          = 800.0   # 열전달 계수 × 면적 [W/K]  — 실험 교정 필요
    T_coolant_K: float = 218.15  # 냉각수 온도 [K]  (−55°C, 여유분 포함)
    dP_MPa: float      = 0.5     # 배관 압력 강하 [MPa]
    T_out_limit_K: float = 233.15  # 출구 온도 상한 알람 기준 [K] (SAE J2601)
    nominal_mdot: float = 0.05   # valve 피드백 없을 때 NTU 계산용 기본 유량 [kg/s]


class PreCoolerNode(SimNode):
    """
    상태 보유 없음 — 순수 함수에 가까운 노드.
    단, Q_cumulative 로 누적 냉각 에너지를 추적한다.
    """

    def __init__(self, params: PreCoolerParams | None = None) -> None:
        self.params = params or PreCoolerParams()
        self._Q_cumulative_J: float = 0.0
        self._last_mdot: float = 0.0   # 이전 tick valve 유량 (1-tick 지연 피드백)

    def reset(self) -> None:
        self._Q_cumulative_J = 0.0
        self._last_mdot = 0.0

    def update_mdot_feedback(self, mdot: float) -> None:
        """메인루프에서 이전 tick의 valve 출력 유량을 주입."""
        self._last_mdot = mdot

    def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:
        # mass_flow_kg_s: 연결된 포트 → 없으면 이전 tick 캐시 → 없으면 nominal
        raw = inputs.get("mass_flow_kg_s")
        if raw is not None:
            mdot = float(raw)
        elif self._last_mdot > 0:
            mdot = self._last_mdot
        else:
            mdot = self.params.nominal_mdot
        T_in  = float(inputs.get("T_in_K",  300.0))
        P_in  = float(inputs.get("P_in_MPa", 35.0))

        p = self.params

        if mdot <= 0.0:
            # 유량 없음 — 출력은 입력 그대로 pass-through
            return {
                "T_out_K":        T_in,
                "P_out_MPa":      max(P_in - p.dP_MPa, 0.0),
                "Q_removed_W":    0.0,
                "mass_flow_kg_s": 0.0,
            }

        # Effectiveness-NTU
        NTU          = p.UA / (mdot * CP_H2)
        effectiveness = 1.0 - math.exp(-NTU)

        T_out = T_in - effectiveness * (T_in - p.T_coolant_K)
        T_out = max(T_out, p.T_coolant_K)   # 냉각수 온도 이하로는 내려가지 않음

        Q_removed = mdot * CP_H2 * (T_in - T_out)   # [W]
        self._Q_cumulative_J += Q_removed * ctx.dt

        P_out = max(P_in - p.dP_MPa, 0.1)

        # SAE J2601 출구 온도 초과 알람
        if T_out > p.T_out_limit_K and ctx.logger:
            ctx.logger.emit(
                ctx.t, EventLevel.WARNING, "PreCoolerNode",
                f"출구 온도 초과: {T_out:.1f} K > {p.T_out_limit_K:.1f} K (SAE J2601 위반)"
            )

        if ctx.logger:
            ctx.logger.log_trend(ctx.t, "precooler.T_in_K",     T_in)
            ctx.logger.log_trend(ctx.t, "precooler.T_out_K",    T_out)
            ctx.logger.log_trend(ctx.t, "precooler.Q_removed_W", Q_removed)
            ctx.logger.log_trend(ctx.t, "precooler.NTU",         NTU)
            ctx.logger.log_trend(ctx.t, "precooler.effectiveness", effectiveness)

        return {
            "T_out_K":        T_out,
            "P_out_MPa":      P_out,
            "Q_removed_W":    Q_removed,
            "mass_flow_kg_s": mdot,   # 질량 보존
        }

    @property
    def Q_cumulative_kJ(self) -> float:
        return self._Q_cumulative_J / 1000.0

    def serialize(self) -> dict:
        return {
            "UA":            self.params.UA,
            "T_coolant_K":   self.params.T_coolant_K,
            "dP_MPa":        self.params.dP_MPa,
            "T_out_limit_K": self.params.T_out_limit_K,
        }

    def deserialize(self, data: dict) -> None:
        self.params = PreCoolerParams(**data)
        self.reset()
