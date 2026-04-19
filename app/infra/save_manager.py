"""
save_manager.py — 강건한 저장/불러오기.
  - 버전 마이그레이션 (v1.0 → v2.0)
  - 저장 시 .bak1/.bak2/.bak3 순환 백업
  - 60초마다 ~/.h2sim_autosave.json 자동 저장
  - ~/.h2sim_recent.json 에 최근 파일 목록 유지
"""
from __future__ import annotations
import json
import os
import shutil
import time

CURRENT_VER    = "2.0"
AUTO_INTERVAL  = 60.0   # 자동 저장 주기 (초)
MAX_RECENT     = 8
BACKUP_N       = 3
_RECENT_PATH   = os.path.join(os.path.expanduser("~"), ".h2sim_recent.json")
_AUTOSAVE_PATH = os.path.join(os.path.expanduser("~"), ".h2sim_autosave.json")


# ── 버전 마이그레이션 ─────────────────────────────────────────────

def _migrate_1_0(data: dict) -> dict:
    """v1.0 → v2.0: MUX 노드에 port_labels 필드 추가."""
    for node in data.get("nodes", []):
        if node.get("type") == "mux":
            node.setdefault("params", {}).setdefault("port_labels", {})
    data["version"] = "2.0"
    return data


_MIGRATORS: dict[str, callable] = {
    "1.0": _migrate_1_0,
}


def migrate(data: dict) -> dict:
    ver = data.get("version", "1.0")
    while ver in _MIGRATORS:
        data = _MIGRATORS[ver](data)
        ver  = data.get("version", ver)
    return data


# ── SaveManager ───────────────────────────────────────────────────

class SaveManager:

    def __init__(self) -> None:
        self._recent: list[str]    = []
        self._last_autosave: float = time.time()
        self._load_recent()

    # ── 저장 ───────────────────────────────────────────────────

    def save(self, path: str, data: dict) -> None:
        """JSON 저장 + 순환 백업."""
        data = dict(data)
        data["version"] = CURRENT_VER

        abs_path = os.path.abspath(path)
        dir_name = os.path.dirname(abs_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # 순환 백업: .bak3 ← .bak2 ← .bak1 ← 현재
        if os.path.isfile(abs_path):
            for i in range(BACKUP_N, 0, -1):
                src = f"{abs_path}.bak{i}"
                dst = f"{abs_path}.bak{i+1}" if i < BACKUP_N else None
                if dst and os.path.isfile(src):
                    shutil.move(src, dst)
            shutil.copy2(abs_path, f"{abs_path}.bak1")

        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._add_recent(abs_path)

    # ── 불러오기 ───────────────────────────────────────────────

    def load(self, path: str) -> dict:
        """JSON 불러오기 + 마이그레이션. 실패 시 예외 전파."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data = migrate(data)
        self._add_recent(os.path.abspath(path))
        return data

    # ── 자동 저장 ──────────────────────────────────────────────

    def autosave_if_due(self, data_fn) -> None:
        """
        data_fn: 현재 그래프 dict를 반환하는 callable.
        AUTO_INTERVAL 초마다 호출.
        """
        now = time.time()
        if now - self._last_autosave < AUTO_INTERVAL:
            return
        try:
            self.save(_AUTOSAVE_PATH, data_fn())
        except Exception:
            pass
        self._last_autosave = now

    # ── 최근 파일 ──────────────────────────────────────────────

    def get_recent(self) -> list[str]:
        return [p for p in self._recent if os.path.isfile(p)]

    def _add_recent(self, path: str) -> None:
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        self._recent = self._recent[:MAX_RECENT]
        self._save_recent()

    def _load_recent(self) -> None:
        try:
            with open(_RECENT_PATH, encoding="utf-8") as f:
                self._recent = json.load(f)
        except Exception:
            self._recent = []

    def _save_recent(self) -> None:
        try:
            with open(_RECENT_PATH, "w", encoding="utf-8") as f:
                json.dump(self._recent, f)
        except Exception:
            pass
