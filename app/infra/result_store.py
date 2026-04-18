"""
Result Store — 시뮬레이션 결과를 CSV / Parquet 로 저장.
Project JSON 과 분리해 입력 정의와 산출물의 책임을 구분한다.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Any


class ResultStore:
    def __init__(self, output_dir: str = "results") -> None:
        self._dir = Path(output_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save_trends(self, trends: dict[str, list[tuple[float, float]]], tag: str = "") -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = self._dir / f"trend_{tag}_{ts}.csv"
        all_t = sorted({t for series in trends.values() for t, _ in series})
        rows = {t: {} for t in all_t}
        for signal, series in trends.items():
            for t, v in series:
                rows[t][signal] = v
        with open(fname, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["t"] + list(trends.keys()))
            writer.writeheader()
            for t in all_t:
                row = {"t": t}
                row.update(rows[t])
                writer.writerow(row)
        return fname

    def save_project(self, project: dict, name: str) -> Path:
        fname = self._dir / f"{name}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False, indent=2)
        return fname

    def load_project(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
