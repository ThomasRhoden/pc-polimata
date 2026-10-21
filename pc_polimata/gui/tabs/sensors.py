from __future__ import annotations

import sys

import customtkinter as ctk

from pc_polimata.core.sensors import SensorMonitor
from pc_polimata.core.timeseries import RollingSeries
from pc_polimata.core.units import format_temp
from pc_polimata.core.windows_temps import HINT
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import LineChart, fmt
from pc_polimata.i18n import tr


class SensorsTab:
    """Barras instantâneas + gráfico dos últimos 60 s, atualizados por `after()`."""

    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        self.last = None
        self.monitor = SensorMonitor()
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
        master.after(300, self.refresh)

    def refresh(self) -> None:
        snap = self.last = self.monitor.read()
        self.history.append(cpu=snap.cpu_percent, ram=snap.ram_percent, gpu=snap.gpu_percent)
        for key, pct in (("cpu", snap.cpu_percent), ("ram", snap.ram_percent), ("gpu", snap.gpu_percent)):
            bar, val = self.bars[key]
            bar.set((pct or 0) / 100)
            val.configure(text=fmt(pct, "%"))
        unit = self.app.settings.temperature_unit
        hint = f"\n{HINT}" if sys.platform.startswith("win") and snap.cpu_temp_c is None else ""
        self.extra.configure(
            text=(
                f"{tr('Temperatura CPU')}: {format_temp(snap.cpu_temp_c, unit)}   "
                f"{tr('Temperatura GPU')}: {format_temp(snap.gpu_temp_c, unit)}\n"
                f"{tr('Disco leitura')}: {snap.disk_read_mb_s} MB/s   {tr('escrita')}: {snap.disk_write_mb_s} MB/s\n"
                f"{tr('Por núcleo')}: {' '.join(f'{p:.0f}' for p in snap.per_core_percent)}{hint}"
            )
        )
        self.chart.redraw()
        self.extra.after(self.app.settings.refresh_ms, self.refresh)
