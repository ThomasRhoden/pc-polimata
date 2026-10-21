from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core import smart
from pc_polimata.core.windows_temps import HINT
from pc_polimata.gui.widgets import button, fmt, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


class SystemTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        s = app.system
        lines = [
            tr("SISTEMA OPERACIONAL"),
            f"  {s['os']['system']} {s['os']['release']} ({s['os']['machine']})",
            f"  Host: {s['os']['hostname']}   Python {s['os']['python']}",
            "",
            tr("PROCESSADOR"),
            f"  {s['cpu']['name']}",
            f"  {tr('Núcleos')}: {s['cpu']['physical_cores']} {tr('físicos')} / "
            f"{s['cpu']['logical_cores']} {tr('lógicos')}",
            f"  {tr('Frequência máx.')}: {fmt(s['cpu']['max_freq_mhz'], ' MHz')}",
            "",
            tr("MEMÓRIA"),
            f"  {tr('Total')}: {s['memory']['total_gb']} GB   {tr('Em uso')}: {s['memory']['used_percent']}%",
            "",
            tr("DISCOS"),
        ]
        lines += [
            f"  {d['mountpoint']:<20} {d['fstype']:<8} {d['total_gb']:>8} GB  {d['used_percent']}% {tr('usado')}"
            for d in s["disks"]
        ]
        lines += ["", "GPU"]
        gpus = [
            f"  {g['name']} — VRAM {fmt(g['memory_total_mb'] and round(g['memory_total_mb']), ' MB')} "
            f"— driver {fmt(g['driver'])} [{g['source']}]"
            for g in s["gpus"]
        ]
        lines += gpus or [f"  {tr('Nenhuma GPU detectada.')}"]
        if s["os"]["system"] == "Windows":
            lines += ["", f"  * {HINT}"]
        self.app, self.base_text = app, "\n".join(lines)
        self.smart_btn = button(master, tr("Saúde dos discos (SMART)"), self.run_smart, primary=False)
        self.smart_btn.pack(anchor="w", padx=8, pady=(8, 0))
        self.box = textbox(master)
        set_text(self.box, self.base_text)

    def run_smart(self) -> None:
        self.smart_btn.configure(state="disabled")
        run_in_thread(self.smart_btn, smart.check_disks, self.done_smart)

    def done_smart(self, res) -> None:
        self.smart_btn.configure(state="normal")
        if isinstance(res, Exception):
            lines = [f"SMART: erro {res}"]
        elif not res:
            lines = ["SMART: smartctl não encontrado (instale smartmontools e execute como admin/root)."]
        else:
            self.app.record("disk_health", [h.to_dict() for h in res])
            lines = ["SMART"] + [
                f"  {h.device:<14} {h.status:<8} {fmt(h.model)}  {fmt(h.temperature_c, ' °C')}  "
                f"{fmt(h.power_on_hours, ' h')}{'  ' + h.error if h.error else ''}"
                for h in res
            ]
        set_text(self.box, "\n".join(lines) + "\n\n" + self.base_text)
