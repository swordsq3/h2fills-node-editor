"""
link_styler.py — 포트 타입별 링크 색상 테마.
압력=파랑, 온도=빨강, 유량=녹색, 상태=회색, 버스=보라(두껍게)
"""
from __future__ import annotations
import dearpygui.dearpygui as dpg

# 포트 이름 키워드 → RGBA 색상 (우선순위 순서)
_PORT_COLORS: list[tuple[str, tuple]] = [
    ("mass_flow", (40,  180,  60, 230)),   # 질량유량 → 녹색
    ("mdot",      (40,  180,  60, 230)),
    ("Q_removed", (200,  80,  20, 220)),   # 열 → 주황
    ("SOC",       (120, 120, 140, 200)),   # 상태 → 회색
    ("m_kg",      (120, 120, 140, 200)),
    ("P_down",    (60,  140, 220, 230)),   # 배압 → 연파랑
    ("P",         (30,  100, 220, 230)),   # 압력 → 파랑
    ("T",         (200,  50,  40, 230)),   # 온도 → 빨강
    ("ch",        (130,  60, 180, 210)),   # Scope 채널 → 보라
    ("in",        (130,  60, 180, 210)),   # MUX 입력
]

_DEFAULT_COLOR = (70, 70, 90, 210)
_BUS_THICKNESS = 3.5
_STD_THICKNESS = 2.0

_cache: dict[tuple, str] = {}


def get_link_color(src_port: str) -> tuple:
    for key, color in _PORT_COLORS:
        if key in src_port:
            return color
    return _DEFAULT_COLOR


def _make_link_theme(color: tuple, thickness: float) -> str:
    r, g, b, a = color
    tag = f"_lt_{r}_{g}_{b}_{int(thickness * 10)}"
    if not dpg.does_item_exist(tag):
        with dpg.theme(tag=tag):
            with dpg.theme_component(dpg.mvNodeLink):
                dpg.add_theme_color(dpg.mvNodeCol_Link,
                                    (r, g, b, a),
                                    category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_LinkHovered,
                                    (min(r+50,255), min(g+50,255), min(b+50,255), 255),
                                    category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_LinkSelected,
                                    (min(r+70,255), min(g+70,255), min(b+70,255), 255),
                                    category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_style(dpg.mvNodeStyleVar_LinkThickness,
                                    thickness, category=dpg.mvThemeCat_Nodes)
    return tag


def apply_link_theme(link_id: int, src_port: str) -> None:
    """link_id에 포트 타입별 색상 테마 적용."""
    is_bus = src_port.startswith("ch")
    color  = get_link_color(src_port)
    thickness = _BUS_THICKNESS if is_bus else _STD_THICKNESS
    key = (color, thickness)
    if key not in _cache:
        _cache[key] = _make_link_theme(color, thickness)
    try:
        dpg.bind_item_theme(link_id, _cache[key])
    except Exception:
        pass
