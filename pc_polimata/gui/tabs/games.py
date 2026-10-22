from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import games
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import fmt, set_text, textbox
from pc_polimata.i18n import N_, tr

AUTO = N_("(detectada)")


class GamesTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        ctk.CTkLabel(
            master, text="⚠ " + tr("Estimativa de desempenho — não é medição real."), text_color=t.BROWN_LIGHT
        ).pack(anchor="w", padx=8, pady=(8, 0))
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(bar, text="CPU:").pack(side="left")
        self.cpu = ctk.CTkOptionMenu(
            bar,
            values=[tr(AUTO), *games.known_cpus()],
            command=lambda _v: self.refresh(),
            fg_color=t.GREEN,
            button_color=t.GREEN_HOVER,
        )
        self.cpu.pack(side="left", padx=(6, 16))
        ctk.CTkLabel(bar, text="GPU:").pack(side="left")
        self.gpu = ctk.CTkOptionMenu(
            bar,
            values=[tr(AUTO), *games.known_gpus()],
            command=lambda _v: self.refresh(),
            fg_color=t.GREEN,
            button_color=t.GREEN_HOVER,
        )
        self.gpu.pack(side="left", padx=6)
        self.box = textbox(master)
        self.refresh()

    def refresh(self) -> None:
        gpu, cpu = self.gpu.get(), self.cpu.get()
        est = games.estimate_for_system(
            self.app.system,
            gpu_override=None if gpu == tr(AUTO) else gpu,
            cpu_override=None if cpu == tr(AUTO) else cpu,
        )
        self.app.record("games_estimate", est)
        lines = [
            f"CPU: {fmt(est['cpu'])}  (tier {fmt(est['cpu_tier'])}/10)",
            f"GPU: {fmt(est['gpu'])}  (tier {fmt(est['gpu_tier'])}/10)",
            "",
            f"{tr('Jogo'):<26} {tr('Preset provável (1080p ~60 FPS)'):<32} {tr('Limitado por')}",
            "-" * 74,
        ]
        lines += [f"{g['game']:<26} {tr(g['preset']):<32} {g['limited_by'] or '—'}" for g in est["games"]]
        if est["gpu_tier"] is None or est["cpu_tier"] is None:
            lines += ["", tr("CPU ou GPU fora da tabela: escolha um modelo equivalente nos menus acima.")]
        set_text(self.box, "\n".join(lines))
