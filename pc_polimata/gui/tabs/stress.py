from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core.stress import StressConfig, StressTest
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button, fmt, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


class StressTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app, self.stress = app, None
        form = ctk.CTkFrame(master, fg_color="transparent")
        form.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(form, text=tr("Duração (s):")).pack(side="left")
        self.duration = ctk.CTkEntry(form, width=70)
        self.duration.insert(0, "60")
        self.duration.pack(side="left", padx=6)
        ctk.CTkLabel(form, text=tr("Limite temp. (°C):")).pack(side="left")
        self.temp = ctk.CTkEntry(form, width=70)
        self.temp.insert(0, "90")
        self.temp.pack(side="left", padx=6)
        self.start_btn = button(form, tr("Iniciar"), self.start)
        self.start_btn.pack(side="left", padx=6)
        ctk.CTkButton(form, text=tr("PARAR"), command=self.stop, fg_color=t.DANGER, hover_color=t.BROWN_HOVER).pack(
            side="left"
        )
        self.box = textbox(master)

    def start(self) -> None:
        try:
            cfg = StressConfig(float(self.duration.get()), float(self.temp.get()))
        except ValueError as exc:
            set_text(self.box, f"{tr('Configuração inválida')}: {exc}")
            return
        self.stress = StressTest(cfg)
        self.start_btn.configure(state="disabled")

        def on_sample(s):
            msg = f"{s['elapsed_s']:>6}s  CPU {s['cpu_percent']:>5}%  temp {fmt(s['temp_c'], ' °C')}"
            self.box.after(0, lambda: set_text(self.box, msg))

        run_in_thread(self.box, lambda: self.stress.run(on_sample), self.done)

    def done(self, res) -> None:
        self.start_btn.configure(state="normal")
        if isinstance(res, Exception):
            set_text(self.box, f"Erro: {res}")
            return
        self.app.record("stress_test", res.to_dict())
        set_text(
            self.box,
            f"{tr('Fim')}: {res.stop_reason}\n{tr('Tempo')}: {res.elapsed_s}s   "
            f"{tr('Temp. máx.')}: {fmt(res.max_temp_c, ' °C')}",
        )

    def stop(self) -> None:
        if self.stress:
            self.stress.stop()
