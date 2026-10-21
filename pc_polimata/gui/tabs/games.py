from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import games
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import fmt, set_text, textbox
from pc_polimata.i18n import tr

AUTO = "(detectada)"


class GamesTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        ctk.CTkLabel(
            master, text="⚠ " + tr("Estimativa de desempenho — não é medição real."), text_color=t.BROWN_LIGHT
        ).pack(anchor="w", padx=8, pady=(8, 0))
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(bar, text="GPU:").pack(side="left")
        self.gpu = ctk.CTkOptionMenu(
            bar,
            values=[AUTO, *games.known_gpus()],
            command=lambda _v: self.refresh(),
            fg_color=t.GREEN,
            button_color=t.GREEN_HOVER,
        )
        self.gpu.pack(side="left", padx=6)
        self.box = textbox(master)
        self.refresh()

    def refresh(self) -> None:
        choice = self.gpu.get()
        est = games.estimate_for_system(self.app.system, gpu_override=None if choice == AUTO else choice)
        self.app.record("games_estimate", est)
        lines = [
            f"CPU: {fmt(est['cpu'])}  (tier {fmt(est['cpu_tier'])}/10)",
            f"GPU: {fmt(est['gpu'])}  (tier {fmt(est['gpu_tier'])}/10)",
            "",
            f"{'Jogo':<26} {'Preset provável (1080p ~60 FPS)':<32} Limitado por",
            "-" * 74,
        ]
        lines += [f"{g['game']:<26} {g['preset']:<32} {fmt(g['limited_by'])}" for g in est["games"]]
        if est["gpu_tier"] is None or est["cpu_tier"] is None:
            lines += ["", "CPU ou GPU fora da tabela: escolha uma GPU equivalente no menu acima."]
        set_text(self.box, "\n".join(lines))
