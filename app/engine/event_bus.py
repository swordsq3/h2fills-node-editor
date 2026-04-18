"""
Event Bus & Logger — 실행 흔적, 알람, trend 데이터를 중앙 수집.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable
import csv
import io


class EventLevel(Enum):
    INFO = auto()
    WARNING = auto()
    ALARM = auto()
    FAULT = auto()


@dataclass
class SimEvent:
    t: float
    level: EventLevel
    source: str
    message: str


class EventBus:
    def __init__(self) -> None:
        self._events: list[SimEvent] = []
        self._trend: dict[str, list[tuple[float, float]]] = {}  # signal -> [(t, v)]
        self._subscribers: list[Callable[[SimEvent], None]] = []

    def subscribe(self, fn: Callable[[SimEvent], None]) -> None:
        self._subscribers.append(fn)

    def emit(self, t: float, level: EventLevel, source: str, message: str) -> None:
        ev = SimEvent(t=t, level=level, source=source, message=message)
        self._events.append(ev)
        for fn in self._subscribers:
            fn(ev)

    def log_trend(self, t: float, signal: str, value: float) -> None:
        self._trend.setdefault(signal, []).append((t, value))

    def get_trend(self, signal: str) -> list[tuple[float, float]]:
        return self._trend.get(signal, [])

    def export_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["t", "level", "source", "message"])
        for ev in self._events:
            writer.writerow([ev.t, ev.level.name, ev.source, ev.message])
        return buf.getvalue()

    def reset(self) -> None:
        self._events.clear()
        self._trend.clear()
