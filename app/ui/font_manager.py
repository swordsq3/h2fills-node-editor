"""
Font Manager — DearPyGui 한국어 폰트 등록.
create_context() 이후, setup_dearpygui() 이전에 setup_fonts()를 호출해야 한다.
"""
from __future__ import annotations
import os
import dearpygui.dearpygui as dpg

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "res", "fonts")

# DearPyGui C++ 레이어는 한글 경로를 지원하지 않으므로, 폰트는 ASCII 경로에서 로드한다.
_ASCII_FONT_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "h2sim", "fonts")

_CANDIDATES = [
    ("NanumGothicCoding-Regular.ttf", 16),
    ("MalgunGothic-Regular.ttf",      16),
]

_default_font = None


def setup_fonts() -> None:
    """폰트 레지스트리 등록 및 전역 기본 폰트 바인딩."""
    global _default_font
    font_path, size = _resolve_font()
    if font_path is None:
        return

    with dpg.font_registry():
        with dpg.font(font_path, size) as f:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Korean)
        _default_font = f

    dpg.bind_font(_default_font)


def _resolve_font() -> tuple[str | None, int]:
    search_dirs = [_ASCII_FONT_DIR, _FONT_DIR]
    for fname, size in _CANDIDATES:
        for d in search_dirs:
            path = os.path.normpath(os.path.join(d, fname))
            # ASCII 경로만 허용 (DearPyGui C++ 레이어 제약)
            try:
                path.encode("ascii")
            except UnicodeEncodeError:
                continue
            if os.path.isfile(path):
                return path, size
    # 시스템 폰트 폴백 (ASCII 경로)
    system_fallback = r"C:\Windows\Fonts\malgun.ttf"
    if os.path.isfile(system_fallback):
        return system_fallback, 16
    return None, 16
