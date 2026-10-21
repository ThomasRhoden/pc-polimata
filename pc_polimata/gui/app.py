"""Janela principal do PC Polimata.

Trabalho pesado roda em threads (que por sua vez usam multiprocessing);
a GUI só é atualizada pela thread principal via `after()`.
"""

from __future__ import annotations

import threading
from tkinter import filedialog

import customtkinter as ctk

from pc_polimata.core import benchmark, bottleneck, report
from pc_polimata.core.sensors import SensorMonitor
from pc_polimata.core.stress import StressConfig, StressTest
from pc_polimata.core.system_info import get_system_info
from pc_polimata.gui import theme as t


def _fmt(v, unit="") -> str:
    return "n/d" if v is None else f"{v}{unit}"


def _button(master, text, command, color=t.GREEN, hover=t.GREEN_HOVER):
    return ctk.CTkButton(master, text=text, command=command, fg_color=color, hover_color=hover)


class PolimataApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("PC Polimata")
        self.geometry("980x640")
        self.configure(fg_color=t.BG)
        self.results: dict = {}
        self.system = get_system_info()

        header = ctk.CTkLabel(self, text="PC Polimata", font=t.FONT_TITLE, text_color=t.GREEN_LIGHT)
        header.pack(anchor="w", padx=16, pady=(12, 0))

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=t.PANEL,
            segmented_button_selected_color=t.BROWN,
            segmented_button_selected_hover_color=t.BROWN_HOVER,
        )
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        for name in ("Sistema", "Sensores", "Benchmark", "Stress test", "Gargalo", "Relatório"):
            self.tabs.add(name)
        self._build_system(self.tabs.tab("Sistema"))
        self._build_sensors(self.tabs.tab("Sensores"))
        self._build_benchmark(self.tabs.tab("Benchmark"))
        self._build_stress(self.tabs.tab("Stress test"))
        self._build_bottleneck(self.tabs.tab("Gargalo"))
        self._build_report(self.tabs.tab("Relatório"))

    # ---------- utilidades ----------
    def _textbox(self, master, height=380):
        box = ctk.CTkTextbox(
            master, font=ctk.CTkFont(*t.MONO), fg_color=t.BG, text_color=t.TEXT, height=height
        )
        box.pack(fill="both", expand=True, padx=8, pady=8)
        return box

    def _set_text(self, box, text: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _in_thread(self, work, done) -> None:
        def runner():
            result = work()
            self.after(0, lambda: done(result))

        threading.Thread(target=runner, daemon=True).start()

    # ---------- Sistema ----------
    def _build_system(self, tab) -> None:
        s = self.system
        lines = [
            "SISTEMA OPERACIONAL",
            f"  {s['os']['system']} {s['os']['release']} ({s['os']['machine']})",
            f"  Host: {s['os']['hostname']}   Python {s['os']['python']}",
            "",
            "PROCESSADOR",
            f"  {s['cpu']['name']}",
            f"  Núcleos: {s['cpu']['physical_cores']} físicos / {s['cpu']['logical_cores']} lógicos",
            f"  Frequência máx.: {_fmt(s['cpu']['max_freq_mhz'], ' MHz')}",
            "",
            "MEMÓRIA",
            f"  Total: {s['memory']['total_gb']} GB   Em uso: {s['memory']['used_percent']}%",
            "",
            "DISCOS",
        ]
        lines += [
            f"  {d['mountpoint']:<20} {d['fstype']:<8} {d['total_gb']:>8} GB  {d['used_percent']}% usado"
            for d in s["disks"]
        ]
        lines += ["", "GPU"]
        lines += [
            f"  {g['name']} — {_fmt(g['memory_total_mb'], ' MB')} — driver {_fmt(g['driver'])}"
            for g in s["gpus"]
        ] or ["  Nenhuma GPU com telemetria detectada (suporte: NVIDIA)."]
        self._set_text(self._textbox(tab), "\n".join(lines))

    # ---------- Sensores ----------
    def _build_sensors(self, tab) -> None:
        self.monitor = SensorMonitor()
        self.sensor_bars: dict[str, tuple[ctk.CTkProgressBar, ctk.CTkLabel]] = {}
        for key, label in (("cpu", "CPU"), ("ram", "RAM"), ("gpu", "GPU")):
            row = ctk.CTkFrame(tab, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)
            ctk.CTkLabel(row, text=label, width=60, font=t.FONT, anchor="w").pack(side="left")
            bar = ctk.CTkProgressBar(row, progress_color=t.GREEN_LIGHT, width=500)
            bar.pack(side="left", padx=8)
            bar.set(0)
            val = ctk.CTkLabel(row, text="—", font=t.FONT, text_color=t.MUTED)
            val.pack(side="left", padx=8)
            self.sensor_bars[key] = (bar, val)
        self.sensor_extra = ctk.CTkLabel(
            tab, text="", font=ctk.CTkFont(*t.MONO), justify="left", text_color=t.TEXT
        )
        self.sensor_extra.pack(anchor="w", padx=12, pady=12)
        self.after(500, self._refresh_sensors)

    def _refresh_sensors(self) -> None:
        snap = self.monitor.read()
        for key, pct in (("cpu", snap.cpu_percent), ("ram", snap.ram_percent), ("gpu", snap.gpu_percent)):
            bar, val = self.sensor_bars[key]
            bar.set((pct or 0) / 100)
            val.configure(text=_fmt(pct, "%"))
        self.sensor_extra.configure(
            text=(
                f"Temperatura CPU: {_fmt(snap.cpu_temp_c, ' °C')}\n"
                f"Temperatura GPU: {_fmt(snap.gpu_temp_c, ' °C')}\n"
                f"Disco leitura: {snap.disk_read_mb_s} MB/s   escrita: {snap.disk_write_mb_s} MB/s\n"
                f"Por núcleo: {' '.join(f'{p:.0f}' for p in snap.per_core_percent)}"
            )
        )
        self.after(1000, self._refresh_sensors)

    # ---------- Benchmark ----------
    def _build_benchmark(self, tab) -> None:
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        self.bench_btn = _button(bar, "Executar benchmark CPU + disco", self._run_benchmark)
        self.bench_btn.pack(side="left")
        self.bench_box = self._textbox(tab)
        self._set_text(self.bench_box, "Score próprio do PC Polimata (não comparável ao Cinebench).")

    def _run_benchmark(self) -> None:
        self.bench_btn.configure(state="disabled")
        self._set_text(self.bench_box, "Executando... (~10 s)")

        def work():
            return benchmark.run_cpu_benchmark(4.0), benchmark.run_disk_benchmark(128)

        def done(res):
            cpu, disk = res
            self.results["cpu_benchmark"] = cpu.to_dict()
            self.results["disk_benchmark"] = disk.to_dict()
            self._set_text(
                self.bench_box,
                (
                    f"CPU single-core: {cpu.single_core_score} pts\n"
                    f"CPU multi-core:  {cpu.multi_core_score} pts ({cpu.processes} processos, "
                    f"escala {cpu.scaling}x)\n\n"
                    f"Disco escrita: {disk.write_mb_s} MB/s\nDisco leitura: {disk.read_mb_s} MB/s "
                    f"(arquivo de {disk.size_mb} MB; leitura pode vir do cache)"
                ),
            )
            self.bench_btn.configure(state="normal")

        self._in_thread(work, done)

    # ---------- Stress ----------
    def _build_stress(self, tab) -> None:
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(form, text="Duração (s):").pack(side="left")
        self.stress_dur = ctk.CTkEntry(form, width=70)
        self.stress_dur.insert(0, "60")
        self.stress_dur.pack(side="left", padx=6)
        ctk.CTkLabel(form, text="Limite temp. (°C):").pack(side="left")
        self.stress_temp = ctk.CTkEntry(form, width=70)
        self.stress_temp.insert(0, "90")
        self.stress_temp.pack(side="left", padx=6)
        self.stress_start = _button(form, "Iniciar", self._start_stress)
        self.stress_start.pack(side="left", padx=6)
        self.stress_stop = _button(form, "PARAR", self._stop_stress, t.DANGER, t.BROWN_HOVER)
        self.stress_stop.pack(side="left")
        self.stress_box = self._textbox(tab)
        self.stress: StressTest | None = None

    def _start_stress(self) -> None:
        try:
            cfg = StressConfig(float(self.stress_dur.get()), float(self.stress_temp.get()))
        except ValueError as exc:
            self._set_text(self.stress_box, f"Configuração inválida: {exc}")
            return
        self.stress = StressTest(cfg)
        self.stress_start.configure(state="disabled")

        def on_sample(s):
            msg = f"{s['elapsed_s']:>6}s  CPU {s['cpu_percent']:>5}%  temp {_fmt(s['temp_c'], ' °C')}"
            self.after(0, lambda: self._set_text(self.stress_box, msg))

        def done(res):
            self.results["stress_test"] = res.to_dict()
            self._set_text(
                self.stress_box,
                (
                    f"Fim: {res.stop_reason}\nTempo: {res.elapsed_s}s   "
                    f"Temp. máx.: {_fmt(res.max_temp_c, ' °C')}"
                ),
            )
            self.stress_start.configure(state="normal")

        self._in_thread(lambda: self.stress.run(on_sample), done)

    def _stop_stress(self) -> None:
        if self.stress:
            self.stress.stop()

    # ---------- Gargalo ----------
    def _build_bottleneck(self, tab) -> None:
        ctk.CTkLabel(
            tab,
            text="Abra o jogo/aplicação que deseja analisar e inicie a amostragem.",
            text_color=t.MUTED,
        ).pack(anchor="w", padx=8, pady=(8, 0))
        form = ctk.CTkFrame(tab, fg_color="transparent")
        form.pack(fill="x", padx=8, pady=8)
        self.bn_dur = ctk.CTkSegmentedButton(
            form, values=["30", "45", "60"], selected_color=t.BROWN, selected_hover_color=t.BROWN_HOVER
        )
        self.bn_dur.set("30")
        self.bn_dur.pack(side="left")
        self.bn_btn = _button(form, "Analisar gargalo", self._run_bottleneck)
        self.bn_btn.pack(side="left", padx=8)
        self.bn_progress = ctk.CTkProgressBar(tab, progress_color=t.GREEN_LIGHT)
        self.bn_progress.pack(fill="x", padx=8)
        self.bn_progress.set(0)
        self.bn_box = self._textbox(tab, 300)

    def _run_bottleneck(self) -> None:
        self.bn_btn.configure(state="disabled")
        duration = float(self.bn_dur.get())

        def work():
            return bottleneck.sample_and_analyze(
                duration, on_progress=lambda p: self.after(0, lambda: self.bn_progress.set(p))
            )

        def done(res):
            self.results["bottleneck"] = res.to_dict()
            self._set_text(
                self.bn_box,
                (
                    f"Veredito: {res.verdict}\n{res.explanation}\n\n"
                    f"CPU média {res.avg_cpu}%  |  núcleo mais carregado {res.avg_max_core}%  |  "
                    f"GPU média {_fmt(res.avg_gpu, '%')}  |  {res.samples} amostras"
                ),
            )
            self.bn_btn.configure(state="normal")

        self._in_thread(work, done)

    # ---------- Relatório ----------
    def _build_report(self, tab) -> None:
        ctk.CTkLabel(
            tab, text="Exporta informações do sistema e os resultados desta sessão.", text_color=t.MUTED
        ).pack(anchor="w", padx=8, pady=8)
        _button(tab, "Exportar JSON", lambda: self._export(".json")).pack(anchor="w", padx=8, pady=4)
        _button(tab, "Exportar HTML", lambda: self._export(".html"), t.BROWN, t.BROWN_HOVER).pack(
            anchor="w", padx=8, pady=4
        )
        self.report_label = ctk.CTkLabel(tab, text="", text_color=t.GREEN_LIGHT)
        self.report_label.pack(anchor="w", padx=8, pady=8)

    def _export(self, ext: str) -> None:
        path = filedialog.asksaveasfilename(defaultextension=ext, initialfile=f"pc_polimata{ext}")
        if path:
            report.save_report(report.build_report(self.system, **self.results), path)
            self.report_label.configure(text=f"Salvo em {path}")


def run_gui() -> None:
    PolimataApp().mainloop()
