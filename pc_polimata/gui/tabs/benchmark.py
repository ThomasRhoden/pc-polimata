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
        set_text(self.box, tr("Executando... (~{seconds} s)", seconds=10))
        run_in_thread(
            self.btn, lambda: (benchmark.run_cpu_benchmark(4.0), benchmark.run_disk_benchmark(128)), self.done
        )

    def done(self, res) -> None:
        self.btn.configure(state="normal")
        if isinstance(res, Exception):
            set_text(self.box, tr("Erro: {error}", error=res))
            return
        cpu, disk = res
        self.app.record("cpu_benchmark", cpu.to_dict(), history_kind="cpu")
        self.app.record("disk_benchmark", disk.to_dict(), history_kind="disk")
        set_text(
            self.box,
            tr(
                "CPU single-core: {single} pts\nCPU multi-core:  {multi} pts ({procs} processos, escala {scaling}x)\n\n"
                "Disco escrita: {write} MB/s\nDisco leitura: {read} MB/s (arquivo de {size} MB; pode vir do cache)",
                single=cpu.single_core_score,
                multi=cpu.multi_core_score,
                procs=cpu.processes,
                scaling=cpu.scaling,
                write=disk.write_mb_s,
                read=disk.read_mb_s,
                size=disk.size_mb,
            ),
        )

    def run_memory(self) -> None:
        self.mem_btn.configure(state="disabled")
        set_text(self.box, tr("Executando..."))
        run_in_thread(self.mem_btn, memory_bench.run_memory_benchmark, self.done_memory)

    def done_memory(self, res) -> None:
        self.mem_btn.configure(state="normal")
        if isinstance(res, Exception):
            set_text(self.box, tr("Erro: {error}", error=res))
            return
        self.app.record("memory_benchmark", res.to_dict(), history_kind="memory")
        set_text(
            self.box,
            tr(
                "Largura de banda da RAM (cópia): {bw} GB/s\nLatência da RAM (acesso aleatório): ~{lat} ns\n"
                "Backend: {backend} — aproximação, buffer de {size} MB",
                bw=res.bandwidth_gb_s,
                lat=res.latency_ns,
                backend=res.backend,
                size=res.size_mb,
            ),
        )
