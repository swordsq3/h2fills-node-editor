"""
SimNode — 시뮬레이션 노드 추상 기반 클래스.
기존 템플릿의 node_abc.py 와 병렬로 존재하며,
도메인 계산(evaluate) 책임만 담당한다.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from app.engine.node_context import NodeContext


class SimNode(ABC):
    """
    상태를 가질 수도 있고(Tank) 순수 함수일 수도 있는(Valve) 노드 공통 계약.

    evaluate(ctx, inputs) -> dict  :  매 tick 호출, 출력값 반환
    reset()                        :  초기 상태로 복원
    serialize() -> dict            :  JSON 직렬화
    deserialize(data)              :  JSON 역직렬화
    """

    @abstractmethod
    def evaluate(self, ctx: NodeContext, inputs: dict[str, Any]) -> dict[str, Any]:
        ...

    def reset(self) -> None:
        pass

    def serialize(self) -> dict:
        return {}

    def deserialize(self, data: dict) -> None:
        pass
