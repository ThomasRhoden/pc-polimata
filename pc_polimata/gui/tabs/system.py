from __future__ import annotations

import customtkinter as ctk

from pc_polimata.core.windows_temps import HINT
from pc_polimata.gui.widgets import fmt, set_text, textbox
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
        set_text(textbox(master), "\n".join(lines))
