"""Geração de relatórios JSON, HTML (tema verde/marrom) e PDF (reportlab opcional)."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from pc_polimata import __version__
from pc_polimata.i18n import N_, tr

SECTION_TITLES = {
    "system": N_("Sistema"),
    "sensors": N_("Sensores"),
    "cpu_benchmark": N_("Benchmark de CPU"),
    "disk_benchmark": N_("Benchmark de disco"),
    "memory_benchmark": N_("Benchmark de memória"),
    "stress_test": N_("Stress test"),
    "bottleneck": N_("Gargalo"),
    "network_latency": N_("Latência de rede"),
    "network_download": N_("Download"),
    "disk_health": N_("Saúde dos discos (SMART)"),
    "games_estimate": N_("Jogos (estimativa)"),
    "diagnosis": N_("Diagnóstico"),
    "drivers": N_("Drivers"),
    "alerts": N_("Alertas"),
    "plugins": N_("Plugins"),
    "fps_capture": N_("FPS (PresentMon)"),
}

PDF_HELP = N_(
    "Exportação em PDF requer o pacote reportlab (pip install reportlab). "
    "Alternativa: exporte em HTML, abra no navegador e use Imprimir > Salvar como PDF."
)


class PdfUnavailableError(RuntimeError):
    """reportlab não está instalado."""


def build_report(system: dict[str, Any], **sections: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "generator": f"PC Polimata {__version__}",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "system": system,
    }
    report.update({k: v for k, v in sections.items() if v is not None})
    return report


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)


def section_title(key: str) -> str:
    return tr(SECTION_TITLES[key]) if key in SECTION_TITLES else key.replace("_", " ").capitalize()


def _is_table(value: list[Any]) -> bool:
    return (
        bool(value)
        and all(isinstance(v, dict) for v in value)
        and all(not isinstance(x, (dict, list)) for v in value for x in v.values())
    )


def _render(value: Any) -> str:
    if isinstance(value, dict):
        rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{_render(v)}</td></tr>" for k, v in value.items())
        return f"<table class='kv'>{rows}</table>"
    if isinstance(value, list):
        if not value:
            return "<span class='muted'>—</span>"
        if _is_table(value):
            cols = list(dict.fromkeys(k for row in value for k in row))
            head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
            body = "".join("<tr>" + "".join(f"<td>{_render(row.get(c))}</td>" for c in cols) + "</tr>" for row in value)
            return f"<table class='grid'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        return "<ul>" + "".join(f"<li>{_render(v)}</li>" for v in value) + "</ul>"
    if value is None:
        return "<span class='muted'>n/d</span>"
    if isinstance(value, bool):
        return "✔" if value else "✖"
    return html.escape(str(value))


def _css() -> str:
    return resources.files("pc_polimata.data").joinpath("report.css").read_text(encoding="utf-8")


def _summary(report: dict[str, Any]) -> list[tuple[str, str]]:
    system = report.get("system", {})
    cards = [
        ("CPU", system.get("cpu", {}).get("name") or "n/d"),
        ("RAM", f"{system.get('memory', {}).get('total_gb', 'n/d')} GB"),
        ("GPU", ", ".join(g.get("name", "") for g in system.get("gpus", [])) or "n/d"),
    ]
    if cpu := report.get("cpu_benchmark"):
        cards.append((tr("Benchmark de CPU"), f"{cpu.get('single_core_score')} / {cpu.get('multi_core_score')}"))
    if diag := report.get("diagnosis"):
        cards.append((tr("Diagnóstico"), f"{diag.get('score')}/100"))
    return cards


def to_html(report: dict[str, Any]) -> str:
    cards = "".join(
        f"<div class='card'><b>{html.escape(k)}</b>{html.escape(str(v))}</div>" for k, v in _summary(report)
    )
    sections = "".join(
        f"<section><h2>{html.escape(section_title(k))}</h2>{_render(v)}</section>"
        for k, v in report.items()
        if k not in {"generator", "generated_at"}
    )
    title = tr("Relatório PC Polimata")
    return (
        f"<!DOCTYPE html><html lang='{'pt-BR' if tr('Sistema') == 'Sistema' else 'en'}'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title>"
        f"<style>{_css()}</style></head><body><header><h1>{html.escape(title)}</h1>"
        f"<p>{html.escape(report['generator'])} — {html.escape(report['generated_at'])}</p></header>"
        f"<div class='summary'>{cards}</div>{sections}"
        f"<footer>PC Polimata — github.com/ThomasRhoden/pc-polimata</footer></body></html>"
    )


def _flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, dict):
        out: list[tuple[str, str]] = []
        for k, v in value.items():
            out += _flatten(v, f"{prefix}{k}." if isinstance(v, (dict, list)) else f"{prefix}{k}")
        return out
    if isinstance(value, list):
        out = []
        for i, v in enumerate(value):
            out += _flatten(v, f"{prefix}{i}." if isinstance(v, (dict, list)) else f"{prefix}{i}")
        return out
    return [(prefix.rstrip("."), "n/d" if value is None else str(value))]


def to_pdf(report: dict[str, Any], path: str | Path) -> Path:
    """Gera um PDF com reportlab; sem ele, lança PdfUnavailableError com instruções."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise PdfUnavailableError(tr(PDF_HELP)) from exc

    green, brown = colors.HexColor("#3f6b3a"), colors.HexColor("#7a5a3a")
    styles = getSampleStyleSheet()
    styles["Title"].textColor = green
    styles["Heading2"].textColor = brown
    cell = styles["BodyText"].clone("cell", fontSize=8, leading=10)

    story: list[Any] = [
        Paragraph(html.escape(tr("Relatório PC Polimata")), styles["Title"]),
        Paragraph(html.escape(f"{report['generator']} — {report['generated_at']}"), styles["BodyText"]),
        Spacer(1, 0.4 * cm),
    ]
    for key, value in report.items():
        if key in {"generator", "generated_at"}:
            continue
        story.append(Paragraph(html.escape(section_title(key)), styles["Heading2"]))
        rows = [[Paragraph(html.escape(k), cell), Paragraph(html.escape(v), cell)] for k, v in _flatten(value)]
        if not rows:
            continue
        table = Table(rows, colWidths=[6 * cm, 11 * cm], repeatRows=0)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbbbbb")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8efe4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story += [table, Spacer(1, 0.3 * cm)]
    out = Path(path)
    SimpleDocTemplate(str(out), pagesize=A4, title=tr("Relatório PC Polimata")).build(story)
    return out


def save_report(report: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return to_pdf(report, path)
    content = to_html(report) if suffix in {".html", ".htm"} else to_json(report)
    path.write_text(content, encoding="utf-8")
    return path
