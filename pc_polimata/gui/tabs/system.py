from __future__ import annotations

from typing import Any

import customtkinter as ctk

from pc_polimata.core import smart
from pc_polimata.core.drivers import OUTDATED_AFTER_DAYS, driver_report
from pc_polimata.core.gpu import GPUStatus
from pc_polimata.core.windows_temps import HINT
from pc_polimata.gui.widgets import button, fmt, run_in_thread, set_text, textbox
from pc_polimata.i18n import tr


def _gpu_status(g: dict[str, Any]) -> GPUStatus:
    return GPUStatus(**{k: v for k, v in g.items() if k in GPUStatus.__dataclass_fields__})


class SystemTab:
    def __init__(self, master: ctk.CTkFrame, app) -> None:
        self.app = app
        s = app.system
        lines = [
            tr("SISTEMA OPERACIONAL"),
            f"  {s['os']['system']} {s['os']['release']} ({s['os']['machine']})",
            f"  Host: {s['os']['hostname']}   Python {s['os']['python']}",
            "",
            tr("PROCESSADOR"),
            f"  {s['cpu']['name']}",
            "  "
            + tr(
                "Núcleos: {physical} físicos / {logical} lógicos",
                physical=s["cpu"]["physical_cores"],
                logical=s["cpu"]["logical_cores"],
            ),
            "  " + tr("Frequência máx.: {freq}", freq=fmt(s["cpu"]["max_freq_mhz"], " MHz")),
            "",
            tr("MEMÓRIA"),
            "  "
            + tr(
                "Total: {total} GB   Em uso: {used}%", total=s["memory"]["total_gb"], used=s["memory"]["used_percent"]
            ),
            "",
            tr("DISCOS"),
        ]
        lines += [
            f"  {d['mountpoint']:<20} {d['fstype']:<8} {d['total_gb']:>8} GB  "
            + tr("{used}% usado", used=d["used_percent"])
            for d in s["disks"]
        ]
        lines += ["", "GPU"]
        gpus = [
            f"  {g['name']} — VRAM {fmt(g['memory_total_mb'] and round(g['memory_total_mb']), ' MB')} [{g['source']}]"
            for g in s["gpus"]
        ]
        lines += gpus or ["  " + tr("Nenhuma GPU detectada.")]
        lines += ["", tr("DRIVERS DE VÍDEO")] + self._driver_lines()
        if s["os"]["system"] == "Windows":
            lines += ["", f"  * {tr(HINT)}"]
        self.base_text = "\n".join(lines)
        self.smart_btn = button(master, tr("Saúde dos discos (SMART)"), self.run_smart, primary=False)
        self.smart_btn.pack(anchor="w", padx=8, pady=(8, 0))
        self.box = textbox(master)
        set_text(self.box, self.base_text)

    def _driver_lines(self) -> list[str]:
        infos = driver_report([_gpu_status(g) for g in self.app.system["gpus"]])
        self.app.record("drivers", [d.to_dict() for d in infos] or None)
        if not infos:
            return ["  " + tr("Nenhuma GPU detectada.")]
        out = []
        for d in infos:
            line = f"  {d.gpu}: {tr('versão')} {fmt(d.version)}, {tr('data')} {fmt(d.release_date)}"
            if d.outdated:
                line += "  ⚠ " + tr(
                    "driver com mais de {days} dias ({age} dias): considere atualizar",
                    days=OUTDATED_AFTER_DAYS,
                    age=d.age_days,
                )
            elif d.outdated is None:
                line += "  (" + tr("data do driver indisponível neste sistema") + ")"
            out.append(line)
        return out

    def run_smart(self) -> None:
        self.smart_btn.configure(state="disabled")
        run_in_thread(self.smart_btn, smart.check_disks, self.done_smart)

    def done_smart(self, res) -> None:
        self.smart_btn.configure(state="normal")
        if isinstance(res, Exception):
            lines = [tr("SMART: erro {error}", error=res)]
        elif not res:
            lines = [tr("SMART: smartctl não encontrado (instale smartmontools e execute como admin/root).")]
        else:
            self.app.record("disk_health", [h.to_dict() for h in res])
            lines = ["SMART"] + [
                f"  {h.device:<14} {tr(h.status):<8} {fmt(h.model)}  {fmt(h.temperature_c, ' °C')}  "
                f"{fmt(h.power_on_hours, ' h')}{'  ' + h.error if h.error else ''}"
                for h in res
            ]
        set_text(self.box, "\n".join(lines) + "\n\n" + self.base_text)
