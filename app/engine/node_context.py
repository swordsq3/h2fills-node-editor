"""
NodeContext — evaluate() 호출 시 각 노드에 전달되는 실행 컨텍스트.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeContext:
    t: float                      # 현재 시각 [s]
    dt: float                     # 시간 간격 [s]
    scenario: dict = field(default_factory=dict)   # 시나리오 파라미터
    stop_flag: bool = False        # 강제 정지 요청
    logger: Any = None             # EventBus/Logger 참조
    unit_system: str = "SI"        # 단위계
