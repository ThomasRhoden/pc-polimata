from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import benchmark
from pc_polimata.gui.widgets import button, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


class BenchmarkTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        self.btn = button(bar, tr("Executar benchmark CPU + disco"), self.run)
        self.btn.pack(side="left")
        self.box = textbox(master)
        set_text(self.box, tr("Score próprio do PC Polimata (não comparável ao Cinebench)."))

    def run(self) -> None:
        self.btn.configure(state="disabled")
        set_text(self.box, tr("Executando...") + " (~10 s)")
        run_in_thread(
            self.btn, lambda: (benchmark.run_cpu_benchmark(4.0), benchmark.run_disk_benchmark(128)), self.done
        )

    def done(self, res) -> None:
        self.btn.configure(state="normal")
        if isinstance(res, Exception):
            set_text(self.box, f"Erro: {res}")
            return
        cpu, disk = res
        self.app.record("cpu_benchmark", cpu.to_dict())
        self.app.record("disk_benchmark", disk.to_dict())
        set_text(
            self.box,
            f"CPU single-core: {cpu.single_core_score} pts\n"
            f"CPU multi-core:  {cpu.multi_core_score} pts ({cpu.processes} proc., x{cpu.scaling})\n\n"
            f"Disk write: {disk.write_mb_s} MB/s\nDisk read:  {disk.read_mb_s} MB/s ({disk.size_mb} MB, OS cache)",
        )
