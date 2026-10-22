from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from pc_polimata.core import exchange
from pc_polimata.core.exchange import RunBundle
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button, fmt, set_text, textbox
from pc_polimata.i18n import tr

FILETYPES = [("PC Polimata JSON", "*.json")]


class CompareTab:
    """Exporta as execuções deste PC e compara dois arquivos (ou este PC vs. outro) lado a lado."""

    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        self.sides: dict[str, RunBundle | None] = {"a": None, "b": None}
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=8)
        button(bar, tr("Exportar execuções deste PC"), self.export).pack(side="left")
        button(bar, tr("A = este PC"), lambda: self.use_local("a"), primary=False).pack(side="left", padx=(16, 4))
        button(bar, tr("Carregar A…"), lambda: self.load("a"), primary=False).pack(side="left", padx=4)
        button(bar, tr("Carregar B…"), lambda: self.load("b"), primary=False).pack(side="left", padx=4)
        self.status = ctk.CTkLabel(master, text="", text_color=t.MUTED, anchor="w")
        self.status.pack(fill="x", padx=12)
        self.box = textbox(master, 440)
        set_text(self.box, tr("Exporte o JSON em cada PC e carregue os dois aqui para comparar."))

    def local_bundle(self) -> RunBundle:
        runs: list = []
        if self.app.history is not None:
            for kind in exchange.PRIMARY_METRICS:
                latest = self.app.history.list_runs(kind, limit=1)
                runs.extend(latest)
        label = self.app.system["cpu"]["name"] or "PC"
        return exchange.make_bundle(label, self.app.system, runs)

    def export(self) -> None:
        bundle = self.local_bundle()
        if not bundle.runs:
            self.status.configure(text=tr("Nenhuma execução salva ainda."), text_color=t.DANGER)
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=FILETYPES)
        if path:
            exchange.export_bundle(bundle, path)
            self.status.configure(text=tr("Salvo em {path}", path=path), text_color=t.GREEN_LIGHT)

    def use_local(self, side: str) -> None:
        self.sides[side] = self.local_bundle()
        self.render()

    def load(self, side: str, path: str | None = None) -> None:
        path = path or filedialog.askopenfilename(filetypes=FILETYPES)
        if not path:
            return
        try:
            self.sides[side] = exchange.import_bundle(path)
        except (OSError, ValueError) as exc:
            self.status.configure(text=tr("Arquivo inválido: {error}", error=exc), text_color=t.DANGER)
            return
        self.status.configure(text=Path(path).name, text_color=t.MUTED)
        self.render()

    def render(self) -> None:
        a, b = self.sides["a"], self.sides["b"]
        lines = []
        for key, bundle in (("A", a), ("B", b)):
            if bundle:
                m = bundle.machine
                lines.append(
                    f"{key}: {bundle.label} — {m.get('cpu') or '?'} | {', '.join(m.get('gpus') or []) or '—'}"
                    f" | {fmt(m.get('ram_gb'), ' GB')} | {m.get('os') or '?'}"
                )
        if a and b:
            lines += ["", f"{tr('métrica'):<26} {'A':>12} {'B':>12} {tr('B vs A'):>10}  {tr('melhor')}"]
            for row in exchange.compare_bundles(a, b):
                winner = {"a": "A", "b": "B", "tie": "="}.get(row.winner or "", "—")
                lines.append(
                    f"{row.kind + '.' + row.metric:<26} {fmt(row.a):>12} {fmt(row.b):>12}"
                    f" {fmt(row.diff_percent, '%'):>10}  {winner}"
                )
            lines += ["", tr("Diferença < 2% é tratada como empate (ruído normal entre execuções).")]
        set_text(self.box, "\n".join(lines) or tr("Exporte o JSON em cada PC e carregue os dois aqui para comparar."))
