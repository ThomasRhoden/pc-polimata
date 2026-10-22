from __future__ import annotations

import sys

import customtkinter as ctk

from pc_polimata.core.sensors import SensorSnapshot
from pc_polimata.core.timeseries import RollingSeries
from pc_polimata.core.units import format_temp
from pc_polimata.core.windows_temps import HINT
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import LineChart, fmt
from pc_polimata.i18n import tr


class SensorsTab:
    """Barras + gráfico dos últimos 60 s. As leituras vêm da thread de sensores do app (`show`)."""

    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        self.last = None
        self.history = RollingSeries(["cpu", "ram", "gpu"], maxlen=60)
        self.bars: dict[str, tuple[ctk.CTkProgressBar, ctk.CTkLabel]] = {}
        for key in ("cpu", "ram", "gpu"):
            row = ctk.CTkFrame(master, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=key.upper(), width=60, font=t.FONT, anchor="w").pack(side="left")
            bar = ctk.CTkProgressBar(row, progress_color=t.GREEN_LIGHT, width=500)
            bar.pack(side="left", padx=8)
            bar.set(0)
            val = ctk.CTkLabel(row, text="—", font=t.FONT, text_color=t.MUTED)
            val.pack(side="left", padx=8)
            self.bars[key] = (bar, val)
        self.extra = ctk.CTkLabel(master, text="", font=ctk.CTkFont(*t.MONO), justify="left", text_color=t.TEXT)
        self.extra.pack(anchor="w", padx=12, pady=6)
        ctk.CTkLabel(master, text=tr("Histórico dos últimos 60 s"), text_color=t.MUTED).pack(anchor="w", padx=12)
        self.chart = LineChart(master, self.history)
        self.chart.pack(fill="both", expand=True, padx=12, pady=(2, 10))
        if app.last_snapshot is not None:
            self.show(app.last_snapshot)

    def show(self, snap: SensorSnapshot) -> None:
        self.last = snap
        self.history.append(cpu=snap.cpu_percent, ram=snap.ram_percent, gpu=snap.gpu_percent)
        for key, pct in (("cpu", snap.cpu_percent), ("ram", snap.ram_percent), ("gpu", snap.gpu_percent)):
            bar, val = self.bars[key]
            bar.set((pct or 0) / 100)
            val.configure(text=fmt(pct, "%"))
        unit = self.app.settings.temperature_unit
        hint = f"\n{tr(HINT)}" if sys.platform.startswith("win") and snap.cpu_temp_c is None else ""
        self.extra.configure(
            text=(
                tr(
                    "Temperatura CPU: {cpu}   Temperatura GPU: {gpu}",
                    cpu=format_temp(snap.cpu_temp_c, unit),
                    gpu=format_temp(snap.gpu_temp_c, unit),
                )
                + "\n"
                + tr(
                    "Disco leitura: {read} MB/s   escrita: {write} MB/s",
                    read=snap.disk_read_mb_s,
                    write=snap.disk_write_mb_s,
                )
                + "\n"
                + tr("Por núcleo: {cores}", cores=" ".join(f"{p:.0f}" for p in snap.per_core_percent))
                + hint
            )
        )
        self.chart.redraw()
