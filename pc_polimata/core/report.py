"""Geração de relatórios JSON e HTML."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pc_polimata import __version__


def build_report(system: dict[str, Any], **sections: Any) -> dict[str, Any]:
    report = {
        "generator": f"PC Polimata {__version__}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "system": system,
    }
    report.update({k: v for k, v in sections.items() if v is not None})
    return report


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)


def _render(value: Any) -> str:
    if isinstance(value, dict):
        rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{_render(v)}</td></tr>" for k, v in value.items())
        return f"<table>{rows}</table>"
    if isinstance(value, list):
        if not value:
            return "<em>—</em>"
        return "<ul>" + "".join(f"<li>{_render(v)}</li>" for v in value) + "</ul>"
    if value is None:
        return "<em>n/d</em>"
    return html.escape(str(value))


_CSS = """
body{background:#141a14;color:#e4e0d4;font-family:Segoe UI,sans-serif;margin:2rem}
h1{color:#7fae6b}h2{color:#b08a5a;border-bottom:1px solid #3d4a33}
table{border-collapse:collapse;margin:.3rem 0}
th{text-align:left;color:#9cc28a;padding:2px 12px 2px 0;vertical-align:top}
td{padding:2px 0}ul{margin:0;padding-left:1rem}
"""


def to_html(report: dict[str, Any]) -> str:
    sections = "".join(
        f"<h2>{html.escape(k)}</h2>{_render(v)}" for k, v in report.items() if k not in {"generator", "generated_at"}
    )
    return (
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
        f"<title>Relatório PC Polimata</title><style>{_CSS}</style></head><body>"
        f"<h1>Relatório PC Polimata</h1><p>{html.escape(report['generator'])} — "
        f"{html.escape(report['generated_at'])}</p>{sections}</body></html>"
    )


def save_report(report: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    content = to_html(report) if path.suffix.lower() in {".html", ".htm"} else to_json(report)
    path.write_text(content, encoding="utf-8")
    return path
