from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from pc_polimata.core import report
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button
from pc_polimata.i18n import tr

FORMATS = ((".json", "JSON", True), (".html", "HTML", False), (".pdf", "PDF", False))


class ReportTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        ctk.CTkLabel(
            master, text=tr("Exporta informações do sistema e os resultados desta sessão."), text_color=t.MUTED
        ).pack(anchor="w", padx=8, pady=8)
        for ext, label, primary in FORMATS:
            button(master, tr("Exportar {fmt}", fmt=label), lambda e=ext: self.export(e), primary=primary).pack(
                anchor="w", padx=8, pady=4
            )
        self.label = ctk.CTkLabel(master, text="", text_color=t.GREEN_LIGHT, justify="left", wraplength=900)
        self.label.pack(anchor="w", padx=8, pady=8)

    def export(self, ext: str) -> None:
        path = filedialog.asksaveasfilename(defaultextension=ext, initialfile=f"pc_polimata{ext}")
        if not path:
            return
        try:
            report.save_report(self.app.build_report(), path)
        except report.PdfUnavailableError as exc:
            self.label.configure(text=str(exc), text_color=t.BROWN_LIGHT)
            return
        except OSError as exc:
            self.label.configure(text=tr("Erro: {error}", error=exc), text_color=t.DANGER)
            return
        self.label.configure(text=tr("Salvo em {path}", path=path), text_color=t.GREEN_LIGHT)
