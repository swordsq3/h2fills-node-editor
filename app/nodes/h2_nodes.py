"""
H2FillS DearPyGui 노드 위젯 정의.
각 클래스는 DPG node_editor 내부에 노드를 그리고,
해당하는 도메인 SimNode 인스턴스를 소유한다.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import dearpygui.dearpygui as dpg

from app.domain.supply    import SupplyNode, SupplyParams
from app.domain.precooler import PreCoolerNode, PreCoolerParams
from app.domain.valve     import ValveNode, ValveParams
from app.domain.tank      import TankNode, TankParams
from app.domain.scope_node import ScopeSimNode
from app.domain.mux_node   import MuxSimNode


# ── 포트 메타데이터 ─────────────────────────────────────────────

@dataclass
class PortMeta:
    name: str
    label: str
    kind: str   # "in" | "out"


# ── 베이스 노드 ────────────────────────────────────────────────

class H2DpgNode:
    NODE_TYPE: str = "base"
    LABEL:     str = "Node"
    COLOR:     tuple = (100, 100, 100, 255)
    INPUTS:    list[PortMeta] = []
    OUTPUTS:   list[PortMeta] = []

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.dpg_tag = f"dpg_node_{node_id}"

    # 포트 태그 규칙: dpg_{node_id}_{in|out}_{port_name}
    def in_tag(self,  port: str) -> str: return f"dpg_{self.node_id}_in_{port}"
    def out_tag(self, port: str) -> str: return f"dpg_{self.node_id}_out_{port}"

    def _attr_type(self, kind: str):
        return (dpg.mvNode_Attr_Input  if kind == "in"
                else dpg.mvNode_Attr_Output)

    def build(self, editor_tag: str, pos: tuple[int, int] = (120, 120)) -> None:
        with dpg.node(tag=self.dpg_tag, label=self.LABEL,
                      pos=list(pos), parent=editor_tag):
            dpg.bind_item_theme(self.dpg_tag, self._get_or_create_theme())
            self._build_params()
            for p in self.INPUTS:
                with dpg.node_attribute(tag=self.in_tag(p.name),
                                        attribute_type=dpg.mvNode_Attr_Input):
                    dpg.add_text(p.label, indent=4, color=(40, 40, 40, 255))
            for p in self.OUTPUTS:
                with dpg.node_attribute(tag=self.out_tag(p.name),
                                        attribute_type=dpg.mvNode_Attr_Output):
                    dpg.add_text(p.label, indent=4, color=(40, 40, 40, 255))

    def _build_params(self) -> None:
        pass   # 서브클래스에서 오버라이드

    def _get_or_create_theme(self) -> int | str:
        theme_tag = f"theme_node_{self.NODE_TYPE}"
        if dpg.does_item_exist(theme_tag):
            return theme_tag
        r, g, b, a = self.COLOR
        with dpg.theme(tag=theme_tag):
            with dpg.theme_component(dpg.mvNode):
                # 타이틀바: 채도 있는 블록 색상 (Simulink 스타일)
                dpg.add_theme_color(dpg.mvNodeCol_TitleBar,
                                    (r, g, b, 230), category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_TitleBarHovered,
                                    (min(r+30,255), min(g+30,255), min(b+30,255), 230),
                                    category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_TitleBarSelected,
                                    (min(r+50,255), min(g+50,255), min(b+50,255), 255),
                                    category=dpg.mvThemeCat_Nodes)
                # 바디: 흰색 (Simulink 블록 내부)
                dpg.add_theme_color(dpg.mvNodeCol_NodeBackground,
                                    (252, 252, 252, 250), category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundHovered,
                                    (240, 245, 255, 255), category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundSelected,
                                    (225, 235, 255, 255), category=dpg.mvThemeCat_Nodes)
                # 테두리: 어두운 (Simulink 블록 윤곽선)
                dpg.add_theme_color(dpg.mvNodeCol_NodeOutline,
                                    (50, 50, 70, 240), category=dpg.mvThemeCat_Nodes)
        return theme_tag

    def get_domain_node(self): raise NotImplementedError
    def get_pos(self) -> list[int]: return dpg.get_item_pos(self.dpg_tag)

    def to_json(self) -> dict:
        return {"type": self.NODE_TYPE, "id": self.node_id, "pos": self.get_pos(), "params": {}}

    def from_json(self, data: dict) -> None:
        pass

    def close(self) -> None:
        if dpg.does_item_exist(self.dpg_tag):
            dpg.delete_item(self.dpg_tag)


# ── Supply 노드 ────────────────────────────────────────────────

class SupplyDpgNode(H2DpgNode):
    NODE_TYPE = "supply"
    LABEL     = "공급 뱅크"
    COLOR     = (60, 110, 200, 255)
    INPUTS    = []
    OUTPUTS   = [
        PortMeta("P_MPa",             "P [MPa]",            "out"),
        PortMeta("T_K",               "T [K]",              "out"),
        PortMeta("P_downstream_MPa",  "P_downstream [MPa]", "out"),
    ]

    def _build_params(self) -> None:
        with dpg.node_attribute(tag=f"{self.node_id}_static",
                                attribute_type=dpg.mvNode_Attr_Static):
            dpg.add_input_float(label="P_supply [MPa]",
                                tag=f"{self.node_id}_P_MPa",
                                default_value=87.5, width=130, step=0)
            dpg.add_input_float(label="T_supply [K]",
                                tag=f"{self.node_id}_T_K",
                                default_value=300.0, width=130, step=0)

    def get_domain_node(self) -> SupplyNode:
        P = dpg.get_value(f"{self.node_id}_P_MPa")
        T = dpg.get_value(f"{self.node_id}_T_K")
        return SupplyNode(SupplyParams(P_MPa=P, T_K=T))

    def to_json(self) -> dict:
        return {**super().to_json(), "params": {
            "P_MPa": dpg.get_value(f"{self.node_id}_P_MPa"),
            "T_K":   dpg.get_value(f"{self.node_id}_T_K"),
        }}

    def from_json(self, data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = f"{self.node_id}_{k}"
            if dpg.does_item_exist(tag): dpg.set_value(tag, v)


# ── PreCooler 노드 ─────────────────────────────────────────────

class PreCoolerDpgNode(H2DpgNode):
    NODE_TYPE = "precooler"
    LABEL     = "프리쿨러"
    COLOR     = (30, 155, 180, 255)
    INPUTS    = [
        PortMeta("P_in_MPa", "P_in [MPa]", "in"),
        PortMeta("T_in_K",   "T_in [K]",   "in"),
    ]
    OUTPUTS   = [
        PortMeta("P_out_MPa",      "P_out [MPa]",    "out"),
        PortMeta("T_out_K",        "T_out [K]",      "out"),
        PortMeta("mass_flow_kg_s", "mdot [kg/s]",    "out"),
        PortMeta("Q_removed_W",    "Q_removed [W]",  "out"),
    ]

    def _build_params(self) -> None:
        with dpg.node_attribute(tag=f"{self.node_id}_static",
                                attribute_type=dpg.mvNode_Attr_Static):
            dpg.add_input_float(label="UA [W/K]",
                                tag=f"{self.node_id}_UA",
                                default_value=800.0, width=130, step=0)
            dpg.add_input_float(label="T_coolant [K]",
                                tag=f"{self.node_id}_T_coolant_K",
                                default_value=218.15, width=130, step=0)
            dpg.add_input_float(label="dP [MPa]",
                                tag=f"{self.node_id}_dP_MPa",
                                default_value=0.5, width=130, step=0)

    def get_domain_node(self) -> PreCoolerNode:
        return PreCoolerNode(PreCoolerParams(
            UA=dpg.get_value(f"{self.node_id}_UA"),
            T_coolant_K=dpg.get_value(f"{self.node_id}_T_coolant_K"),
            dP_MPa=dpg.get_value(f"{self.node_id}_dP_MPa"),
        ))

    def to_json(self) -> dict:
        return {**super().to_json(), "params": {
            "UA":          dpg.get_value(f"{self.node_id}_UA"),
            "T_coolant_K": dpg.get_value(f"{self.node_id}_T_coolant_K"),
            "dP_MPa":      dpg.get_value(f"{self.node_id}_dP_MPa"),
        }}

    def from_json(self, data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = f"{self.node_id}_{k}"
            if dpg.does_item_exist(tag): dpg.set_value(tag, v)


# ── Valve 노드 ────────────────────────────────────────────────

class ValveDpgNode(H2DpgNode):
    NODE_TYPE = "valve"
    LABEL     = "밸브"
    COLOR     = (50, 170, 80, 255)
    INPUTS    = [
        PortMeta("P_upstream_MPa",   "P_up [MPa]",   "in"),
        PortMeta("T_upstream_K",     "T_up [K]",     "in"),
        PortMeta("P_downstream_MPa", "P_down [MPa]", "in"),
    ]
    OUTPUTS   = [
        PortMeta("mass_flow_kg_s", "mdot [kg/s]", "out"),
    ]

    def _build_params(self) -> None:
        with dpg.node_attribute(tag=f"{self.node_id}_static",
                                attribute_type=dpg.mvNode_Attr_Static):
            dpg.add_input_float(label="Cv",
                                tag=f"{self.node_id}_Cv",
                                default_value=0.8, width=130, step=0)
            dpg.add_input_float(label="Orifice [m²]",
                                tag=f"{self.node_id}_orifice_area",
                                default_value=2e-6, width=130,
                                format="%.2e", step=0)

    def get_domain_node(self) -> ValveNode:
        return ValveNode(ValveParams(
            Cv=dpg.get_value(f"{self.node_id}_Cv"),
            orifice_area=dpg.get_value(f"{self.node_id}_orifice_area"),
        ))

    def to_json(self) -> dict:
        return {**super().to_json(), "params": {
            "Cv":           dpg.get_value(f"{self.node_id}_Cv"),
            "orifice_area": dpg.get_value(f"{self.node_id}_orifice_area"),
        }}

    def from_json(self, data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = f"{self.node_id}_{k}"
            if dpg.does_item_exist(tag): dpg.set_value(tag, v)


# ── Tank 노드 ─────────────────────────────────────────────────

class TankDpgNode(H2DpgNode):
    NODE_TYPE = "tank"
    LABEL     = "수소 탱크"
    COLOR     = (200, 110, 30, 255)
    INPUTS    = [
        PortMeta("mass_flow_in", "mdot_in [kg/s]", "in"),
        PortMeta("T_in",         "T_in [K]",       "in"),
    ]
    OUTPUTS   = [
        PortMeta("P_MPa", "P [MPa]", "out"),
        PortMeta("T_K",   "T [K]",   "out"),
        PortMeta("m_kg",  "m [kg]",  "out"),
        PortMeta("SOC",   "SOC",     "out"),
    ]

    def _build_params(self) -> None:
        with dpg.node_attribute(tag=f"{self.node_id}_static",
                                attribute_type=dpg.mvNode_Attr_Static):
            dpg.add_input_float(label="V [m³]",
                                tag=f"{self.node_id}_volume",
                                default_value=0.1218, width=130, step=0)
            dpg.add_input_float(label="P_init [MPa]",
                                tag=f"{self.node_id}_P_init",
                                default_value=5.0, width=130, step=0)
            dpg.add_input_float(label="T_init [K]",
                                tag=f"{self.node_id}_T_init",
                                default_value=288.15, width=130, step=0)
            dpg.add_text("", tag=f"{self.node_id}_status")

    def get_domain_node(self) -> TankNode:
        return TankNode(TankParams(
            volume=dpg.get_value(f"{self.node_id}_volume"),
            P_init=dpg.get_value(f"{self.node_id}_P_init"),
            T_init=dpg.get_value(f"{self.node_id}_T_init"),
        ))

    def update_status(self, P: float, T: float, soc: float) -> None:
        tag = f"{self.node_id}_status"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, f"P={P:.1f}MPa  SOC={soc*100:.0f}%")

    def to_json(self) -> dict:
        return {**super().to_json(), "params": {
            "volume": dpg.get_value(f"{self.node_id}_volume"),
            "P_init": dpg.get_value(f"{self.node_id}_P_init"),
            "T_init": dpg.get_value(f"{self.node_id}_T_init"),
        }}

    def from_json(self, data: dict) -> None:
        for k, v in data.get("params", {}).items():
            tag = f"{self.node_id}_{k}"
            if dpg.does_item_exist(tag): dpg.set_value(tag, v)


# ── Scope 노드 ────────────────────────────────────────────────

class ScopeDpgNode(H2DpgNode):
    NODE_TYPE = "scope"
    LABEL     = "스코프"
    COLOR     = (80, 80, 160, 255)
    INPUTS    = [
        PortMeta("ch0", "Ch0", "in"),
        PortMeta("ch1", "Ch1", "in"),
        PortMeta("ch2", "Ch2", "in"),
        PortMeta("ch3", "Ch3", "in"),
    ]
    OUTPUTS = []

    _SERIES_COLORS = [
        (80,  220, 120, 255),
        (220, 120,  80, 255),
        (80,  160, 220, 255),
        (220, 220,  80, 255),
    ]

    def __init__(self, node_id: str) -> None:
        super().__init__(node_id)
        self._domain = ScopeSimNode()

    def _build_params(self) -> None:
        with dpg.node_attribute(
                tag=f"{self.node_id}_plot_attr",
                attribute_type=dpg.mvNode_Attr_Static):
            with dpg.plot(tag=f"{self.node_id}_plot",
                          height=150, width=260,
                          no_menus=True, no_box_select=True,
                          no_mouse_pos=True):
                dpg.add_plot_legend(location=dpg.mvPlot_Location_NorthEast,
                                    outside=False)
                dpg.add_plot_axis(dpg.mvXAxis,
                                  label="t [s]",
                                  tag=f"{self.node_id}_xax")
                dpg.add_plot_axis(dpg.mvYAxis,
                                  label="",
                                  tag=f"{self.node_id}_yax")
                for i in range(4):
                    dpg.add_line_series(
                        [], [],
                        label=f"ch{i}",
                        tag=f"{self.node_id}_s{i}",
                        parent=f"{self.node_id}_yax",
                    )

    def get_domain_node(self) -> ScopeSimNode:
        return self._domain

    def update_plot(self, domain: ScopeSimNode) -> None:
        for i in range(4):
            tag = f"{self.node_id}_s{i}"
            if not dpg.does_item_exist(tag):
                continue
            times, vals = domain.get_series(f"ch{i}")
            pairs = [(t, v) for t, v in zip(times, vals) if v == v]
            if pairs:
                ts, vs = zip(*pairs)
                dpg.set_value(tag, [list(ts), list(vs)])
            else:
                dpg.set_value(tag, [[], []])
        try:
            dpg.fit_axis_data(f"{self.node_id}_xax")
            dpg.fit_axis_data(f"{self.node_id}_yax")
        except Exception:
            pass

    def to_json(self) -> dict:
        return {**super().to_json(), "params": {}}

    def from_json(self, data: dict) -> None:
        pass


# ── Mux 노드 ─────────────────────────────────────────────────

class MuxDpgNode(H2DpgNode):
    NODE_TYPE = "mux"
    LABEL     = "MUX"
    COLOR     = (120, 60, 180, 255)
    INPUTS    = [
        PortMeta("in0", "in0 [P]",   "in"),
        PortMeta("in1", "in1 [T]",   "in"),
        PortMeta("in2", "in2 [mdot]","in"),
        PortMeta("in3", "in3 [SOC]", "in"),
    ]
    OUTPUTS   = [
        PortMeta("ch0", "ch0", "out"),
        PortMeta("ch1", "ch1", "out"),
        PortMeta("ch2", "ch2", "out"),
        PortMeta("ch3", "ch3", "out"),
    ]

    def _build_params(self) -> None:
        with dpg.node_attribute(tag=f"{self.node_id}_static",
                                attribute_type=dpg.mvNode_Attr_Static):
            dpg.add_text("[4x1] 버스", color=(120, 60, 180, 255))
            dpg.add_separator()

    def get_domain_node(self) -> MuxSimNode:
        return MuxSimNode()

    def to_json(self) -> dict:
        return {**super().to_json(), "params": {}}

    def from_json(self, data: dict) -> None:
        pass


# ── 팩토리 ────────────────────────────────────────────────────

NODE_CLASSES: dict[str, type[H2DpgNode]] = {
    "supply":    SupplyDpgNode,
    "precooler": PreCoolerDpgNode,
    "valve":     ValveDpgNode,
    "tank":      TankDpgNode,
    "mux":       MuxDpgNode,
    "scope":     ScopeDpgNode,
}

PALETTE: list[dict] = [
    {"type": "supply",    "label": "공급 뱅크",  "icon": "supply"},
    {"type": "precooler", "label": "프리쿨러",   "icon": "precooler"},
    {"type": "valve",     "label": "밸브",        "icon": "valve"},
    {"type": "tank",      "label": "수소 탱크",   "icon": "tank"},
    {"type": "mux",       "label": "MUX",         "icon": "mux"},
    {"type": "scope",     "label": "스코프",      "icon": "scope"},
]
