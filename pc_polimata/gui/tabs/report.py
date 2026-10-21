from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from pc_polimata.core import report
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button
from pc_polimata.i18n import tr


class ReportTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        ctk.CTkLabel(
            master,
            text=tr("Exporta informações do sistema e os resultados desta sessão."),
            text_color=t.MUTED,
        ).pack(anchor="w", padx=8, pady=8)
        button(master, tr("Exportar JSON"), lambda: self.export(".json")).pack(anchor="w", padx=8, pady=4)
        button(master, tr("Exportar HTML"), lambda: self.export(".html"), primary=False).pack(
            anchor="w", padx=8, pady=4
        )
        self.label = ctk.CTkLabel(master, text="", text_color=t.GREEN_LIGHT)
        self.label.pack(anchor="w", padx=8, pady=8)

    def export(self, ext: str) -> None:
        path = filedialog.asksaveasfilename(defaultextension=ext, initialfile=f"pc_polimata{ext}")
        if path:
            report.save_report(self.app.build_report(), path)
            self.label.configure(text=f"{tr('Salvo em')} {path}")
