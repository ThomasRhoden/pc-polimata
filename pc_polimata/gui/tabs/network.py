from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import network
from pc_polimata.gui.widgets import button, fmt, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


class NetworkTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        bar = ctk.CTkFrame(master, fg_color="transparent")
        bar.pack(fill="x", padx=8, pady=8)
        self.lat_btn = button(bar, tr("Medir latência"), self.run_latency)
        self.lat_btn.pack(side="left")
        self.dl_btn = button(bar, tr("Teste de download"), self.run_download, primary=False)
        self.dl_btn.pack(side="left", padx=8)
        self.box = textbox(master)
        self.results: list[str] = []
        self.show_interfaces()

    def show_interfaces(self) -> None:
        lines = [tr("Interfaces locais")]
        for i in network.list_interfaces():
            state = "UP" if i["is_up"] else "down"
            lines.append(f"  {i['name']:<16} {state:<5} {', '.join(i['ipv4']) or '-'}")
        self.interfaces = "\n".join(lines)
        set_text(self.box, self.interfaces)

    def _show(self) -> None:
        set_text(self.box, "\n".join([*self.results, "", self.interfaces]))

    def run_latency(self) -> None:
        self.lat_btn.configure(state="disabled")
        run_in_thread(self.lat_btn, network.measure_latencies, self.done_latency)

    def done_latency(self, res) -> None:
        self.lat_btn.configure(state="normal")
        if isinstance(res, Exception):
            self.results = [tr("Erro: {error}", error=res)]
        else:
            self.app.record("network_latency", [r.to_dict() for r in res])
            self.results = [
                tr(
                    "TCP {host}:{port}  média {avg}  mín {min}  jitter {jitter}  falhas {failures}",
                    host=r.host,
                    port=r.port,
                    avg=fmt(r.avg_ms, " ms"),
                    min=fmt(r.min_ms, " ms"),
                    jitter=fmt(r.jitter_ms, " ms"),
                    failures=r.failures,
                )
                for r in res
            ]
        self._show()

    def run_download(self) -> None:
        self.dl_btn.configure(state="disabled")
        self.results = [tr("Executando... (~{seconds} s)", seconds=10)]
        self._show()
        run_in_thread(self.dl_btn, network.download_throughput, self.done_download)

    def done_download(self, res) -> None:
        self.dl_btn.configure(state="normal")
        if isinstance(res, Exception) or res.error:
            self.results = [tr("Erro: {error}", error=res if isinstance(res, Exception) else res.error)]
        else:
            self.app.record("network_download", res.to_dict())
            self.results = [
                tr(
                    "Download: {mbps} Mbit/s ({mb:.1f} MB em {seconds:.1f} s)",
                    mbps=res.mbps,
                    mb=res.bytes_received / 1e6,
                    seconds=res.seconds,
                )
                + (" — " + tr("tempo limite atingido") if res.timed_out else "")
            ]
        self._show()
