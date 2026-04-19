"""
Icon Loader — res/icons/ SVG 기반 PIL 렌더링 → DearPyGui 텍스처 등록.
DearPyGui는 SVG 직접 로드 불가이므로, Pillow로 래스터화 후 float-RGBA 텍스처로 등록.
"""
from __future__ import annotations
import os
import dearpygui.dearpygui as dpg
from PIL import Image, ImageDraw

SIZE = 48

# ── 컴포넌트별 아이콘 생성 함수 ─────────────────────────────────

def _supply(sz: int) -> Image.Image:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 실린더 몸체
    d.rounded_rectangle([sz*0.22, sz*0.25, sz*0.78, sz*0.90], radius=sz*0.1,
                         fill=(70, 130, 220, 240), outline=(140, 190, 255, 255), width=2)
    # 노즐
    d.rectangle([int(sz*0.38), int(sz*0.08), int(sz*0.62), int(sz*0.27)],
                fill=(100, 160, 235, 240))
    d.ellipse([int(sz*0.34), int(sz*0.04), int(sz*0.66), int(sz*0.16)],
              fill=(130, 180, 245, 255))
    # 밸브 손잡이
    d.line([int(sz*0.28), int(sz*0.10), int(sz*0.72), int(sz*0.10)],
           fill=(180, 210, 255, 255), width=3)
    return img


def _precooler(sz: int) -> Image.Image:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 배경 박스
    d.rounded_rectangle([sz*0.08, sz*0.15, sz*0.92, sz*0.85], radius=sz*0.08,
                         fill=(30, 160, 190, 200), outline=(100, 220, 240, 255), width=2)
    # 냉각 핀 (수평선)
    for i in range(4):
        y = int(sz * (0.25 + i * 0.15))
        d.line([int(sz*0.18), y, int(sz*0.82), y],
               fill=(180, 240, 255, 230), width=2)
    # 눈꽃 모양 (간략)
    cx, cy = sz // 2, sz // 2
    d.line([cx - sz//8, cy, cx + sz//8, cy], fill=(255, 255, 255, 220), width=3)
    d.line([cx, cy - sz//8, cx, cy + sz//8], fill=(255, 255, 255, 220), width=3)
    return img


def _valve(sz: int) -> Image.Image:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = sz // 2, sz // 2
    # 배관 (좌우)
    d.rectangle([0, cy - sz//8, sz, cy + sz//8], fill=(80, 180, 100, 200))
    # 나비 밸브 디스크 (두 삼각형)
    d.polygon([cx, cy - sz//3,  cx - sz//4, cy + sz//3,  cx + sz//4, cy + sz//3],
              fill=(50, 200, 80, 240))
    d.polygon([cx, cy + sz//3,  cx - sz//4, cy - sz//3,  cx + sz//4, cy - sz//3],
              fill=(50, 200, 80, 240))
    # 중앙 핀
    d.ellipse([cx - sz//10, cy - sz//10, cx + sz//10, cy + sz//10],
              fill=(200, 255, 200, 255))
    # 외곽선
    d.ellipse([sz*0.12, sz*0.12, sz*0.88, sz*0.88],
              outline=(130, 230, 150, 255), width=2)
    return img


def _tank(sz: int) -> Image.Image:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 탱크 몸체 (가로 캡슐)
    d.rounded_rectangle([sz*0.08, sz*0.28, sz*0.92, sz*0.72], radius=sz*0.22,
                         fill=(210, 120, 40, 230), outline=(255, 180, 90, 255), width=2)
    # SOC 표시 바 (내부)
    d.rounded_rectangle([sz*0.16, sz*0.38, sz*0.68, sz*0.62], radius=sz*0.05,
                         fill=(255, 200, 80, 220))
    # 포트 노브
    d.rectangle([int(sz*0.88), int(sz*0.40), int(sz*0.96), int(sz*0.60)],
                fill=(240, 150, 60, 255))
    return img


def _mux(sz: int) -> Image.Image:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([sz*0.08, sz*0.08, sz*0.92, sz*0.92], radius=sz*0.1,
                         fill=(100, 50, 160, 210), outline=(180, 120, 240, 255), width=2)
    # 왼쪽 4개 입력선
    for i in range(4):
        y = int(sz * (0.22 + i * 0.19))
        d.line([int(sz*0.08), y, int(sz*0.42), y], fill=(160, 120, 220, 200), width=2)
        d.ellipse([int(sz*0.38), y - 3, int(sz*0.46), y + 3], fill=(200, 160, 255, 255))
    # 오른쪽 4개 출력선
    for i in range(4):
        y = int(sz * (0.22 + i * 0.19))
        d.line([int(sz*0.58), y, int(sz*0.92), y], fill=(220, 180, 255, 200), width=2)
    # 중앙 MUX 박스
    d.rectangle([int(sz*0.42), int(sz*0.12), int(sz*0.58), int(sz*0.88)],
                fill=(140, 80, 200, 240))
    return img


def _scope(sz: int) -> Image.Image:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([sz*0.05, sz*0.05, sz*0.95, sz*0.95], radius=sz*0.08,
                         fill=(40, 40, 70, 220), outline=(120, 120, 200, 255), width=2)
    # 격자선
    for i in [0.35, 0.65]:
        d.line([int(sz*0.12), int(sz*i), int(sz*0.88), int(sz*i)],
               fill=(80, 80, 120, 160), width=1)
        d.line([int(sz*i), int(sz*0.12), int(sz*i), int(sz*0.88)],
               fill=(80, 80, 120, 160), width=1)
    # 파형
    pts = []
    n = 12
    for i in range(n + 1):
        x = sz * (0.12 + 0.76 * i / n)
        import math
        y = sz * (0.5 - 0.25 * math.sin(i * math.pi * 1.5 / n))
        pts.append((x, y))
    d.line(pts, fill=(80, 220, 120, 255), width=2)
    return img


_MAKERS = {
    "supply":    _supply,
    "precooler": _precooler,
    "valve":     _valve,
    "tank":      _tank,
    "mux":       _mux,
    "scope":     _scope,
}

_TAGS: dict[str, str] = {}


def setup_icons() -> None:
    """dpg.create_context() 이후 호출. 텍스처 레지스트리에 아이콘 등록."""
    global _TAGS
    with dpg.texture_registry():
        for name, maker in _MAKERS.items():
            img = maker(SIZE).convert("RGBA")
            flat: list[float] = []
            for r, g, b, a in img.getdata():
                flat.extend([r / 255.0, g / 255.0, b / 255.0, a / 255.0])
            tag = f"icon_tex_{name}"
            dpg.add_static_texture(SIZE, SIZE, flat, tag=tag)
            _TAGS[name] = tag


def get_icon_tag(name: str) -> str | None:
    return _TAGS.get(name)
