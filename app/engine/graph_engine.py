"""
Execution Graph Engine — 포트 수준 링크 기반 DAG 실행 엔진.

연결 단위: (src_node, src_port) → (dst_node, dst_port)

예시:
    g.connect("valve", "mass_flow_kg_s", "tank", "mass_flow_in")
    → tick() 시 tank.evaluate(ctx, {"mass_flow_in": 0.107}) 호출

설계 원칙:
  - dirty propagation: 변경된 노드와 그 하위 노드만 재계산
  - 위상 정렬(Kahn's algorithm)으로 순환 감지 및 실행 순서 결정
  - 포트 이름 불일치는 None 으로 전달(노드가 기본값 처리)
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from app.engine.node_context import NodeContext


@dataclass(frozen=True)
class PortLink:
    """단방향 포트 연결 하나를 표현하는 불변 값 객체."""
    src_node: str
    src_port: str
    dst_node: str
    dst_port: str


class GraphEngine:
    def __init__(self) -> None:
        self._nodes: dict[str, Any] = {}
        self._links: list[PortLink] = []
        self._sorted: list[str] = []
        self._cache: dict[str, dict[str, Any]] = {}   # node_id → 마지막 출력 dict
        self._dirty: set[str] = set()

    # ── 그래프 편집 ─────────────────────────────────────────────

    def register_node(self, node_id: str, node: Any) -> None:
        self._nodes[node_id] = node
        self._cache[node_id] = {}
        self.mark_dirty(node_id)
        self._topological_sort()

    def connect(self,
                src_node: str, src_port: str,
                dst_node: str, dst_port: str) -> None:
        """포트 수준 연결. 같은 링크 중복 추가 방지."""
        link = PortLink(src_node, src_port, dst_node, dst_port)
        if link not in self._links:
            self._links.append(link)
        self.mark_dirty(dst_node)
        self._topological_sort()

    def disconnect(self,
                   src_node: str, src_port: str,
                   dst_node: str, dst_port: str) -> None:
        link = PortLink(src_node, src_port, dst_node, dst_port)
        if link in self._links:
            self._links.remove(link)
        self.mark_dirty(dst_node)
        self._topological_sort()

    def disconnect_node(self, node_id: str) -> None:
        """노드 삭제 시 관련 링크 전체 제거."""
        self._links = [l for l in self._links
                       if l.src_node != node_id and l.dst_node != node_id]
        self._nodes.pop(node_id, None)
        self._cache.pop(node_id, None)
        self._dirty.discard(node_id)
        self._topological_sort()

    # ── dirty 관리 ──────────────────────────────────────────────

    def mark_dirty(self, node_id: str) -> None:
        """노드와 그 하위 노드를 모두 dirty 로 표시."""
        if node_id in self._dirty:
            return
        self._dirty.add(node_id)
        for link in self._links:
            if link.src_node == node_id:
                self.mark_dirty(link.dst_node)

    # ── 실행 ────────────────────────────────────────────────────

    def tick(self, ctx: NodeContext) -> dict[str, dict[str, Any]]:
        """
        한 time-step 실행.
        dirty 노드만 evaluate() 호출, 나머지는 캐시 반환.
        반환값: {node_id: output_dict}
        """
        results: dict[str, dict[str, Any]] = {}

        for nid in self._sorted:
            if nid not in self._dirty:
                results[nid] = self._cache.get(nid, {})
                continue

            # 이 노드의 입력 포트를 업스트림 출력에서 수집
            inputs: dict[str, Any] = {}
            for link in self._links:
                if link.dst_node == nid:
                    src_output = self._cache.get(link.src_node, {})
                    inputs[link.dst_port] = src_output.get(link.src_port)

            output = self._nodes[nid].evaluate(ctx, inputs)
            self._cache[nid] = output or {}
            results[nid] = self._cache[nid]

        self._dirty.clear()
        return results

    # ── 위상 정렬 ───────────────────────────────────────────────

    def _topological_sort(self) -> None:
        # 링크에서 노드 간 엣지 추출 (포트 정보 무시)
        edges: dict[str, set[str]] = defaultdict(set)
        for link in self._links:
            if link.src_node in self._nodes and link.dst_node in self._nodes:
                edges[link.src_node].add(link.dst_node)

        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for src, dsts in edges.items():
            for dst in dsts:
                if dst in in_degree:
                    in_degree[dst] += 1

        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order: list[str] = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for dst in edges.get(nid, set()):
                in_degree[dst] -= 1
                if in_degree[dst] == 0:
                    queue.append(dst)

        if len(order) != len(self._nodes):
            raise RuntimeError("그래프에 순환 의존성이 감지되었습니다.")
        self._sorted = order

    # ── 조회 헬퍼 ───────────────────────────────────────────────

    def get_output(self, node_id: str) -> dict[str, Any]:
        return self._cache.get(node_id, {})

    def get_links(self) -> list[PortLink]:
        return list(self._links)
