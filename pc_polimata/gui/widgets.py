"""Componentes reutilizáveis da GUI."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from pc_polimata.core.timeseries import RollingSeries, to_points
from pc_polimata.gui import theme as t


def fmt(value, unit: str = "") -> str:
    return "n/d" if value is None else f"{value}{unit}"


def button(master, text: str, command, primary: bool = True) -> ctk.CTkButton:
    color, hover = (t.GREEN, t.GREEN_HOVER) if primary else (t.BROWN, t.BROWN_HOVER)
    return ctk.CTkButton(master, text=text, command=command, fg_color=color, hover_color=hover)


def textbox(master, height: int = 380) -> ctk.CTkTextbox:
    box = ctk.CTkTextbox(master, font=ctk.CTkFont(*t.MONO), fg_color=t.BG, text_color=t.TEXT, height=height)
    box.pack(fill="both", expand=True, padx=8, pady=8)
    box.configure(state="disabled")
    return box


def set_text(box: ctk.CTkTextbox, text: str) -> None:
    box.configure(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", text)
    box.configure(state="disabled")


def run_in_thread(widget, work: Callable[[], object], done: Callable[[object], None]) -> None:
    """Executa `work` fora da thread da UI e entrega o resultado via `after()`."""

    def runner():
        try:
            result = work()
        except Exception as exc:  # noqa: BLE001 - mostrado ao usuário em vez de matar a thread
            result = exc
        widget.after(0, lambda: done(result))

    threading.Thread(target=runner, daemon=True).start()


class LineChart(tk.Canvas):
    """Gráfico de linhas leve (0–100 %) desenhado em um Canvas do tkinter."""

    COLORS = (t.GREEN_LIGHT, t.BROWN_LIGHT, t.SKY)

    def __init__(
        self,
        master,
        series: RollingSeries,
        height: int = 160,
        vmax: float = 100.0,
        vmin: float = 0.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        super().__init__(master, height=height, bg=t.BG, highlightthickness=0)
        self.series, self.vmax, self.vmin = series, vmax, vmin
        self.labels = labels or {}
        self.bind("<Configure>", lambda _e: self.redraw())

    def redraw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 2), max(self.winfo_height(), 2)
        top = 22  # espaço da legenda
        for frac in (0.25, 0.5, 0.75):
            y = top + (h - top) * frac
            self.create_line(0, y, w, y, fill=t.GRID, dash=(2, 4))
        legend_x = 8
        for i, name in enumerate(self.series.names):
            color = self.COLORS[i % len(self.COLORS)]
            for seg in to_points(self.series.values(name), w, h - top - 2, self.series.maxlen, self.vmax, self.vmin):
                if len(seg) > 1:
                    self.create_line(*[c for x, y in seg for c in (x, y + top)], fill=color, width=2)
            label = f"■ {self.labels.get(name, name.upper())}"
            item = self.create_text(legend_x, 10, text=label, fill=color, anchor="w", font=(t.FONT[0], 10))
            legend_x = self.bbox(item)[2] + 16
