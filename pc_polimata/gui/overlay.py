"""Overlay sempre visível com CPU/GPU/RAM/temperaturas.

É uma janela Tk comum sem borda, `-topmost` e com transparência por
`-alpha`. Fica por cima de janelas e de jogos em modo janela/janela sem
borda; jogos em tela cheia exclusiva (DirectX/Vulkan) desenham por cima de
qualquer janela do SO, então o overlay some neles. Ver docs/OVERLAY.md.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from pc_polimata.core.live import SIZES, overlay_geometry, overlay_lines
from pc_polimata.core.sensors import SensorSnapshot
from pc_polimata.gui import theme as t


class Overlay(ctk.CTkToplevel):
    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self.app = app
        cfg = app.settings.overlay_config()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", cfg.opacity)
        except Exception:  # noqa: BLE001 - alguns gerenciadores de janela X11 não suportam
            pass
        self.configure(fg_color=t.BG)
        self.label = ctk.CTkLabel(
            self,
            text="…",
            justify="left",
            anchor="nw",
            font=ctk.CTkFont(t.MONO[0], SIZES[cfg.size][2], weight="bold"),
            text_color=t.GREEN_LIGHT,
        )
        self.label.pack(fill="both", expand=True, padx=10, pady=8)
        self.geometry(overlay_geometry(cfg, self.winfo_screenwidth(), self.winfo_screenheight()))
        # arrastar com o botão esquerdo; clique direito fecha
        self.bind("<ButtonPress-1>", self._start_drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Button-3>", lambda _e: app.toggle_overlay())
        self.label.bind("<ButtonPress-1>", self._start_drag)
        self.label.bind("<B1-Motion>", self._drag)
        self.label.bind("<Button-3>", lambda _e: app.toggle_overlay())
        self._drag_from = (0, 0)

    def _start_drag(self, event: Any) -> None:
        self._drag_from = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _drag(self, event: Any) -> None:
        dx, dy = self._drag_from
        self.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")

    def update_snapshot(self, snap: SensorSnapshot, fps: str | None = None) -> None:
        self.label.configure(text="\n".join(overlay_lines(snap, self.app.settings.temperature_unit, fps)))
