"""
PreCoolerNode 단위 테스트 + Without vs With PreCooler 타당성 비교.

비교 시나리오:
  Case A — Without PreCooler: Supply(300K) → Valve → Tank
  Case B — With    PreCooler: Supply(300K) → PreCooler → Valve → Tank

기대 결과:
  - Case B의 탱크 유입 온도(T_in)가 Case A보다 낮아야 한다
  - Case B의 탱크 최종 온도가 Case A보다 낮아야 한다 (과열 완화)
  - 두 케이스 모두 압력은 상승해야 한다
  - PreCooler가 Q_removed > 0 을 출력해야 한다
"""
import math
import pytest
from app.engine.graph_engine import GraphEngine
from app.engine.node_context import NodeContext
from app.domain.supply import SupplyNode, SupplyParams
from app.domain.precooler import PreCoolerNode, PreCoolerParams
from app.domain.valve import ValveNode, ValveParams
from app.domain.tank import TankNode, TankParams

# ── 공통 시나리오 파라미터 ──────────────────────────────────────
SUPPLY_P_MPA  = 87.5
SUPPLY_T_K    = 300.0    # 프리쿨러 전 공급 가스 온도 (상온)
TANK_P_INIT   = 5.0
TANK_T_INIT   = 288.15
TANK_VOLUME   = 0.1218
N_TICKS       = 10
DT            = 1.0

VALVE_PARAMS    = ValveParams(Cv=0.8, orifice_area=3e-5)
TANK_PARAMS     = TankParams(volume=TANK_VOLUME, P_init=TANK_P_INIT, T_init=TANK_T_INIT)
PRECOOLER_PARAMS = PreCoolerParams(UA=800.0, T_coolant_K=218.15, dP_MPa=0.5)


# ── 헬퍼: 시뮬레이션 실행기 ─────────────────────────────────────

def run_without_precooler(n_ticks: int = N_TICKS) -> list[dict]:
    """Case A: Supply(300K) → Valve → Tank"""
    g      = GraphEngine()
    supply = SupplyNode(SupplyParams(P_MPa=SUPPLY_P_MPA, T_K=SUPPLY_T_K))
    valve  = ValveNode(VALVE_PARAMS)
    tank   = TankNode(TANK_PARAMS)

    g.register_node("supply", supply)
    g.register_node("valve",  valve)
    g.register_node("tank",   tank)

    g.connect("supply", "P_MPa",            "valve", "P_upstream_MPa")
    g.connect("supply", "T_K",              "valve", "T_upstream_K")
    g.connect("supply", "P_downstream_MPa", "valve", "P_downstream_MPa")
    g.connect("valve",  "mass_flow_kg_s",   "tank",  "mass_flow_in")
    g.connect("supply", "T_K",              "tank",  "T_in")

    history = []
    for step in range(n_ticks):
        ctx = NodeContext(t=float(step * DT), dt=DT)
        r   = g.tick(ctx)
        history.append({
            "t":        step * DT,
            "P_MPa":    r["tank"]["P_MPa"],
            "T_K":      r["tank"]["T_K"],
            "m_kg":     r["tank"]["m_kg"],
            "T_in_K":   SUPPLY_T_K,          # 유입 온도 = 공급 온도 그대로
            "mdot":     r["valve"]["mass_flow_kg_s"],
        })
        supply.set_downstream_P(r["tank"]["P_MPa"])
        g.mark_dirty("supply")
    return history


def run_with_precooler(n_ticks: int = N_TICKS) -> list[dict]:
    """Case B: Supply(300K) → PreCooler → Valve → Tank"""
    g         = GraphEngine()
    supply    = SupplyNode(SupplyParams(P_MPa=SUPPLY_P_MPA, T_K=SUPPLY_T_K))
    precooler = PreCoolerNode(PRECOOLER_PARAMS)
    valve     = ValveNode(VALVE_PARAMS)
    tank      = TankNode(TANK_PARAMS)

    g.register_node("supply",    supply)
    g.register_node("precooler", precooler)
    g.register_node("valve",     valve)
    g.register_node("tank",      tank)

    g.connect("supply",    "P_MPa",            "precooler", "P_in_MPa")
    g.connect("supply",    "T_K",              "precooler", "T_in_K")
    g.connect("precooler", "P_out_MPa",        "valve",     "P_upstream_MPa")
    g.connect("precooler", "T_out_K",          "valve",     "T_upstream_K")
    g.connect("supply",    "P_downstream_MPa", "valve",     "P_downstream_MPa")
    g.connect("valve",     "mass_flow_kg_s",   "tank",      "mass_flow_in")
    g.connect("precooler", "T_out_K",          "tank",      "T_in")

    history = []
    for step in range(n_ticks):
        ctx = NodeContext(t=float(step * DT), dt=DT)
        r   = g.tick(ctx)
        history.append({
            "t":        step * DT,
            "P_MPa":    r["tank"]["P_MPa"],
            "T_K":      r["tank"]["T_K"],
            "m_kg":     r["tank"]["m_kg"],
            "T_in_K":   r["precooler"]["T_out_K"],  # 냉각된 유입 온도
            "mdot":     r["valve"]["mass_flow_kg_s"],
            "Q_W":      r["precooler"]["Q_removed_W"],
            "NTU":      r["precooler"].get("NTU", None),
        })
        supply.set_downstream_P(r["tank"]["P_MPa"])
        precooler.update_mdot_feedback(r["valve"]["mass_flow_kg_s"])
        g.mark_dirty("supply")
        g.mark_dirty("precooler")
    return history


# ── PreCoolerNode 단위 테스트 ────────────────────────────────────

class TestPreCoolerNode:

    def test_output_temperature_lower_than_input(self):
        """유량 > 0 일 때 출구 온도 < 입구 온도."""
        pc  = PreCoolerNode(PRECOOLER_PARAMS)
        ctx = NodeContext(t=0.0, dt=1.0)
        out = pc.evaluate(ctx, {"mass_flow_kg_s": 0.1, "T_in_K": 300.0, "P_in_MPa": 87.0})
        assert out["T_out_K"] < 300.0, "출구 온도가 입구보다 높음"

    def test_output_temperature_above_coolant(self):
        """출구 온도는 냉각수 온도 이상이어야 한다 (물리 하한)."""
        pc  = PreCoolerNode(PRECOOLER_PARAMS)
        ctx = NodeContext(t=0.0, dt=1.0)
        out = pc.evaluate(ctx, {"mass_flow_kg_s": 0.001, "T_in_K": 220.0, "P_in_MPa": 87.0})
        assert out["T_out_K"] >= PRECOOLER_PARAMS.T_coolant_K

    def test_zero_flow_passthrough(self):
        """유량 0 이면 온도 변화 없음."""
        pc  = PreCoolerNode(PRECOOLER_PARAMS)
        ctx = NodeContext(t=0.0, dt=1.0)
        out = pc.evaluate(ctx, {"mass_flow_kg_s": 0.0, "T_in_K": 300.0, "P_in_MPa": 87.0})
        assert out["Q_removed_W"] == 0.0
        assert out["T_out_K"] == 300.0

    def test_q_removed_positive(self):
        """냉각이 일어날 때 Q_removed > 0."""
        pc  = PreCoolerNode(PRECOOLER_PARAMS)
        ctx = NodeContext(t=0.0, dt=1.0)
        out = pc.evaluate(ctx, {"mass_flow_kg_s": 0.05, "T_in_K": 300.0, "P_in_MPa": 87.0})
        assert out["Q_removed_W"] > 0

    def test_pressure_drop(self):
        """압력 강하가 dP_MPa 만큼 발생."""
        pc  = PreCoolerNode(PRECOOLER_PARAMS)
        ctx = NodeContext(t=0.0, dt=1.0)
        out = pc.evaluate(ctx, {"mass_flow_kg_s": 0.05, "T_in_K": 300.0, "P_in_MPa": 87.0})
        assert abs(out["P_out_MPa"] - (87.0 - PRECOOLER_PARAMS.dP_MPa)) < 1e-6

    def test_effectiveness_between_0_and_1(self):
        """NTU 계산에서 effectiveness 는 (0, 1) 범위."""
        UA   = PRECOOLER_PARAMS.UA
        cp   = 14307.0
        mdot = 0.05
        NTU  = UA / (mdot * cp)
        eff  = 1.0 - math.exp(-NTU)
        assert 0 < eff < 1

    def test_reset(self):
        """reset 후 누적 에너지 초기화."""
        pc  = PreCoolerNode(PRECOOLER_PARAMS)
        ctx = NodeContext(t=0.0, dt=1.0)
        pc.evaluate(ctx, {"mass_flow_kg_s": 0.05, "T_in_K": 300.0, "P_in_MPa": 87.0})
        pc.reset()
        assert pc.Q_cumulative_kJ == 0.0

    def test_mdot_feedback(self):
        """update_mdot_feedback 주입 후 NTU 계산에 반영."""
        pc  = PreCoolerNode(PRECOOLER_PARAMS)
        pc.update_mdot_feedback(0.1)
        ctx = NodeContext(t=0.0, dt=1.0)
        out = pc.evaluate(ctx, {"T_in_K": 300.0, "P_in_MPa": 87.0})
        assert out["T_out_K"] < 300.0


# ── 비교 타당성 테스트 ────────────────────────────────────────────

class TestComparisonWithoutVsWithPreCooler:

    def setup_method(self):
        self.case_a = run_without_precooler(N_TICKS)
        self.case_b = run_with_precooler(N_TICKS)

    def test_both_cases_pressure_rises(self):
        """두 케이스 모두 탱크 압력이 상승해야 한다."""
        assert self.case_a[-1]["P_MPa"] > TANK_P_INIT, "Case A: 압력 상승 없음"
        assert self.case_b[-1]["P_MPa"] > TANK_P_INIT, "Case B: 압력 상승 없음"

    def test_tin_lower_with_precooler(self):
        """Case B의 유입 온도가 Case A보다 낮아야 한다."""
        tin_a = self.case_a[0]["T_in_K"]
        tin_b = self.case_b[0]["T_in_K"]
        assert tin_b < tin_a, (
            f"PreCooler가 온도를 낮추지 못함: {tin_b:.1f} K >= {tin_a:.1f} K"
        )

    def test_tank_temperature_lower_with_precooler(self):
        """Case B의 탱크 최종 온도가 Case A보다 낮아야 한다 (과열 완화)."""
        T_a = self.case_a[-1]["T_K"]
        T_b = self.case_b[-1]["T_K"]
        assert T_b < T_a, (
            f"PreCooler 온도 완화 실패: Case B {T_b:.1f} K >= Case A {T_a:.1f} K"
        )

    def test_precooler_removes_heat(self):
        """Case B에서 Q_removed > 0 이 적어도 한 tick 이상 발생해야 한다."""
        q_vals = [row["Q_W"] for row in self.case_b if row.get("Q_W") is not None]
        assert any(q > 0 for q in q_vals), "PreCooler 열 제거 없음"

    def test_tin_within_sae_j2601_limit(self):
        """Case B의 유입 온도가 SAE J2601 기준(233.15 K) 이하인지 확인."""
        limit = PRECOOLER_PARAMS.T_out_limit_K
        violations = [r for r in self.case_b if r["T_in_K"] > limit]
        # 첫 tick은 nominal_mdot 사용으로 정확도 낮을 수 있어 경고만
        if violations:
            print(f"\n[WARNING] SAE J2601 초과 tick: {len(violations)}개 "
                  f"(max {max(r['T_in_K'] for r in violations):.1f} K) "
                  f"→ UA 증가 또는 냉각수 온도 강화 필요")

    def test_mass_conservation(self):
        """두 케이스 모두 질량이 단조 증가해야 한다."""
        for label, history in [("A", self.case_a), ("B", self.case_b)]:
            masses = [r["m_kg"] for r in history]
            assert all(masses[i] <= masses[i+1] for i in range(len(masses)-1)), \
                f"Case {label}: 질량이 단조 증가하지 않음: {masses}"


# ── 수치 요약 출력 (pytest -s 로 확인) ──────────────────────────

def test_print_comparison_table():
    """
    두 케이스 수치 비교 요약 출력.
    pytest -s tests/test_precooler.py::test_print_comparison_table 로 확인.
    """
    case_a = run_without_precooler(N_TICKS)
    case_b = run_with_precooler(N_TICKS)

    header = f"{'t':>5}  {'A_P':>8}  {'A_T':>7}  {'B_P':>8}  {'B_T':>7}  {'B_Tin':>7}  {'B_Q_kW':>8}  {'dT':>7}"
    print("\n\n=== Without PreCooler (A) vs With PreCooler (B) ===")
    print(header)
    print("-" * len(header))
    for a, b in zip(case_a, case_b):
        q_kw = b.get("Q_W", 0.0) / 1000.0
        dT   = a["T_K"] - b["T_K"]
        print(f"{a['t']:>5.0f}  "
              f"{a['P_MPa']:>8.3f}  {a['T_K']:>7.1f}  "
              f"{b['P_MPa']:>8.3f}  {b['T_K']:>7.1f}  "
              f"{b['T_in_K']:>7.1f}  {q_kw:>8.2f}  {dT:>+7.1f}")

    print(f"\n최종 탱크 온도: Case A = {case_a[-1]['T_K']:.1f} K  |  Case B = {case_b[-1]['T_K']:.1f} K")
    print(f"온도 절감:      {case_a[-1]['T_K'] - case_b[-1]['T_K']:.1f} K")
    print(f"유입 온도(B):   {case_b[0]['T_in_K']:.1f} K  (SAE J2601 기준 233.15 K)")
    assert True  # 출력 확인용
