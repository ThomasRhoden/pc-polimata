"""Exportar/importar execuções de benchmark em JSON e comparar duas máquinas.

Formato (``format: "pc-polimata-runs"``, versão 1)::

    {"format": "pc-polimata-runs", "format_version": 1, "app_version": "0.4.0",
     "exported_at": "...", "label": "PC da sala",
     "machine": {"cpu": "...", "gpus": [...], "ram_gb": 32, "os": "..."},
     "runs": [{"kind": "cpu", "created_at": "...", "metrics": {...}, "note": ""}]}

Nenhum dado pessoal entra no arquivo além do que já aparece no relatório
(modelo de CPU/GPU, RAM, SO); o hostname é omitido de propósito.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pc_polimata import __version__
from pc_polimata.core.history import PRIMARY_METRICS, Run

FORMAT = "pc-polimata-runs"
FORMAT_VERSION = 1
MAX_FILE_BYTES = 5 * 2**20


@dataclass
class RunBundle:
    label: str
    machine: dict[str, Any]
    runs: list[dict[str, Any]]
    exported_at: str = ""
    app_version: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def latest(self, kind: str) -> dict[str, Any] | None:
        matching = [r for r in self.runs if r.get("kind") == kind]
        return max(matching, key=lambda r: str(r.get("created_at", ""))) if matching else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT,
            "format_version": FORMAT_VERSION,
            "app_version": self.app_version or __version__,
            "exported_at": self.exported_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": self.label,
            "machine": self.machine,
            "runs": self.runs,
        }


def machine_summary(system: dict[str, Any]) -> dict[str, Any]:
    mem = system.get("memory", {})
    os_info = system.get("os", {})
    return {
        "cpu": system.get("cpu", {}).get("name"),
        "cores": system.get("cpu", {}).get("physical_cores"),
        "threads": system.get("cpu", {}).get("logical_cores"),
        "gpus": [g.get("name") for g in system.get("gpus", [])],
        "ram_gb": mem.get("total_gb"),
        "os": " ".join(str(v) for v in (os_info.get("system"), os_info.get("release")) if v) or None,
    }


def run_to_dict(run: Run) -> dict[str, Any]:
    return {"kind": run.kind, "created_at": run.created_at, "metrics": run.metrics, "note": run.note}


def make_bundle(label: str, system: dict[str, Any], runs: list[Run] | list[dict[str, Any]]) -> RunBundle:
    items = [run_to_dict(r) if isinstance(r, Run) else dict(r) for r in runs]
    return RunBundle(label=label, machine=machine_summary(system), runs=items)


def export_bundle(bundle: RunBundle, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def bundle_from_dict(data: Any) -> RunBundle:
    """Valida e normaliza; erros viram ValueError com mensagem clara."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("not a PC Polimata runs file")
    version = data.get("format_version")
    if not isinstance(version, int) or version > FORMAT_VERSION:
        raise ValueError(f"unsupported format_version: {version!r}")
    runs = data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("'runs' must be a list")
    clean: list[dict[str, Any]] = []
    for item in runs:
        if not isinstance(item, dict) or item.get("kind") not in PRIMARY_METRICS:
            continue  # tipos desconhecidos (versões futuras) são ignorados
        metrics = item.get("metrics")
        if not isinstance(metrics, dict):
            continue
        numeric = {k: v for k, v in metrics.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        clean.append(
            {
                "kind": item["kind"],
                "created_at": str(item.get("created_at", "")),
                "metrics": numeric,
                "note": str(item.get("note", "")),
            }
        )
    if not clean:
        raise ValueError("file has no valid runs")
    raw_machine = data.get("machine")
    machine: dict[str, Any] = raw_machine if isinstance(raw_machine, dict) else {}
    return RunBundle(
        label=str(data.get("label") or machine.get("cpu") or "?"),
        machine=machine,
        runs=clean,
        exported_at=str(data.get("exported_at", "")),
        app_version=str(data.get("app_version", "")),
    )


def import_bundle(path: str | Path) -> RunBundle:
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file too large")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    return bundle_from_dict(data)


@dataclass(frozen=True)
class ComparisonRow:
    kind: str
    metric: str
    a: float | None
    b: float | None
    higher_is_better: bool
    diff_percent: float | None  # (b - a) / a, positivo = B melhor
    winner: str | None  # "a", "b", "tie" ou None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "metric": self.metric,
            "a": self.a,
            "b": self.b,
            "diff_percent": self.diff_percent,
            "winner": self.winner,
        }


def compare_bundles(a: RunBundle, b: RunBundle, tie_percent: float = 2.0) -> list[ComparisonRow]:
    """Compara a execução mais recente de cada tipo, métrica a métrica. Diferença < `tie_percent` = empate."""
    rows: list[ComparisonRow] = []
    for kind, metrics in PRIMARY_METRICS.items():
        run_a, run_b = a.latest(kind), b.latest(kind)
        if run_a is None and run_b is None:
            continue
        for metric, higher in metrics:
            va = run_a["metrics"].get(metric) if run_a else None
            vb = run_b["metrics"].get(metric) if run_b else None
            diff: float | None = None
            winner: str | None = None
            if va and vb is not None:
                raw = (vb - va) / va * 100
                diff = round(raw if higher else -raw, 1)
                winner = "tie" if abs(diff) < tie_percent else ("b" if diff > 0 else "a")
            rows.append(ComparisonRow(kind, metric, va, vb, higher, diff, winner))
    return rows
