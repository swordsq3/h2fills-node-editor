"""
jump_lines.py — Simulink 스타일 직선 + 교차 점프 아크 오버레이.

전략:
  - ImNodes 링크 색상을 투명하게 설정 (h2_node_editor에서 처리)
  - viewport drawlist에 Manhattan L-라우팅 선을 직접 그림
  - 교차점에 반원 아크(점프 선)를 그려 비연결 교차임을 표시
  - 매 tick마다 dpg.get_item_rect_min/max 로 핀 위치를 screen-space로 쿼리

좌표계:
  dpg.get_item_rect_min(attr_tag) → 전역 screen 좌표
  viewport drawlist도 같은 전역 screen 좌표 사용 → 별도 변환 없음
"""
from __future__ import annotations
import math
import dearpygui.dearpygui as dpg
from app.ui.link_styler import get_link_color

JUMP_R    = 6.0    # 점프 아크 반지름 (픽셀)
THICKNESS = 2.0    # 기본 선 두께
BUS_THICK = 3.5    # 버스(ch*) 선 두께
ARC_SEGS  = 10     # 아크 폴리라인 분할 수


# ── 핀 위치 계산 ─────────────────────────────────────────────────

def _pin_pos(attr_tag: str, kind: str) -> tuple[float, float] | None:
    """
    attr_tag: DPG node_attribute 아이템 태그
    kind: "out" → 오른쪽 중앙, "in" → 왼쪽 중앙
    """
    if not dpg.does_item_exist(attr_tag):
        return None
    try:
        mn = dpg.get_item_rect_min(attr_tag)
        mx = dpg.get_item_rect_max(attr_tag)
        cy = (mn[1] + mx[1]) / 2.0
        return (mx[0], cy) if kind == "out" else (mn[0], cy)
    except Exception:
        return None


# ── Manhattan 라우팅 ─────────────────────────────────────────────

def _route(p1: tuple, p2: tuple) -> list[tuple]:
    """L자 경로: 수평 먼저 → 수직."""
    mx = (p1[0] + p2[0]) / 2.0
    return [p1, (mx, p1[1]), (mx, p2[1]), p2]


def _to_segs(pts: list[tuple]) -> list[tuple]:
    return [(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
            for i in range(len(pts) - 1)]


# ── 교차 검출 ────────────────────────────────────────────────────

def _cross_point(s1: tuple, s2: tuple) -> tuple[float, float] | None:
    """
    수평/수직 세그먼트 쌍의 교차점 반환.
    같은 방향이거나 끝점 공유이면 None.
    """
    x1a, y1a, x1b, y1b = s1
    x2a, y2a, x2b, y2b = s2
    h1 = abs(y1a - y1b) < 0.5
    h2 = abs(y2a - y2b) < 0.5
    if h1 == h2:
        return None   # 평행

    if h1:
        hx1, hx2 = min(x1a, x1b), max(x1a, x1b)
        hy = y1a
        vx = x2a
        vy1, vy2 = min(y2a, y2b), max(y2a, y2b)
    else:
        hx1, hx2 = min(x2a, x2b), max(x2a, x2b)
        hy = y2a
        vx = x1a
        vy1, vy2 = min(y1a, y1b), max(y1a, y1b)

    eps = 4.0   # 끝점 근처 무시 (교차가 아닌 T-합류 방지)
    if hx1 + eps < vx < hx2 - eps and vy1 + eps < hy < vy2 - eps:
        return (vx, hy)
    return None


# ── 점프 아크 그리기 ─────────────────────────────────────────────

def _draw_arc(dl: str, cx: float, cy: float,
              is_horiz: bool, color: tuple, thickness: float) -> None:
    """
    교차점 (cx, cy)에 위쪽(수평 세그먼트) 또는 왼쪽(수직 세그먼트) 방향으로
    작은 반원 아크를 그린다.
    """
    pts: list[tuple] = []
    for i in range(ARC_SEGS + 1):
        a = math.pi * i / ARC_SEGS   # 0 → π
        if is_horiz:
            px = cx - JUMP_R + (2 * JUMP_R * i / ARC_SEGS)
            py = cy - JUMP_R * math.sin(a)
        else:
            px = cx - JUMP_R * math.sin(a)
            py = cy - JUMP_R + (2 * JUMP_R * i / ARC_SEGS)
        pts.append((px, py))
    try:
        dpg.draw_polyline(pts, color=color, thickness=thickness, parent=dl)
    except Exception:
        pass


# ── 메인 오버레이 클래스 ─────────────────────────────────────────

class JumpLineOverlay:
    """
    매 tick 호출되는 점프선 오버레이.
    H2NodeEditor.__init__ 에서 생성하고, ensure_init()은 viewport show 직후 호출.
    """

    def __init__(self) -> None:
        self._dl    = "jump_dl"
        self._ready = False

    def ensure_init(self) -> None:
        """dpg.show_viewport() 이후, 첫 번째 render 이전에 호출."""
        if not self._ready:
            try:
                dpg.add_viewport_drawlist(tag=self._dl, front=True)
                self._ready = True
            except Exception:
                pass

    def update(self, links: list[tuple]) -> None:
        """
        links: [(src_node, src_port, dst_node, dst_port), ...]
        """
        if not self._ready or not dpg.does_item_exist(self._dl):
            return

        # 이전 프레임 클리어
        try:
            dpg.delete_item(self._dl, children_only=True)
        except Exception:
            return

        # ── 라우트 계산 ────────────────────────────────────────
        routes: list[dict] = []
        for sn, sp, dn, dp in links:
            p1 = _pin_pos(f"dpg_{sn}_out_{sp}", "out")
            p2 = _pin_pos(f"dpg_{dn}_in_{dp}",  "in")
            if p1 is None or p2 is None:
                continue
            is_bus = sp.startswith("ch")
            color  = get_link_color(sp)
            thick  = BUS_THICK if is_bus else THICKNESS
            pts    = _route(p1, p2)
            routes.append({
                "segs":  _to_segs(pts),
                "color": color,
                "thick": thick,
            })

        if not routes:
            return

        # ── 교차점 탐색 ────────────────────────────────────────
        # crossing_info[i] = [(crossing_point, seg_index), ...]
        crossing_info: list[list] = [[] for _ in routes]
        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                for si, seg_i in enumerate(routes[i]["segs"]):
                    for sj, seg_j in enumerate(routes[j]["segs"]):
                        pt = _cross_point(seg_i, seg_j)
                        if pt:
                            crossing_info[i].append((pt, si))
                            crossing_info[j].append((pt, sj))

        # ── 선 그리기 ──────────────────────────────────────────
        for r in routes:
            for x1, y1, x2, y2 in r["segs"]:
                try:
                    dpg.draw_line((x1, y1), (x2, y2),
                                  color=r["color"],
                                  thickness=r["thick"],
                                  parent=self._dl)
                except Exception:
                    pass

        # ── 점프 아크 그리기 ───────────────────────────────────
        # 인덱스가 더 높은(나중에 추가된) 라우트가 점프(아크를 그림)
        for j in range(len(routes)):
            for pt, si in crossing_info[j]:
                seg = routes[j]["segs"][si]
                is_h = abs(seg[1] - seg[3]) < 0.5
                _draw_arc(self._dl, pt[0], pt[1],
                          is_h, routes[j]["color"], routes[j]["thick"])
