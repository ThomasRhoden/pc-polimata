from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import bottleneck
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button, fmt, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


class BottleneckTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        ctk.CTkLabel(
            master,
            text=tr("Abra o jogo/aplicação que deseja analisar e inicie a amostragem."),
            text_color=t.MUTED,
        ).pack(anchor="w", padx=8, pady=(8, 0))
        form = ctk.CTkFrame(master, fg_color="transparent")
        form.pack(fill="x", padx=8, pady=8)
        self.duration = ctk.CTkSegmentedButton(
            form, values=["30", "45", "60"], selected_color=t.BROWN, selected_hover_color=t.BROWN_HOVER
        )
        self.duration.set("30")
        self.duration.pack(side="left")
        self.btn = button(form, tr("Analisar gargalo"), self.run)
        self.btn.pack(side="left", padx=8)
        self.progress = ctk.CTkProgressBar(master, progress_color=t.GREEN_LIGHT)
        self.progress.pack(fill="x", padx=8)
        self.progress.set(0)
        self.box = textbox(master, 300)

    def run(self) -> None:
        self.btn.configure(state="disabled")
        duration = float(self.duration.get())
        on_progress = lambda p: self.progress.after(0, lambda: self.progress.set(p))  # noqa: E731
        run_in_thread(self.btn, lambda: bottleneck.sample_and_analyze(duration, on_progress=on_progress), self.done)

    def done(self, res) -> None:
        self.btn.configure(state="normal")
        if isinstance(res, Exception):
            set_text(self.box, tr("Erro: {error}", error=res))
            return
        self.app.record("bottleneck", res.to_dict())
        set_text(
            self.box,
            tr("Veredito: {verdict}", verdict=tr(res.verdict))
            + f"\n{res.explanation}\n\n"
            + tr(
                "CPU {cpu}%  |  núcleo mais carregado {core}%  |  GPU {gpu}  |  {samples} amostras",
                cpu=res.avg_cpu,
                core=res.avg_max_core,
                gpu=fmt(res.avg_gpu, "%"),
                samples=res.samples,
            ),
        )
