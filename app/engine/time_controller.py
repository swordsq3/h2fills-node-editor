"""
Time Controller — 시뮬레이션 시계의 단일 기준원.
UI 이벤트 루프와 완전히 분리된 시뮬레이션 시간을 관리한다.
"""
from dataclasses import dataclass, field
from enum import Enum, auto


class SimState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()


@dataclass
class TimeController:
    dt: float = 1.0          # 기본 시간 간격 [s]
    t_end: float = 600.0     # 시뮬레이션 종료 시각 [s]
    t: float = field(default=0.0, init=False)
    state: SimState = field(default=SimState.IDLE, init=False)
    _step_count: int = field(default=0, init=False)

    def reset(self) -> None:
        self.t = 0.0
        self._step_count = 0
        self.state = SimState.IDLE

    def start(self) -> None:
        if self.state in (SimState.IDLE, SimState.PAUSED):
            self.state = SimState.RUNNING

    def pause(self) -> None:
        if self.state == SimState.RUNNING:
            self.state = SimState.PAUSED

    def step(self) -> bool:
        """한 tick 진행. 시뮬레이션이 끝나면 False 반환."""
        if self.state not in (SimState.RUNNING, SimState.PAUSED):
            return False
        self.t += self.dt
        self._step_count += 1
        if self.t >= self.t_end:
            self.state = SimState.FINISHED
            return False
        return True

    def seek(self, target_t: float) -> None:
        """특정 시각으로 점프 (replay 용도)."""
        self.t = max(0.0, min(target_t, self.t_end))

    @property
    def progress(self) -> float:
        return self.t / self.t_end if self.t_end > 0 else 0.0

    @property
    def is_running(self) -> bool:
        return self.state == SimState.RUNNING
