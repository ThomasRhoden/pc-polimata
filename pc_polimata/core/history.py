"""Histórico de benchmarks em SQLite (biblioteca padrão, sem ORM).

Cada execução vira uma linha com o tipo (`cpu`, `disk`, `memory`), as
métricas em JSON e um resumo do hardware, para comparar execuções ao longo
do tempo (ex.: antes/depois de trocar a pasta térmica).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pc_polimata.core.settings import config_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metrics TEXT NOT NULL,
    hardware TEXT NOT NULL DEFAULT '{}',
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_runs_kind ON runs(kind, created_at);
"""

# Métrica principal de cada tipo e se "maior é melhor".
PRIMARY_METRICS: dict[str, list[tuple[str, bool]]] = {
    "cpu": [("single_core_score", True), ("multi_core_score", True)],
    "disk": [("write_mb_s", True), ("read_mb_s", True)],
    "memory": [("bandwidth_gb_s", True), ("latency_ns", False)],
}


@dataclass(frozen=True)
class Run:
    id: int
    kind: str
    created_at: str
    metrics: dict[str, Any]
    hardware: dict[str, Any]
    note: str = ""


def default_db_path() -> Path:
    return config_dir() / "history.sqlite3"


class HistoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._conn:  # commit/rollback automático
            yield self._conn

    def save_run(
        self,
        kind: str,
        metrics: dict[str, Any],
        hardware: dict[str, Any] | None = None,
        note: str = "",
        created_at: datetime | None = None,
    ) -> int:
        if kind not in PRIMARY_METRICS:
            raise ValueError(f"unknown run kind: {kind}")
        ts = (created_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")
        with self._tx() as conn:
            cur = conn.execute(
                "INSERT INTO runs (kind, created_at, metrics, hardware, note) VALUES (?, ?, ?, ?, ?)",
                (kind, ts, json.dumps(metrics), json.dumps(hardware or {}), note),
            )
            return int(cur.lastrowid)

    def list_runs(self, kind: str | None = None, limit: int = 50) -> list[Run]:
        query = "SELECT * FROM runs"
        params: tuple = ()
        if kind:
            query += " WHERE kind = ?"
            params = (kind,)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        rows = self._conn.execute(query, (*params, limit)).fetchall()
        return [
            Run(r["id"], r["kind"], r["created_at"], json.loads(r["metrics"]), json.loads(r["hardware"]), r["note"])
            for r in rows
        ]

    def get(self, run_id: int) -> Run | None:
        runs = [r for r in self.list_runs(limit=10**6) if r.id == run_id]
        return runs[0] if runs else None

    def delete(self, run_id: int) -> bool:
        with self._tx() as conn:
            return conn.execute("DELETE FROM runs WHERE id = ?", (run_id,)).rowcount > 0

    def close(self) -> None:
        self._conn.close()


def compare(old: Run, new: Run) -> dict[str, dict[str, float | None]]:
    """Diferença percentual por métrica principal; positivo = melhorou."""
    if old.kind != new.kind:
        raise ValueError("cannot compare runs of different kinds")
    out = {}
    for metric, higher_is_better in PRIMARY_METRICS[old.kind]:
        a, b = old.metrics.get(metric), new.metrics.get(metric)
        change = None
        if a and b is not None:
            change = (b - a) / a * 100
            if not higher_is_better:
                change = -change
            change = round(change, 1)
        out[metric] = {"old": a, "new": b, "improvement_percent": change}
    return out


def series(runs: list[Run], metric: str) -> list[float | None]:
    """Valores de uma métrica em ordem cronológica (para gráfico)."""
    return [r.metrics.get(metric) for r in sorted(runs, key=lambda r: (r.created_at, r.id))]
