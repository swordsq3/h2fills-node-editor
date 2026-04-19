"""
Tank Lumped Model (집중 매개변수 모델)
상태: 압력 P [MPa], 온도 T [K], 질량 m [kg]
입력: mass_flow_in [kg/s]
출력: P, T, m, SOC (State of Charge)

단순화된 이상기체 근사 (초기 MVP).
추후 REFPROP/CoolProp 어댑터로 교체 가능.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from app.domain.sim_node_abc import SimNode
from app.engine.node_context import NodeContext
from app.engine.event_bus import EventLevel

R_H2 = 4124.0    # J/(kg·K), 수소 기체 상수


@dataclass
class TankParams:
    volume: float = 0.1218       # [m³] — 700bar 타입 IV, ~5 kg
    T_init: float = 288.15       # [K]
    P_init: float = 5.0          # [MPa]
    P_max: float = 87.5          # [MPa] — 안전 상한
    cv: float = 10_183.0         # J/(kg·K), 수소 정적비열


class TankNode(SimNode):
    def __init__(self, params: TankParams | None = None) -> None:
        self.params = params or TankParams()
        self._P = self.params.P_init
        self._T = self.params.T_init
        self._m = self._init_mass()

    def _init_mass(self) -> float:
        p = self.params
        return (p.P_init * 1e6) * p.volume / (R_H2 * p.T_init)

    def reset(self) -> None:
        self._P = self.params.P_init
        self._T = self.params.T_init
        self._m = self._init_mass()

    def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:
        mdot_in = float(inputs.get("mass_flow_in", 0.0))
        T_in = float(inputs.get("T_in", ctx.scenario.get("T_supply", 233.15)))  # [K] 프리쿨러 출구 온도

        dt = ctx.dt
        p = self.params

        dm = mdot_in * dt
        m_old = self._m          # 에너지 방정식에 사용할 이전 질량 저장
        self._m += dm

        if dm > 0 and self._m > 0:
            # 에너지 보존: U_old + h_in*dm = U_new (강체 탱크, 일 항 없음)
            # U = m*cv*T, h_in = (cv+R)*T_in (이상기체 엔탈피)
            h_in = (p.cv + R_H2) * T_in
            U = p.cv * m_old * self._T + h_in * dm
            self._T = U / (p.cv * self._m)

        self._P = (self._m * R_H2 * self._T) / (p.volume * 1e6)

        # 안전 모니터
        if self._P >= p.P_max and ctx.logger:
            ctx.logger.emit(ctx.t, EventLevel.ALARM, "TankNode", f"압력 한계 초과: {self._P:.2f} MPa")

        soc = self._P / p.P_max

        if ctx.logger:
            ctx.logger.log_trend(ctx.t, "tank.P_MPa", self._P)
            ctx.logger.log_trend(ctx.t, "tank.T_K", self._T)
            ctx.logger.log_trend(ctx.t, "tank.m_kg", self._m)
            ctx.logger.log_trend(ctx.t, "tank.SOC", soc)

        return {"P_MPa": self._P, "T_K": self._T, "m_kg": self._m, "SOC": soc}

    def serialize(self) -> dict:
        return {
            "volume": self.params.volume,
            "T_init": self.params.T_init,
            "P_init": self.params.P_init,
            "P_max": self.params.P_max,
            "cv": self.params.cv,
        }

    def deserialize(self, data: dict) -> None:
        self.params = TankParams(**data)
        self.reset()
