from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from pc_polimata.core.history import PRIMARY_METRICS, compare, series
from pc_polimata.core.timeseries import RollingSeries
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import LineChart, button, fmt, set_text, textbox
from pc_polimata.i18n import N_, tr

KIND_LABELS = {"cpu": "CPU", "disk": N_("Disco"), "memory": N_("Memória")}


def _local(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M:%S")


class HistoryTab:
    """Lista execuções salvas, compara as duas mais recentes e plota a evolução."""

    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        self.kind = ctk.CTkSegmentedButton(
            bar,
            values=[tr(v) for v in KIND_LABELS.values()],
            command=lambda _v: self.refresh(),
            selected_color=t.BROWN,
            selected_hover_color=t.BROWN_HOVER,
        )
        self.kind.set(tr(KIND_LABELS["cpu"]))
        self.kind.pack(side="left")
        button(bar, tr("Comparar execuções"), self.refresh).pack(side="left", padx=8)
        self.chart_label = ctk.CTkLabel(master, text="", text_color=t.MUTED)
        self.chart_label.pack(anchor="w", padx=12)
        self.series = RollingSeries(["a", "b"], maxlen=20)
        self.chart = LineChart(master, self.series, height=180)
        self.chart.pack(fill="x", padx=12)
        self.box = textbox(master, 240)
        self.refresh()

    def _kind(self) -> str:
        label = self.kind.get()
        return next(k for k, v in KIND_LABELS.items() if tr(v) == label)

    def refresh(self) -> None:
        store = self.app.history
        if store is None:
            set_text(self.box, tr("Histórico indisponível (banco SQLite não pôde ser aberto)."))
            return
        kind = self._kind()
        runs = store.list_runs(kind, limit=20)
        if not runs:
            set_text(self.box, tr("Nenhuma execução salva ainda."))
            self.chart.series = RollingSeries(["a"], maxlen=20)
            self.chart.redraw()
            return
        metrics = [m for m, _ in PRIMARY_METRICS[kind]]
        # normaliza cada métrica para 0–100 % do melhor valor, para caber no mesmo gráfico
        rolling = RollingSeries(metrics, maxlen=max(len(runs), 2))
        values = {m: series(runs, m) for m in metrics}
        peaks = {m: max((v for v in values[m] if v), default=1) for m in metrics}
        for i in range(len(runs)):
            rolling.append(**{m: (values[m][i] / peaks[m] * 100 if values[m][i] else None) for m in metrics})
        self.chart.series = rolling
        self.chart.labels = {m: m.replace("_", " ") for m in metrics}
        known = [v for m in metrics for v in rolling.values(m) if v is not None]
        self.chart.vmin = max(0.0, (min(known) // 5) * 5 - 5) if known else 0.0
        self.chart.redraw()
        self.chart_label.configure(
            text=tr("% do melhor resultado de cada métrica (eixo ajustado), mais antigo → recente")
        )

        lines = []
        if len(runs) >= 2:
            lines.append(tr("Última (#{new}) vs anterior (#{old}):", new=runs[0].id, old=runs[1].id))
            for metric, d in compare(runs[1], runs[0]).items():
                change = d["improvement_percent"]
                arrow = "" if change is None else ("▲" if change > 0 else "▼" if change < 0 else "=")
                lines.append(f"  {metric:<20} {fmt(d['old']):>10} → {fmt(d['new']):>10}  {arrow} {fmt(change, '%')}")
            lines.append("")
        lines.append(f"{'#':>4}  {tr('data (local)'):<20} " + "  ".join(f"{m:>18}" for m in metrics))
        for r in runs:
            lines.append(
                f"{r.id:>4}  {_local(r.created_at):<20} " + "  ".join(f"{fmt(r.metrics.get(m)):>18}" for m in metrics)
            )
        set_text(self.box, "\n".join(lines))
