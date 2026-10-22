from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from pc_polimata.core import fpslog, presentmon
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
        live = ctk.CTkFrame(master, fg_color="transparent")
        live.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(live, text=tr("FPS ao vivo no overlay:")).pack(side="left", padx=(0, 8))
        button(live, tr("Arquivo CSV…"), self.live_file, primary=False).pack(side="left", padx=4)
        button(live, tr("Pasta do MangoHud…"), self.live_folder, primary=False).pack(side="left", padx=4)
        if sys.platform.startswith("win"):
            button(live, tr("PresentMon ao vivo"), self.live_presentmon, primary=False).pack(side="left", padx=4)
        button(live, tr("Parar"), self.stop_live, primary=False).pack(side="left", padx=4)
        self.live_label = ctk.CTkLabel(live, text="", text_color=t.GREEN_LIGHT, font=ctk.CTkFont(*t.MONO))
        self.live_label.pack(side="left", padx=12)
        self.proc: subprocess.Popen[bytes] | None = None
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self.box = textbox(master, 400)
        exe = presentmon.find_presentmon()
        if not sys.platform.startswith("win"):
            intro = tr("No Linux, use o MangoHud com log ativado e escolha a pasta dos logs (ver docs/OVERLAY.md).")
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

    # ---------- ao vivo ----------
    def _start(self, tail: fpslog.FrameLogTail | fpslog.FolderTail, what: str) -> None:
        self.app.start_fps_tail(tail)
        if self.app.overlay is None:
            self.app.toggle_overlay()
        self.live_label.configure(text=tr("acompanhando {what}…", what=what))

    def live_file(self, path: str | None = None) -> None:
        path = path or filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            self._start(fpslog.FrameLogTail(path, process=self.process.get().strip() or None), Path(path).name)

    def live_folder(self, folder: str | None = None) -> None:
        folder = folder or filedialog.askdirectory(initialdir=str(Path.home() / "mangohud_logs"))
        if folder:
            self._start(fpslog.FolderTail(folder), folder)

    def live_presentmon(self) -> None:
        process = self.process.get().strip()
        exe = presentmon.find_presentmon()
        if not process or exe is None:
            set_text(self.box, tr("Informe o processo e instale o PresentMon (ver docs/OVERLAY.md)."))
            return
        self.stop_live()
        self._tmp = tempfile.TemporaryDirectory()
        out = Path(self._tmp.name) / "live.csv"
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.proc = subprocess.Popen(presentmon.live_command(exe, process, out), creationflags=flags)
        except OSError as exc:
            set_text(self.box, tr("Falha na medição: {error}", error=exc))
            return
        self._start(fpslog.FrameLogTail(out, process=process), process)

    def stop_live(self) -> None:
        self.app.stop_fps_tail()
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None
        self.live_label.configure(text="")

    def on_live_stats(self, stats: presentmon.FrameStats | None) -> None:
        text = fpslog.overlay_text(stats)
        self.live_label.configure(text=text or tr("aguardando frames…"))
