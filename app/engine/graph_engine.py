"""
Execution Graph Engine — DAG 정렬 및 dirty propagation 기반 노드 실행.
"""
from __future__ import annotations
from collections import defaultdict, deque
from typing import Any

from app.engine.node_context import NodeContext


class GraphEngine:
    """
    노드 그래프를 위상 정렬(Kahn's algorithm)하고
    매 tick 에 변경된 노드만 재계산하는 dirty propagation 엔진.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Any] = {}          # node_id -> SimNode instance
        self._edges: dict[str, list[str]] = defaultdict(list)  # src -> [dst]
        self._sorted: list[str] = []
        self._cache: dict[str, Any] = {}           # node_id -> last output
        self._dirty: set[str] = set()

    def register_node(self, node_id: str, node: Any) -> None:
        self._nodes[node_id] = node
        self.mark_dirty(node_id)

    def connect(self, src_id: str, dst_id: str) -> None:
        self._edges[src_id].append(dst_id)
        self._topological_sort()

    def disconnect(self, src_id: str, dst_id: str) -> None:
        self._edges[src_id].remove(dst_id)
        self._topological_sort()

    def mark_dirty(self, node_id: str) -> None:
        self._dirty.add(node_id)
        for dst in self._edges.get(node_id, []):
            self.mark_dirty(dst)

    def tick(self, ctx: NodeContext) -> dict[str, Any]:
        """한 time-step 실행. dirty 노드만 evaluate."""
        results: dict[str, Any] = {}
        for nid in self._sorted:
            if nid not in self._dirty:
                results[nid] = self._cache.get(nid)
                continue
            node = self._nodes[nid]
            upstream = {src: self._cache.get(src) for src in self._nodes if nid in self._edges.get(src, [])}
            output = node.evaluate(ctx, upstream)
            self._cache[nid] = output
            results[nid] = output
        self._dirty.clear()
        return results

    def _topological_sort(self) -> None:
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for src, dsts in self._edges.items():
            for dst in dsts:
                if dst in in_degree:
                    in_degree[dst] += 1
        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for dst in self._edges.get(nid, []):
                in_degree[dst] -= 1
                if in_degree[dst] == 0:
                    queue.append(dst)
        if len(order) != len(self._nodes):
            raise RuntimeError("순환 의존성이 감지되었습니다.")
        self._sorted = order
