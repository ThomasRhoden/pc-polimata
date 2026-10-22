from __future__ import annotations

import sys

import customtkinter as ctk

from pc_polimata.core import presentmon
from pc_polimata.gui import theme as t
from pc_polimata.gui.widgets import button, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


class FpsTab:
    """Liga o overlay e, no Windows com PresentMon, mede FPS/1% low de um jogo."""

    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=8)
        button(bar, tr("Mostrar/ocultar overlay"), app.toggle_overlay).pack(side="left")
        ctk.CTkLabel(bar, text=tr("Processo do jogo:")).pack(side="left", padx=(24, 4))
        self.process = ctk.CTkEntry(bar, width=200, placeholder_text="game.exe")
        self.process.pack(side="left")
        self.seconds = ctk.CTkOptionMenu(bar, values=["10", "30", "60"], width=70, fg_color=t.GREEN)
        self.seconds.pack(side="left", padx=4)
        self.capture_btn = button(bar, tr("Medir FPS (PresentMon)"), self.capture, primary=False)
        self.capture_btn.pack(side="left", padx=4)
        self.box = textbox(master, 420)
        exe = presentmon.find_presentmon()
        if not sys.platform.startswith("win"):
            intro = tr("A medição de FPS usa o PresentMon e só funciona no Windows.")
        elif exe is None:
            intro = tr("PresentMon não encontrado. Instale-o e coloque no PATH (ou defina PRESENTMON_PATH).")
        else:
            intro = tr("PresentMon encontrado: {path}", path=exe)
        set_text(
            self.box,
            intro
            + "\n\n"
            + tr(
                "O overlay funciona em jogos em janela ou janela sem borda; em tela cheia exclusiva ele fica escondido."
            )
            + "\n"
            + tr("Clique direito no overlay fecha; arraste para mover. Detalhes em docs/OVERLAY.md."),
        )

    def capture(self) -> None:
        process = self.process.get().strip()
        if not process:
            set_text(self.box, tr("Informe o nome do executável do jogo (ex.: game.exe)."))
            return
        seconds = int(self.seconds.get())
        self.capture_btn.configure(state="disabled")
        set_text(self.box, tr("Medindo {process} por {seconds} s…", process=process, seconds=seconds))

        def done(result: object) -> None:
            self.capture_btn.configure(state="normal")
            if isinstance(result, Exception):
                set_text(self.box, tr("Falha na medição: {error}", error=result))
                return
            assert isinstance(result, presentmon.FrameStats)
            self.app.record("fps_capture", result.to_dict())
            self.app.last_fps = f"FPS {result.avg_fps:.0f}  1% {result.low_1_percent_fps:.0f}"
            set_text(
                self.box,
                tr(
                    "{process}: {frames} frames\nFPS médio: {fps}\n1% low: {low}\n"
                    "Frametime médio: {ft} ms   p99: {p99} ms   máx: {max} ms",
                    process=result.process or process,
                    frames=result.frames,
                    fps=result.avg_fps,
                    low=result.low_1_percent_fps,
                    ft=result.avg_frametime_ms,
                    p99=result.p99_frametime_ms,
                    max=result.max_frametime_ms,
                ),
            )

        def work() -> object:
            try:
                return presentmon.capture(process, seconds)
            except Exception as exc:  # noqa: BLE001 - mostrado na aba
                return exc

        run_in_thread(self.box, work, done)
