from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import benchmark, memory_bench
from pc_polimata.gui.widgets import button, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


class BenchmarkTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        self.btn = button(bar, tr("Executar benchmark CPU + disco"), self.run)
        self.btn.pack(side="left")
        self.mem_btn = button(bar, tr("Executar benchmark de memória"), self.run_memory, primary=False)
        self.mem_btn.pack(side="left", padx=8)
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
        self.app.record("cpu_benchmark", cpu.to_dict(), history_kind="cpu")
        self.app.record("disk_benchmark", disk.to_dict(), history_kind="disk")
        set_text(
            self.box,
            f"CPU single-core: {cpu.single_core_score} pts\n"
            f"CPU multi-core:  {cpu.multi_core_score} pts ({cpu.processes} proc., x{cpu.scaling})\n\n"
            f"Disk write: {disk.write_mb_s} MB/s\nDisk read:  {disk.read_mb_s} MB/s ({disk.size_mb} MB, OS cache)",
        )

    def run_memory(self) -> None:
        self.mem_btn.configure(state="disabled")
        set_text(self.box, tr("Executando..."))
        run_in_thread(self.mem_btn, memory_bench.run_memory_benchmark, self.done_memory)

    def done_memory(self, res) -> None:
        self.mem_btn.configure(state="normal")
        if isinstance(res, Exception):
            set_text(self.box, f"Erro: {res}")
            return
        self.app.record("memory_benchmark", res.to_dict(), history_kind="memory")
        set_text(
            self.box,
            f"RAM bandwidth (copy): {res.bandwidth_gb_s} GB/s\n"
            f"RAM latency (random access): ~{res.latency_ns} ns\n"
            f"Backend: {res.backend} — approximation, {res.size_mb} MB buffer",
        )
